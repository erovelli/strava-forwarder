# health-forwarder

*(formerly strava-forwarder)*

Automatically forwards Apple Watch / iPhone workouts to a shared Google Sheet, for group accountability trackers. The moment a workout ends, an iPhone automation sends the activity name and the day's activity minutes to a small script attached to the Google Sheet, which fills them into the matching date row — in that person's own columns.

Everything in this setup is **completely free**: no Strava account, no server, no subscriptions. Workout data goes only from each person's phone to the group's Google Sheet.

> **Why the change?** Earlier versions of this project pulled workouts from the Strava API using a Python script on a server. Strava has since gated API access behind premium accounts, so workouts now come directly from Apple Health instead — which also removes the need for a server entirely. The old Python version is preserved as [release v1.0.0](../../releases/tag/v1.0.0).

## How It Works

1. You finish a workout on your Apple Watch (or iPhone).
2. A Shortcuts automation for that activity type fires. It looks up today's total **Exercise Minutes** in Apple Health and sends one line — activity name, date, today's minutes so far, and the time — to a small Google Apps Script attached to the group's Google Sheet, along with your personal token.
3. The script recognizes you by your token and appends the entry to a hidden log worksheet. Entries it has already seen are ignored, so nothing is ever double-counted.
4. It then rewrites **your** cells on the matching date row from the log: all of that day's activity names in order, plus the day's minutes (the largest total received for the date, since each entry carries the day's running total).

Because the sheet cells are always recomputed from the log, every delivery is safe: a second workout on the same day joins the first instead of replacing it, and repeated deliveries of the same entry change nothing.

Deliveries are also self-healing. The automation writes each entry to a small **outbox** file and sends the whole outbox, clearing it only after a successful reply — so if the phone had no signal when a workout ended, that entry simply rides along with the next one. Since repeats are ignored server-side, re-sending is always safe.

> **What counts as "minutes"?** The minutes column shows Apple's **Exercise Minutes** for the day — the green-ring metric: movement at or above a brisk walk, from workouts and everyday activity alike. It usually reads slightly higher than the workouts' own durations. (This metric is used because iOS automations can see *that* a workout ended, but not inside it — its duration isn't readable by Shortcuts.)

## Who Sets Up What

The **sheet owner** does the one-time script setup (Part 1) and gives every member two things: the script's web address and that member's personal token. Each **member** builds one small automation on their iPhone **per activity type they do** (Part 2) — climbing, running, and so on — no Google account access, no code, nothing to install. Members don't even need edit access to the spreadsheet; the script writes on the owner's behalf.

---

## Part 1 — Attach the script to the Google Sheet (sheet owner only, one time, on a computer)

1. Open the Google Sheet in a browser.
2. In the menu, click **Extensions → Apps Script**. A code editor opens in a new tab.
3. Delete any code already in the editor, then copy the entire contents of [`Code.gs`](Code.gs) from this repository and paste it in.
4. Edit the `USERS` map near the top: one line per group member. For each person, invent a unique secret token (like a password — letters, numbers, and dashes; no spaces) and set the column number where their activity names should go; their minutes are always written to the next column over. Column numbers: A=1, B=2, … G=7, and so on. Skip over any extra per-person columns your sheet has (weekly counts, notes) — the script only ever touches the two columns starting at the number you give. For example:

   ```javascript
   const USERS = {
     "evan-x7f2":  7,   // Evan  → names in G, minutes in H
     "sam-p9k1":  10,   // Sam   → names in J, minutes in K
     "dana-m3q8": 13,   // Dana  → names in M, minutes in N
   };
   ```
5. Click the **Deploy** button (top right) → **New deployment**.
6. Click the gear icon next to "Select type" and choose **Web app**.
7. Set **Execute as: Me** and **Who has access: Anyone**, then click **Deploy**.

   > "Anyone" only means anyone *with the exact URL and a valid token* can submit entries — the URL is unguessable and each token only reaches its own columns. The sheet's own sharing settings are unaffected.
8. Google will ask you to authorize the script. Click **Authorize access**, pick your account, and if you see a warning that the app isn't verified, click **Advanced → Go to (project name) (unsafe)** → **Allow**. This warning appears because you wrote the script yourself; you are authorizing your own code.
9. Copy the **Web app URL** it gives you (it ends in `/exec`). Send each member the URL and *their* token, privately.

> **Adding a member or editing the code later:** changes don't go live until you click **Deploy → Manage deployments → ✏️ Edit → Version: New version → Deploy**. This is the most commonly missed step in Apps Script. The URL stays the same.

> On its first run the script creates a hidden worksheet named **Forwarder Log** — that's its memory of every entry received. Leave it alone. (Deleting it won't break anything, but previously received entries could then be double-counted if re-sent, and cells rewrite from an empty history.)

## Part 2 — Create the automations (each member, on their iPhone)

You'll create one automation **per activity type you actually do** (e.g. one for Climbing, one for Running). Each is identical except for the trigger's workout type and one typed word. Automations can't be shared between phones, so each member builds their own — the first takes a few minutes, the rest go quickly.

For each activity type:

1. Open the **Shortcuts** app, go to the **Automation** tab, and tap **+**.
2. Choose the **Apple Watch Workout** trigger (on some iOS versions it's just **Workout**). Tap the workout-type field (it defaults to **Any**) and pick the specific activity, e.g. **Climbing**. Set it to fire when the workout **Ends**, and select **Run Immediately** so it never asks for confirmation. Tap **Next**.
3. On the screen that asks what to run, choose **New Blank Automation** — an empty action editor opens that belongs to this automation.
4. Add **Find Health Samples** (search for it):
   - **Type: Exercise Minutes**.
   - Add the filter **Start Date** · **is today**.
   - **Unit: min**, **Group By: Day**, and leave **Limit off**. This returns a single value: today's total exercise minutes.
5. Add a **Text** action. Build one line with four parts separated by the `|` character (type the three `|` yourself):
   - Type the activity name exactly as you want it in the sheet, e.g. `Climbing`.
   - Type `|`, then insert **Current Date** from the variable bar; tap the chip and set **Date Format: Custom** with the format string exactly `MMM dd` (this produces dates like `Feb 02`, matching the sheet).
   - Type `|`, then insert the **Health Samples** variable (the result of step 4).
   - Type `|`, then insert **Current Date** again with the custom date format `HH:mm`. (This time stamp is how the system tells two same-named workouts on one day apart.)
6. Add **Append to Text File**: set the text to the **Text** variable from the previous step, the file path to `outbox.txt` (in the default Shortcuts folder), and turn **Make New Line** on. This is the outbox — it holds any entry that couldn't be sent yet.
7. Add **Get File**: same folder, **File Path** `outbox.txt`.
8. Add **Get Contents of URL**:
   - In the URL field, paste the Web app URL from the sheet owner and add **your personal token** to the end, like this:
     `https://script.google.com/macros/s/…/exec?token=evan-x7f2`
   - Tap the arrow to expand the action. Set **Method: POST**.
   - Under **Request Body**, choose **File** and select the **File** variable from the *Get File* step (the whole outbox, not just today's Text).
9. Add **Delete Files**: set it to delete the **File** from the *Get File* step, and turn **Ask Before Deleting** off. Because this step only runs when the upload succeeded, a failed upload (phone offline, no signal at the gym) leaves the outbox intact — it's re-sent automatically with the next workout, and the server ignores anything it already has.
10. *(Optional)* Add **Show Notification** with the **Contents of URL** as its text, so you get a "Recorded 1 new workout(s)…" confirmation each time.
11. Save the automation. Repeat for your other activity types — same steps, different trigger type and different word at the start of the Text line.

Then finish a short test workout of one of those types — even a 1-minute session. The activity and minutes should appear on today's row within a few seconds. The first run will ask permission to access Health data, files, and to contact `script.google.com` — allow all of them.

> A workout of a type you haven't made an automation for is simply not recorded — you can always add another automation later, or sweep missed ones in by hand (see Part 3).

## Part 3 — Importing history from before setup (optional, one time)

This part is not needed for normal operation — thanks to the outbox, the automations catch up on their own after missed uploads. It exists only for **workouts that happened before the automations were set up**, which they can never see. If the group is happy starting the tracker from today, skip this entirely.

**For a handful of past workouts, no computer is needed:** the outbox is an ordinary text file, so you can add history by hand. Open `outbox.txt` in the **Files** app (in the Shortcuts folder) and type one line per workout — activity, sheet date, that day's total minutes, and a time:

```
Climbing|Jul 12|45|18:00
Outdoor Walk|Jul 10|38|07:30
```

The lines upload along with your next workout, deduplicated like everything else. (The minutes field is the day's total, so for two workouts on one day, give the later line the combined minutes.)

**For months of history**, use the included [`backfill.py`](backfill.py) instead. It converts the export file every iPhone can produce into the same lines — with true per-day workout totals — and posts them through the same endpoint, so duplicates are impossible and it's safe to re-run:

1. On the iPhone: **Health app → tap your picture (top right) → Export All Health Data**, then share `export.zip` to a computer (AirDrop works well).
2. On the computer (any machine with Python 3.9+, no packages needed):

   ```bash
   python3 backfill.py export.zip 'https://script.google.com/macros/s/…/exec' YOUR-TOKEN
   ```

The script only ever sends workouts from the **current calendar year**, no matter how far back the export goes. This is deliberate: the sheet's date rows carry no year and the tracker is recreated each year, so an older year's "Jul 14" workout would otherwise be merged into this year's Jul 14 row. Within the current year, workouts whose date doesn't match a row in the sheet are skipped. (Backfilled days show summed workout durations; days recorded live show Apple's slightly broader exercise-minutes total — close, but not identical metrics.)

## Yearly Rollover

The tracker is recreated each year. Both ways of doing that are safe:

- **A new spreadsheet each year** — repeat Part 1 in the new sheet (paste the script, set up `USERS`, deploy). This produces a **new Web app URL**, so each member updates the URL in their automations once a year; tokens can stay the same.
- **Reusing the same spreadsheet** (clearing or replacing the Tracker rows for the new year) — nothing else changes and members keep the same URL. This is safe because the script stamps every log entry with the year it was received and only ever rewrites cells from the current year's entries, so last year's "Jul 14" can never bleed into this year's row.

Either way, history for the new year starts accumulating from the automations as usual; `backfill.py` can sweep in anything from earlier in the current year.

## Google Sheet Format

The worksheet must have dates pre-populated in column B using the format `MMM dd` with a zero-padded day (e.g., `Feb 02`). The date column is shared by everyone; each member has their own adjacent pair of columns — activity names and minutes — assigned in the `USERS` map. Any other columns (weekly tallies, notes) are never touched by the script.

| Column | Content |
|--------|---------|
| B | Date (`Feb 02`) — shared |
| G / H | Member 1: activity names / day's active minutes |
| J / K | Member 2: activity names / day's active minutes |
| … | one pair per member |

Multiple workouts on the same date appear as one comma-separated list of names, in time order; the minutes cell shows the day's total.

## Configuration

Constants at the top of `Code.gs` (remember to deploy a **new version** after editing — see the note in Part 1):

| Constant | Default | Description |
|----------|---------|-------------|
| `USERS` | *(examples)* | Map of each member's secret token to the column number for their activity names; minutes go in the next column over |
| `WORKSHEET_NAME` | `"Tracker"` | Name of the worksheet tab to write to |
| `DATE_COLUMN` | `2` (column B) | Column containing the `MMM dd` dates |
| `LOG_SHEET_NAME` | `"Forwarder Log"` | Name of the hidden log worksheet the script maintains |

## Troubleshooting

- **The automation never fires** — it triggers on live-tracked workouts (Apple Watch, or the iPhone's own workout tracking) of the exact type it was created for. Workouts of other types need their own automations, and workouts typed into Health/Fitness manually after the fact don't trigger anything; sweep those in via Part 3.
- **"Recorded 0 new workout(s)"** — the entry was already received earlier (a repeat delivery); the sheet is unchanged, which is exactly right.
- **A missed workout showed up later, bundled with the next one** — that's the outbox catching up after the phone was offline. Working as intended.
- **"…updated 0 row(s)"** — the entry's date didn't match any value in column B. Check that column B shows dates exactly like `Feb 02` (zero-padded day, matching `MMM dd`), and note that the phone's language affects month names — a phone not set to English writes months the sheet won't match.
- **"Error: invalid token"** — the token in the automation's URL doesn't match any entry in the `USERS` map. Check for typos, and if the member was just added, make sure a **new version** was deployed.
- **Minutes look like 0 or far too small** — in *Find Health Samples*, make sure the **Start Date is today** filter and **Group By: Day** are set and **Limit is off**.
- **Minutes look higher than the workouts themselves** — expected: the minutes column is Apple's exercise-minutes metric for the whole day (all brisk movement), not the workouts' summed durations.
- **Entries land in the wrong columns** — two members are using the same token, or the column number in `USERS` is wrong. Each member's token must be unique.
- **A day's cell looks wrong and won't fix itself** — the source of truth is the hidden **Forwarder Log** sheet (unhide it via the sheet tabs). Deleting a bad log row and re-sending any entry for that date rewrites the cells.
- **Response looks like an HTML page or an error about `doPost`** — the deployment is stale or the URL is wrong; make sure you're using the `/exec` URL from an active Web app deployment, and re-deploy a new version after any code edit.
