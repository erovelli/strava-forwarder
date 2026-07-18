/**
 * health-forwarder — Google Apps Script web app.
 *
 * Receives daily exercise totals posted by the "Health Forwarder" iPhone
 * Shortcut and writes them into the tracker worksheet. Each line of the
 * request body is one day, with fields separated by "|":
 *
 *   Feb 02|43
 *   (sheet date | exercise minutes)
 *
 * The sheet owner deploys this script once. Each user posts with their own
 * secret token, which doubles as their identity: it selects the column
 * their minutes are written to.
 */

// --- Configuration ---

// One entry per user: their secret token mapped to the column number where
// their exercise minutes go (A = 1, B = 2, ... H = 8). Invent a unique token
// per person and hand it to them privately. After editing this map, deploy
// a new version for the change to take effect.
const USERS = {
  "change-me-1": 8, // column H
  "change-me-2": 10, // column J
};

const WORKSHEET_NAME = "Tracker";
const DATE_COLUMN = 2; // column B: dates formatted like "Feb 02"

// --- Web app entry point ---

function doPost(e) {
  const minutesColumn = e.parameter ? USERS[e.parameter.token] : undefined;
  if (!minutesColumn) {
    return reply("Error: invalid token");
  }

  const days = parseDays(e.postData ? e.postData.contents : "");
  if (days.length === 0) {
    return reply("Error: no exercise data found in request body");
  }

  const updated = writeDays(days, minutesColumn);
  return reply("Updated " + updated + " row(s) in " + WORKSHEET_NAME);
}

// --- Parsing and sheet writing ---

function parseDays(body) {
  return body
    .split("\n")
    .map(function (line) { return line.trim(); })
    .filter(function (line) { return line.indexOf("|") !== -1; })
    .map(function (line) {
      const parts = line.split("|").map(function (p) { return p.trim(); });
      return { date: parts[0], minutes: Math.round(parseFloat(parts[1])) || 0 };
    });
}

function writeDays(days, minutesColumn) {
  const sheet =
    SpreadsheetApp.getActiveSpreadsheet().getSheetByName(WORKSHEET_NAME);
  const dates = sheet
    .getRange(1, DATE_COLUMN, sheet.getLastRow(), 1)
    .getDisplayValues()
    .map(function (row) { return row[0]; });

  // Lines sharing a date are summed, so the payload is correct whether the
  // Shortcut grouped samples by day or sent them raw.
  const byRow = {};
  days.forEach(function (day) {
    const row = dates.indexOf(day.date) + 1;
    if (row === 0) return; // no row for this date: skip
    byRow[row] = (byRow[row] || 0) + day.minutes;
  });

  Object.keys(byRow).forEach(function (row) {
    sheet.getRange(Number(row), minutesColumn).setValue(byRow[row]);
  });

  return Object.keys(byRow).length;
}

function reply(message) {
  return ContentService.createTextOutput(message);
}
