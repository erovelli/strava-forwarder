/**
 * health-forwarder — Google Apps Script web app.
 *
 * Receives workouts posted by the "Health Forwarder" iPhone Shortcut, which
 * runs automatically each time a workout ends. Each line of the request
 * body is one workout, with fields separated by "|":
 *
 *   Climbing|Jul 14|43|18:32
 *   (activity type | sheet date | day's total minutes so far | entry time)
 *
 * The minutes field is cumulative for the day — the automation posts the
 * day's activity total at each workout's end — so a date's cell shows the
 * largest value received for it, while activity names accumulate per entry.
 *
 * Accepted workouts are appended to a log worksheet, and the visible cells
 * for that user and date are recomputed from the log. The log is what makes
 * separate posts safe: a second workout on the same day is added alongside
 * the first, and a workout that was already received is ignored.
 *
 * Sheet dates carry no year and the tracker is recreated yearly, so log
 * entries are stamped with the year they were received and cells are only
 * recomputed from the current year's entries. A spreadsheet reused across
 * years therefore never mixes last year's workouts into this year's rows.
 */

// --- Configuration ---

// One entry per user: their secret token mapped to the column number where
// their activity names go; minutes go in the next column over (A = 1, B = 2,
// ... G = 7). Invent a unique token per person and hand it to them
// privately. After editing this map, deploy a new version for the change to
// take effect.
const USERS = {
  "change-me-1": 7, // columns G/H
  "change-me-2": 10, // columns J/K
};

const WORKSHEET_NAME = "Tracker";
const DATE_COLUMN = 2; // column B: dates formatted like "Feb 02"
const LOG_SHEET_NAME = "Forwarder Log"; // created and hidden automatically

// --- Web app entry point ---

function doPost(e) {
  try {
    return handleRequest(e);
  } catch (err) {
    // Always answer in plain text: the Shortcut and backfill script parse
    // the reply, and an uncaught throw would return Google's HTML error page.
    return reply(`Error: ${err.message}`);
  }
}

function handleRequest(e) {
  const nameColumn = e.parameter ? USERS[e.parameter.token] : undefined;
  if (!nameColumn) {
    return reply("Error: invalid token");
  }

  const workouts = parseWorkouts(e.postData ? e.postData.contents : "");
  if (workouts.length === 0) {
    return reply("Error: no workouts found in request body");
  }

  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const { added, updated } = recordWorkouts(e.parameter.token, nameColumn, workouts);
    return reply(
      `Recorded ${added} new workout(s), updated ${updated} row(s) in ${WORKSHEET_NAME}`
    );
  } finally {
    lock.releaseLock();
  }
}

// --- Parsing ---

function parseWorkouts(body) {
  return body.split("\n").map(parseLine).filter(Boolean);
}

function parseLine(line) {
  const parts = String(line).split("|").map((p) => p.trim());
  if (parts.length < 3 || !parts[0] || !parts[1]) return null;
  const minutes = Math.round(parseFloat(parts[2])) || 0;
  const start = parts[3] || "";
  return {
    name: parts[0],
    date: parts[1],
    minutes,
    start,
    // Canonical form used for duplicate detection in the log.
    line: `${parts[0]}|${parts[1]}|${minutes}|${start}`,
  };
}

// --- Log and sheet writing ---

function recordWorkouts(token, nameColumn, workouts) {
  const year = new Date().getFullYear();
  const doc = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = doc.getSheetByName(WORKSHEET_NAME);
  if (!sheet) {
    throw new Error(`worksheet "${WORKSHEET_NAME}" not found`);
  }

  const log = doc.getSheetByName(LOG_SHEET_NAME) || createLog(doc);
  const logRows = log.getDataRange().getValues();

  const seen = new Set(logRows.map((r) => logKey(r[0], r[3], r[1])));
  const fresh = workouts.filter((w) => !seen.has(logKey(token, year, w.line)));
  if (fresh.length > 0) {
    const received = new Date();
    log
      .getRange(log.getLastRow() + 1, 1, fresh.length, 4)
      .setValues(fresh.map((w) => [token, w.line, received, year]));
  }

  // Recompute every date mentioned in this post from the current year's log
  // entries, so cells always reflect all of the day's workouts regardless of
  // delivery order — and never a previous year's workouts on the same date.
  const postedDates = new Set(workouts.map((w) => w.date));

  const mine = logRows
    .concat(fresh.map((w) => [token, w.line, null, year]))
    .filter((r) => r[0] === token && Number(r[3]) === year)
    .map((r) => parseLine(r[1]))
    .filter((w) => w && postedDates.has(w.date));

  const dates = sheet
    .getRange(1, DATE_COLUMN, sheet.getLastRow(), 1)
    .getDisplayValues()
    .map(([d]) => d);

  let updated = 0;
  for (const date of postedDates) {
    const row = dates.indexOf(date) + 1;
    if (row === 0) continue; // no row for this date: skip
    const day = mine
      .filter((w) => w.date === date)
      .sort((a, b) => a.start.localeCompare(b.start));
    const names = day.map((w) => w.name).join(", ");
    // Minutes are day-cumulative, so the day's total is the largest value.
    const total = day.reduce((max, w) => Math.max(max, w.minutes), 0);
    sheet.getRange(row, nameColumn, 1, 2).setValues([[names, total]]);
    updated++;
  }

  return { added: fresh.length, updated };
}

function createLog(doc) {
  const log = doc.insertSheet(LOG_SHEET_NAME);
  log.appendRow(["token", "workout", "received", "year"]);
  log.hideSheet();
  return log;
}

function logKey(token, year, line) {
  return `${token}|${year}|${line}`;
}

function reply(message) {
  return ContentService.createTextOutput(message);
}
