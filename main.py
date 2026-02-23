import requests
import os

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")

STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"


def get_access_token():
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }
    response = requests.post(STRAVA_TOKEN_URL, data=payload)
    response.raise_for_status()
    return response.json()["access_token"]


def get_recent_activities(access_token, count=5):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        STRAVA_ACTIVITIES_URL, headers=headers, params={"per_page": count}
    )
    response.raise_for_status()
    return response.json()


def fmt_duration(seconds):
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


def parse_activity(activity):
    return {
        "name": activity["name"],
        "date": activity["start_date"].split("T")[0],
        "duration": fmt_duration(activity["elapsed_time"]),
    }


if __name__ == "__main__":
    token = get_access_token()
    activities = get_recent_activities(token)
    result = [parse_activity(a) for a in activities]
    print(result)
