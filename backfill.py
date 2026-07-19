#!/usr/bin/env python3
"""One-time backfill: post this year's workouts from an Apple Health export.

The workout-ended automation only records workouts going forward. To fill in
history, export your data from the Health app and feed it through the same
endpoint the Shortcut uses:

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

import re
import sys
import urllib.request
import zipfile
from datetime import date, datetime
from xml.etree import ElementTree

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def friendly_name(activity_type: str) -> str:
    """HKWorkoutActivityTypeTraditionalStrengthTraining -> Traditional Strength Training"""
    name = activity_type.removeprefix("HKWorkoutActivityType")
    return re.sub(r"(?<=[a-z])(?=[A-Z0-9])", " ", name)


def sheet_date(start: datetime) -> str:
    return f"{MONTHS[start.month - 1]} {start.day:02d}"


def workout_lines(xml_file, year: int):
    for _, elem in ElementTree.iterparse(xml_file):
        if elem.tag != "Workout":
            continue
        start = datetime.strptime(elem.get("startDate"), "%Y-%m-%d %H:%M:%S %z")
        if start.year == year:
            minutes = round(float(elem.get("duration", "0")))  # durationUnit is "min"
            name = friendly_name(elem.get("workoutActivityType", "Workout"))
            yield f"{name}|{sheet_date(start)}|{minutes}|{start:%H:%M}"
        elem.clear()


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    export_path, url, token = sys.argv[1:4]
    year = date.today().year

    if export_path.endswith(".zip"):
        with zipfile.ZipFile(export_path) as archive:
            with archive.open("apple_health_export/export.xml") as xml_file:
                lines = list(workout_lines(xml_file, year))
    else:
        with open(export_path, "rb") as xml_file:
            lines = list(workout_lines(xml_file, year))

    if not lines:
        sys.exit(f"No workouts from {year} found in the export.")
    print(f"Posting {len(lines)} workout(s) from {year}...")

    request = urllib.request.Request(
        f"{url}?token={token}", data="\n".join(lines).encode()
    )
    with urllib.request.urlopen(request) as response:
        print(response.read().decode())


if __name__ == "__main__":
    main()
