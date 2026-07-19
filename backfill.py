#!/usr/bin/env python3
"""One-time backfill: post this year's workouts from an Apple Health export.

The workout-ended automation only records workouts going forward. To fill in
history, export your data from the Health app and feed it through the same
endpoint the automation uses:

  1. On the iPhone: Health app -> tap your picture -> Export All Health Data.
     Share the resulting export.zip to your computer (AirDrop, Files, ...).
  2. Run:

     python3 backfill.py export.zip 'https://script.google.com/macros/s/<ID>/exec' YOUR-TOKEN

Only workouts from the current calendar year are sent. The tracker sheet is
recreated each year and its date rows carry no year, so older workouts would
land on this year's rows — the export's earlier years are always skipped.

Safe to re-run: the server logs every workout it has seen and ignores
duplicates. Requires only the Python standard library (3.9+).
"""

import argparse
import re
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime
from typing import IO, Iterator
from xml.etree import ElementTree

# English month abbreviations, hard-coded on purpose: the sheet's dates are
# English, and locale-aware formatting would break the match on machines set
# to another language.
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

EXPORT_XML = "apple_health_export/export.xml"


def friendly_name(activity_type: str) -> str:
    """HKWorkoutActivityTypeTraditionalStrengthTraining -> Traditional Strength Training"""
    name = activity_type.removeprefix("HKWorkoutActivityType")
    return re.sub(r"(?<=[a-z])(?=[A-Z0-9])", " ", name)


def sheet_date(start: datetime) -> str:
    return f"{MONTHS[start.month - 1]} {start.day:02d}"


def collect_workouts(xml_file: IO[bytes], year: int) -> list[tuple[datetime, str, float]]:
    """Return (start, activity name, duration in minutes) per workout in `year`."""
    workouts = []
    for _, elem in ElementTree.iterparse(xml_file):
        if elem.tag != "Workout":
            continue
        start = datetime.strptime(elem.get("startDate"), "%Y-%m-%d %H:%M:%S %z")
        if start.year == year:
            name = friendly_name(elem.get("workoutActivityType", "Workout"))
            workouts.append((start, name, float(elem.get("duration", "0"))))
        elem.clear()
    return workouts


def workout_lines(workouts: list[tuple[datetime, str, float]]) -> Iterator[str]:
    """Yield one line per workout, in start order.

    The minutes field is the running total for the workout's day, mirroring
    the phone automation (which posts the day's activity total at each
    workout's end); the server shows the largest value received per date.
    """
    day_totals: dict[date, float] = {}
    for start, name, minutes in sorted(workouts, key=lambda w: w[0]):
        day = start.date()
        day_totals[day] = day_totals.get(day, 0.0) + minutes
        yield f"{name}|{sheet_date(start)}|{round(day_totals[day])}|{start:%H:%M}"


def load_lines(export_path: str, year: int) -> list[str]:
    if export_path.endswith(".zip"):
        with zipfile.ZipFile(export_path) as archive:
            with archive.open(EXPORT_XML) as xml_file:
                return list(workout_lines(collect_workouts(xml_file, year)))
    with open(export_path, "rb") as xml_file:
        return list(workout_lines(collect_workouts(xml_file, year)))


def post_lines(url: str, token: str, lines: list[str]) -> str:
    request = urllib.request.Request(
        f"{url}?token={token}", data="\n".join(lines).encode()
    )
    with urllib.request.urlopen(request) as response:
        return response.read().decode()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("export", help="export.zip (or export.xml) from the Health app")
    parser.add_argument("url", help="the script's Web app URL, ending in /exec")
    parser.add_argument("token", help="your personal token from the sheet owner")
    args = parser.parse_args()
    year = date.today().year

    try:
        lines = load_lines(args.export, year)
    except FileNotFoundError:
        sys.exit(f"File not found: {args.export}")
    except (zipfile.BadZipFile, KeyError):
        sys.exit(f"{args.export} does not look like a Health export "
                 f"(expected {EXPORT_XML} inside the zip)")
    except ElementTree.ParseError as err:
        sys.exit(f"Could not parse the export's XML: {err}")

    if not lines:
        sys.exit(f"No workouts from {year} found in the export.")
    print(f"Posting {len(lines)} workout(s) from {year}...")

    try:
        print(post_lines(args.url, args.token, lines))
    except urllib.error.URLError as err:
        sys.exit(f"Upload failed: {getattr(err, 'reason', err)}")


if __name__ == "__main__":
    main()
