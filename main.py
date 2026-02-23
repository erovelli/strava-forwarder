import os
import requests
import gspread
from dataclasses import dataclass
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- Configuration ---

STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
WORKSHEET_NAME = "Tracker"

DATE_FORMAT_IN = "%Y-%m-%d"
DATE_FORMAT_OUT = "%b %d"


# --- Data Model ---


@dataclass
class Activity:
    name: str
    date: str
    duration: int  # minutes


# --- Strava Client ---


class StravaClient:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._access_token: str | None = None

    @property
    def access_token(self) -> str:
        if not self._access_token:
            self._access_token = self._fetch_access_token()
        return self._access_token

    def _fetch_access_token(self) -> str:
        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token",
        }
        response = requests.post(STRAVA_TOKEN_URL, data=payload)
        response.raise_for_status()
        return response.json()["access_token"]

    def get_recent_activities(self, count: int = 5) -> list[Activity]:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(
            STRAVA_ACTIVITIES_URL, headers=headers, params={"per_page": count}
        )
        response.raise_for_status()
        return [self._parse_activity(a) for a in response.json()]

    @staticmethod
    def _parse_activity(raw: dict) -> Activity:
        return Activity(
            name=raw["name"],
            date=raw["start_date"].split("T")[0],
            duration=raw["elapsed_time"] // 60,
        )


# --- Google Sheets Client ---


class SheetsClient:
    def __init__(self, credentials_file: str, sheet_id: str):
        creds = Credentials.from_service_account_file(
            credentials_file, scopes=GOOGLE_SCOPES
        )
        self._workbook = gspread.authorize(creds).open_by_key(sheet_id)

    def write_activities(
        self, activities: list[Activity], worksheet_name: str = WORKSHEET_NAME
    ) -> None:
        worksheet = self._workbook.worksheet(worksheet_name)
        date_column = worksheet.col_values(2)

        updates = []
        for activity in activities:
            sheet_date = datetime.strptime(activity.date, DATE_FORMAT_IN).strftime(
                DATE_FORMAT_OUT
            )
            try:
                row = date_column.index(sheet_date) + 1
            except ValueError:
                print(f"No row found for date {sheet_date}, skipping '{activity.name}'")
                continue
            updates.append(
                {
                    "range": f"G{row}:H{row}",
                    "values": [[activity.name, activity.duration]],
                }
            )

        if updates:
            worksheet.batch_update(updates)
            print(f"Updated {len(updates)} row(s) in {worksheet_name}")
        else:
            print(f"No matching rows found in {worksheet_name}")


# --- Entry Point ---


def main() -> None:
    strava = StravaClient(
        client_id=os.environ["STRAVA_CLIENT_ID"],
        client_secret=os.environ["STRAVA_CLIENT_SECRET"],
        refresh_token=os.environ["STRAVA_REFRESH_TOKEN"],
    )
    sheets = SheetsClient(
        credentials_file="credentials.json",
        sheet_id=os.environ["GOOGLE_SHEET_ID"],
    )

    activities = strava.get_recent_activities()
    sheets.write_activities(activities)


if __name__ == "__main__":
    main()
