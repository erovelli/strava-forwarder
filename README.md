# health-forwarder

*(formerly strava-forwarder)*

Automatically forwards Apple Watch / iPhone workouts to a shared Google Sheet, for group accountability trackers. Every day, an iPhone Shortcut reads each person's recent workouts straight from Apple Health and sends them to a small script attached to the Google Sheet, which fills in the activity name and duration on the matching date row — in that person's own columns.

Everything in this setup is **completely free**: no Strava account, no server, no subscriptions. Workout data goes only from each person's phone to the group's Google Sheet.

> **Why the change?** Earlier versions of this project pulled workouts from the Strava API using a Python script on a server. Strava has since gated API access behind premium accounts, so workouts now come directly from Apple Health instead — which also removes the need for a server entirely. The old Python version is preserved as [release v1.0.0](../../releases/tag/v1.0.0).

## How It Works

1. Your Apple Watch (or iPhone) records a workout, which is stored in Apple Health.
2. Once a day, an automation runs a Shortcut on your iPhone that reads your recent workouts from Apple Health.
3. The Shortcut sends them to a small Google Apps Script attached to the group's Google Sheet, along with your personal token.
4. The script recognizes you by your token, finds the row matching each workout's date, and writes the activity name and duration into **your** columns. Multiple workouts on the same day are combined into one entry.

Re-sending the same workouts is always safe: rows are matched by date and overwritten, never appended. This means you can also **backfill retrospectively** — set the Shortcut to fetch your last 100 workouts instead of 5, run it once, and every matching date row gets filled in.

## Who Sets Up What

The **sheet owner** does the one-time script setup (Part 1) and gives every member two things: a link to the shared Shortcut and that member's personal token. Each **member** only does the phone setup (Parts 2–3) — no Google account access, no code, nothing to install beyond the Shortcut. Members don't even need edit access to the spreadsheet; the script writes on the owner's behalf.

---

## Part 1 — Attach the script to the Google Sheet (sheet owner only, one time, on a computer)

1. Open the Google Sheet in a browser.
2. In the menu, click **Extensions → Apps Script**. A code editor opens in a new tab.
3. Delete any code already in the editor, then copy the entire contents of [`Code.gs`](Code.gs) from this repository and paste it in.
4. Edit the `USERS` map near the top: one line per group member. For each person, invent a unique secret token (like a password — letters, numbers, and dashes; no spaces) and set the column number where their activity names should go. The duration always goes in the next column over. Column numbers: A=1, B=2, … G=7, and so on. For example:

   ```javascript
   const USERS = {
     "erik-x7f2":  7,   // Erik  → columns G/H
     "sam-p9k1":   9,   // Sam   → columns I/J
     "dana-m3q8": 11,   // Dana  → columns K/L
   };
   ```
5. Click the **Deploy** button (top right) → **New deployment**.
6. Click the gear icon next to "Select type" and choose **Web app**.
7. Set **Execute as: Me** and **Who has access: Anyone**, then click **Deploy**.

   > "Anyone" only means anyone *with the exact URL and a valid token* can submit workouts — the URL is unguessable and each token only reaches its own columns. The sheet's own sharing settings are unaffected.
8. Google will ask you to authorize the script. Click **Authorize access**, pick your account, and if you see a warning that the app isn't verified, click **Advanced → Go to (project name) (unsafe)** → **Allow**. This warning appears because you wrote the script yourself; you are authorizing your own code.
9. Copy the **Web app URL** it gives you (it ends in `/exec`). Send each member the URL and *their* token, privately.

> **Adding a member or editing the code later:** changes don't go live until you click **Deploy → Manage deployments → ✏️ Edit → Version: New version → Deploy**. This is the most commonly missed step in Apps Script. The URL stays the same.

## Part 2 — Build the Shortcut (each member, on their iPhone)

> If someone in the group has already built this Shortcut, ask them to share it with you (long-press the Shortcut → **Share**) — then you only need to import it, replace the token in the URL with your own, and skip to Part 3.

Open the **Shortcuts** app, tap **+** to create a new shortcut, name it **Health Forwarder**, and add these actions in order (use the search bar to find each one):

1. **Find Health Samples**
   - Tap the pale blue **Type** field and choose **Workouts**.
   - Set **Sort by: Start Date** and **Order: Latest First**.
   - Turn **Limit** on and set it to **5**. (Use a bigger number like **100** to backfill history — see Part 4.)
2. **Repeat with Each** — make sure it repeats over **Health Samples** (it usually connects automatically).
3. Inside the repeat block, add a **Text** action. In the text box, build one line with three parts separated by the `|` character (type the two `|` characters yourself):
   - Tap **Repeat Item** in the variable bar above the keyboard to insert it, then tap the inserted variable and set its property to **Workout Type**.
   - Type `|`, insert **Repeat Item** again, and set its property to **Start Date**. Tap the variable once more and set **Date Format: Custom**, with the format string exactly `MMM dd` (this produces dates like `Feb 02`, matching the sheet).
   - Type `|`, insert **Repeat Item** a third time, and set its property to **Duration**.
4. Still inside the repeat block, add **Add to Variable**, set the input to the **Text** from the previous step, and name the variable `Lines`.
5. After the repeat block ends, add **Combine Text**: combine **Lines**, separator **New Lines**.
6. Add **Get Contents of URL**:
   - In the URL field, paste the Web app URL from the sheet owner and add **your personal token** to the end, like this:
     `https://script.google.com/macros/s/…/exec?token=erik-x7f2`
   - Tap the arrow to expand the action. Set **Method: POST**.
   - Under **Request Body**, choose **File** and select the **Combined Text** variable.
7. *(Optional)* Add **Show Notification** with the **Contents of URL** as its text, so you get a "Updated 2 row(s) in Tracker" confirmation each run.

Tap the Shortcut's ▶︎ button to test it. The first run asks for permission to access your Health data (allow **Workouts**) and to contact `script.google.com` — allow both. Then check the sheet: recent workout days should be filled in, in your columns.

## Part 3 — Run it automatically every day

1. In the Shortcuts app, go to the **Automation** tab and tap **+**.
2. Choose **Time of Day**, pick a time you're usually awake (e.g. 9:00 PM), set it to **Daily**, and select **Run Immediately** so it doesn't ask for confirmation.
3. Choose the **Health Forwarder** shortcut.

Your phone now uploads your workouts every day on its own. If your phone is off or offline at that time, no problem — the next successful run re-sends the last 5 workouts and backfills anything that was missed.

## Part 4 — Backfilling past workouts

To fill in history retrospectively (for example when you first set this up):

1. Edit the Shortcut and change the **Limit** in *Find Health Samples* from 5 to **100** (or however far back you want to go).
2. Run the Shortcut manually once.
3. Change the limit back to 5.

Every workout whose date matches a row in the sheet gets written; dates with no matching row are skipped. Running it multiple times is harmless — rows are overwritten with the same values, not duplicated. Each member backfills independently; nobody's upload touches anyone else's columns.

## Google Sheet Format

The worksheet must have dates pre-populated in column B using the format `MMM dd` with a zero-padded day (e.g., `Feb 02`). The date column is shared by everyone; each member has their own pair of adjacent columns for name and duration, assigned in the `USERS` map.

| Column | Content |
|--------|---------|
| B | Date (`Feb 02`) — shared |
| G / H | Member 1: activity name / duration (minutes) |
| I / J | Member 2: activity name / duration (minutes) |
| … | one adjacent pair per member |

If someone has multiple workouts on the same date, their names are combined into a single comma-separated entry and their durations are summed.

## Configuration

Constants at the top of `Code.gs` (remember to deploy a **new version** after editing — see the note in Part 1):

| Constant | Default | Description |
|----------|---------|-------------|
| `USERS` | *(examples)* | Map of each member's secret token to the column number for their activity names; durations are written to the next column over |
| `WORKSHEET_NAME` | `"Tracker"` | Name of the worksheet tab to write to |
| `DATE_COLUMN` | `2` (column B) | Column containing the `MMM dd` dates |

The number of workouts fetched per run is set by the **Limit** in the Shortcut's *Find Health Samples* action.

## Troubleshooting

- **"Updated 0 row(s)"** — the workout dates didn't match any value in column B. Check that column B shows dates exactly like `Feb 02` (zero-padded day, matching `MMM dd`).
- **"Error: invalid token"** — the token in the Shortcut URL doesn't match any entry in the `USERS` map. Check for typos, and if the member was just added, make sure a **new version** was deployed.
- **Workouts appear in the wrong columns** — two members are using the same token, or the column number in `USERS` is wrong. Each member's token must be unique.
- **Response looks like an HTML page or an error about `doPost`** — the deployment is stale or the URL is wrong; make sure you're using the `/exec` URL from an active Web app deployment, and re-deploy a new version after any code edit.
- **The nightly automation didn't run** — the phone was likely off or offline. The next run backfills automatically since it always sends the last 5 workouts.
- **Workout shows the wrong day** — dates are formatted in the phone's local time zone by the Shortcut, so this should not happen; if it does, check the `MMM dd` custom date format in the Text action.
