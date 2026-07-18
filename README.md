# health-forwarder

*(formerly strava-forwarder)*

Automatically forwards daily exercise minutes from Apple Health to a shared Google Sheet, for group accountability trackers. Every day, an iPhone Shortcut reads each person's Exercise Minutes straight from Apple Health and sends them to a small script attached to the Google Sheet, which fills in the matching date row — in that person's own column.

Everything in this setup is **completely free**: no Strava account, no server, no subscriptions. Exercise data goes only from each person's phone to the group's Google Sheet.

> **Why the change?** Earlier versions of this project pulled workout names and durations from the Strava API using a Python script on a server. Strava has since gated API access behind premium accounts, so the data now comes directly from Apple Health instead — which also removes the need for a server entirely. The old Python version is preserved as [release v1.0.0](../../releases/tag/v1.0.0).
>
> One trade-off: Apple's built-in Shortcuts actions can read Health *metrics* (like Exercise Minutes) but not individual workout records, so the sheet now tracks **minutes per day** rather than named activities. A notes column next to each person's minutes is a nice manual complement.

## How It Works

1. Your Apple Watch (or iPhone) tracks exercise, which lands in Apple Health as Exercise Minutes.
2. Once a day, an automation runs a Shortcut on your iPhone that reads your recent daily Exercise Minute totals from Apple Health.
3. The Shortcut sends them to a small Google Apps Script attached to the group's Google Sheet, along with your personal token.
4. The script recognizes you by your token, finds the row matching each date, and writes that day's total minutes into **your** column.

Re-sending the same days is always safe: rows are matched by date and overwritten, never appended. This means you can also **backfill retrospectively** — set the Shortcut to fetch 100 days instead of 7, run it once, and every matching date row gets filled in.

> **What counts as "exercise minutes"?** This is the number behind Apple's green Exercise ring: minutes of movement at or above a brisk walk, from workouts and everyday activity alike. It can differ slightly from a workout's elapsed time (a 60-minute gym session might credit 52 exercise minutes).

## Who Sets Up What

The **sheet owner** does the one-time script setup (Part 1) and gives every member two things: a link to the shared Shortcut and that member's personal token. Each **member** only does the phone setup (Parts 2–3) — no Google account access, no code, nothing to install beyond the Shortcut. Members don't even need edit access to the spreadsheet; the script writes on the owner's behalf.

---

## Part 1 — Attach the script to the Google Sheet (sheet owner only, one time, on a computer)

1. Open the Google Sheet in a browser.
2. In the menu, click **Extensions → Apps Script**. A code editor opens in a new tab.
3. Delete any code already in the editor, then copy the entire contents of [`Code.gs`](Code.gs) from this repository and paste it in.
4. Edit the `USERS` map near the top: one line per group member. For each person, invent a unique secret token (like a password — letters, numbers, and dashes; no spaces) and set the column number where their exercise minutes should go. Column numbers: A=1, B=2, … H=8, and so on. For example:

   ```javascript
   const USERS = {
     "erik-x7f2":  8,   // Erik  → column H
     "sam-p9k1":  10,   // Sam   → column J
     "dana-m3q8": 12,   // Dana  → column L
   };
   ```
5. Click the **Deploy** button (top right) → **New deployment**.
6. Click the gear icon next to "Select type" and choose **Web app**.
7. Set **Execute as: Me** and **Who has access: Anyone**, then click **Deploy**.

   > "Anyone" only means anyone *with the exact URL and a valid token* can submit data — the URL is unguessable and each token only reaches its own column. The sheet's own sharing settings are unaffected.
8. Google will ask you to authorize the script. Click **Authorize access**, pick your account, and if you see a warning that the app isn't verified, click **Advanced → Go to (project name) (unsafe)** → **Allow**. This warning appears because you wrote the script yourself; you are authorizing your own code.
9. Copy the **Web app URL** it gives you (it ends in `/exec`). Send each member the URL and *their* token, privately.

> **Adding a member or editing the code later:** changes don't go live until you click **Deploy → Manage deployments → ✏️ Edit → Version: New version → Deploy**. This is the most commonly missed step in Apps Script. The URL stays the same.

## Part 2 — Build the Shortcut (each member, on their iPhone)

> If someone in the group has already built this Shortcut, ask them to share it with you (long-press the Shortcut → **Share**) — then you only need to import it, replace the token in the URL with your own, and skip to Part 3.

Open the **Shortcuts** app, tap **+** to create a new shortcut, name it **Health Forwarder**, and add these actions in order (use the search bar to find each one):

1. **Find Health Samples**
   - Tap the pale blue **Type** field and choose **Exercise Minutes**.
   - Tap **Add Filter** and set **Start Date** · **is in the last** · **7** · **days** (the last week — days already uploaded are harmlessly re-written). Use a bigger number like **100** to backfill history — see Part 4.
   - Check that **Unit** is **min**.
   - Set **Group By: Day** — this is essential; it turns the raw samples into one total per day.
   - Leave **Limit** turned **off**. (It counts individual samples, not days, and will silently truncate your totals.)
2. **Repeat with Each** — make sure it repeats over **Health Samples** (it usually connects automatically).
3. Inside the repeat block, add a **Text** action. In the text box, build one line with two parts separated by the `|` character (type the `|` yourself):
   - Tap **Repeat Item** in the variable bar above the keyboard to insert it, then tap the inserted variable and set its property to **Start Date**. Tap it once more and set **Date Format: Custom**, with the format string exactly `MMM dd` (this produces dates like `Feb 02`, matching the sheet).
   - Type `|`, then insert **Repeat Item** again and set its property to **Value** (the day's total minutes).
4. Still inside the repeat block, add **Add to Variable**, set the input to the **Text** from the previous step, and name the variable `Lines`.
5. After the repeat block ends, add **Combine Text**: combine **Lines**, separator **New Lines**.
6. Add **Get Contents of URL**:
   - In the URL field, paste the Web app URL from the sheet owner and add **your personal token** to the end, like this:
     `https://script.google.com/macros/s/…/exec?token=erik-x7f2`
   - Tap the arrow to expand the action. Set **Method: POST**.
   - Under **Request Body**, choose **File** and select the **Combined Text** variable.
7. *(Optional)* Add **Show Notification** with the **Contents of URL** as its text, so you get a "Updated 7 row(s) in Tracker" confirmation each run.

Tap the Shortcut's ▶︎ button to test it. The first run asks for permission to access your Health data (allow **Exercise Minutes**) and to contact `script.google.com` — allow both. Then check the sheet: the last week's rows should show your minutes, in your column.

## Part 3 — Run it automatically every day

1. In the Shortcuts app, go to the **Automation** tab and tap **+**.
2. Choose **Time of Day**, pick a time late in the day (e.g. 9:00 PM, so the day's exercise is mostly in), set it to **Daily**, and select **Run Immediately** so it doesn't ask for confirmation.
3. Choose the **Health Forwarder** shortcut.

Your phone now uploads your minutes every day on its own. Each run covers the last 7 days, so a day when the phone was off or offline is backfilled automatically by the next successful run — and today's partial total is corrected by tomorrow's run.

## Part 4 — Backfilling past days

To fill in history retrospectively (for example when you first set this up):

1. Edit the Shortcut and change the **Start Date** filter in *Find Health Samples* from the last **7** days to the last **100** days (or however far back you want to go).
2. Run the Shortcut manually once.
3. Change the filter back to 7 days.

Every day whose date matches a row in the sheet gets written; dates with no matching row are skipped. Running it multiple times is harmless — rows are overwritten with the same values, not duplicated. Each member backfills independently; nobody's upload touches anyone else's column.

## Google Sheet Format

The worksheet must have dates pre-populated in column B using the format `MMM dd` with a zero-padded day (e.g., `Feb 02`). The date column is shared by everyone; each member has their own minutes column, assigned in the `USERS` map. The column next to each member's minutes makes a good spot for hand-written notes ("5k run", "leg day") — the script never touches it.

| Column | Content |
|--------|---------|
| B | Date (`Feb 02`) — shared |
| H | Member 1: exercise minutes (G free for notes) |
| J | Member 2: exercise minutes (I free for notes) |
| … | one column per member |

## Configuration

Constants at the top of `Code.gs` (remember to deploy a **new version** after editing — see the note in Part 1):

| Constant | Default | Description |
|----------|---------|-------------|
| `USERS` | *(examples)* | Map of each member's secret token to the column number for their exercise minutes |
| `WORKSHEET_NAME` | `"Tracker"` | Name of the worksheet tab to write to |
| `DATE_COLUMN` | `2` (column B) | Column containing the `MMM dd` dates |

The number of days fetched per run is set by the **Limit** in the Shortcut's *Find Health Samples* action.

## Troubleshooting

- **"Updated 0 row(s)"** — the dates didn't match any value in column B. Check that column B shows dates exactly like `Feb 02` (zero-padded day, matching `MMM dd`).
- **"Error: invalid token"** — the token in the Shortcut URL doesn't match any entry in the `USERS` map. Check for typos, and if the member was just added, make sure a **new version** was deployed.
- **Minutes look far too small** — the *Find Health Samples* action has **Limit** turned on, or is missing **Group By: Day**. Limit counts individual samples (roughly one per minute of exercise), not days, so it silently truncates totals — turn it off and use the Start Date filter to control the window instead.
- **Minutes look higher than your workouts** — that's expected: exercise minutes count *all* movement at or above a brisk walk throughout the day (stairs, hurried walking), not just workout sessions.
- **Minutes land in the wrong column** — two members are using the same token, or the column number in `USERS` is wrong. Each member's token must be unique.
- **Response looks like an HTML page or an error about `doPost`** — the deployment is stale or the URL is wrong; make sure you're using the `/exec` URL from an active Web app deployment, and re-deploy a new version after any code edit.
- **The nightly automation didn't run** — the phone was likely off or offline. The next run backfills automatically since it always sends the last 7 days.
- **A day shows fewer minutes than expected** — exercise minutes are Apple's green-ring metric (movement at or above a brisk walk), not workout elapsed time; gentler activity credits fewer minutes.
