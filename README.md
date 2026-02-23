# strava-forwarder

A Python automation tool that polls the Strava API for recent fitness activities and writes them to a shared Google Sheet. It is designed to support group accountability workflows by automatically forwarding workout data — including activity name and duration — triggered by Apple Watch fitness sessions synced through the Strava mobile app.

## How It Works

1. Apple Watch records a fitness session and syncs it to Strava via the Strava iOS app.
2. A cron job on a persistent Ubuntu server executes the script once daily.
3. The script fetches the most recent activities from the Strava API.
4. For each activity, it looks up the corresponding date row in a designated Google Sheet worksheet and writes the activity name and duration.

## Prerequisites

- Python 3.10 or later
- A Strava API application (Client ID, Client Secret, and a valid Refresh Token)
- A Google Cloud service account with access to the Google Sheets API
- A `credentials.json` file downloaded from the Google Cloud Console for the service account
- The target Google Sheet shared with the service account's email address

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/strava-forwarder.git
cd strava-forwarder
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib gspread
```

### 4. Add credentials

Place your Google service account credentials file in the project root:

```
strava-forwarder/
└── credentials.json
```

### 5. Set environment variables

Export the following environment variables before running the script:

```bash
export STRAVA_CLIENT_ID=your_strava_client_id
export STRAVA_CLIENT_SECRET=your_strava_client_secret
export STRAVA_REFRESH_TOKEN=your_strava_refresh_token
export GOOGLE_SHEET_ID=your_google_sheet_id
```

## Scheduling with Cron

The script is intended to run daily via a crontab entry on a persistent Ubuntu server. Because cron does not inherit a user's shell environment, the environment variables and the virtual environment interpreter must be specified explicitly in the crontab.

Open the crontab editor:

```bash
crontab -e
```

Add an entry such as the following to run the script every day at 08:00:

```
0 8 * * * STRAVA_CLIENT_ID=your_strava_client_id STRAVA_CLIENT_SECRET=your_strava_client_secret STRAVA_REFRESH_TOKEN=your_strava_refresh_token GOOGLE_SHEET_ID=your_google_sheet_id /path/to/strava-forwarder/.venv/bin/python3 /path/to/strava-forwarder/main.py >> /tmp/strava-forwarder.log 2>&1
```

Both stdout and stderr are redirected to `/tmp/strava-forwarder.log`. This file persists across runs and can be inspected to verify execution or diagnose errors:

```bash
cat /tmp/strava-forwarder.log
```

Replace `/path/to/strava-forwarder` with the absolute path to the cloned repository on the server.

## Manual Usage

The script can also be run directly after activating the virtual environment:

```bash
source .venv/bin/activate
python3 main.py
```

The script will fetch the five most recent Strava activities and update the corresponding rows in the `Tracker` worksheet of the configured Google Sheet. Each row is matched by date (column B), and the activity name and duration in minutes are written to columns G and H respectively.

## Google Sheet Format

The target worksheet must have dates pre-populated in column B using the format `Mon DD` (e.g., `Feb 22`). The script will skip any activity whose date does not match an existing row.

| Column | Content |
|--------|---------|
| B | Date (`Mon DD`) |
| G | Activity name |
| H | Duration (minutes) |
