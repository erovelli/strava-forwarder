/**
 * health-forwarder — Google Apps Script web app.
 *
 * Receives workouts posted by the "Health Forwarder" iPhone Shortcut and
 * writes them into the tracker worksheet. Each line of the request body is
 * one workout, with fields separated by "|":
 *
 *   Outdoor Run|Feb 02|43
 *   (workout type | sheet date | duration in minutes)
 *
 * The sheet owner deploys this script once. Each user posts with their own
 * secret token, which doubles as their identity: it selects the column pair
 * their workouts are written to.
 */

// --- Configuration ---

// One entry per user: their secret token mapped to the column number where
// their activity names go (durations go in the next column over; G = 7).
// Invent a unique token per person and hand it to them privately. After
// editing this map, deploy a new version for the change to take effect.
const USERS = {
  "change-me-1": 7, // columns G/H
  "change-me-2": 9, // columns I/J
};

const WORKSHEET_NAME = "Tracker";
const DATE_COLUMN = 2; // column B: dates formatted like "Feb 02"

// --- Web app entry point ---

function doPost(e) {
  const nameColumn = e.parameter ? USERS[e.parameter.token] : undefined;
  if (!nameColumn) {
    return reply("Error: invalid token");
  }

  const workouts = parseWorkouts(e.postData ? e.postData.contents : "");
  if (workouts.length === 0) {
    return reply("Error: no workouts found in request body");
  }

  const updated = writeWorkouts(workouts, nameColumn);
  return reply("Updated " + updated + " row(s) in " + WORKSHEET_NAME);
}

// --- Workout parsing and sheet writing ---

function parseWorkouts(body) {
  return body
    .split("\n")
    .map(function (line) { return line.trim(); })
    .filter(function (line) { return line.indexOf("|") !== -1; })
    .map(function (line) {
      const parts = line.split("|").map(function (p) { return p.trim(); });
      return {
        name: parts[0],
        date: parts[1],
        minutes: Math.round(parseFloat(parts[2])) || 0,
      };
    });
}

function writeWorkouts(workouts, nameColumn) {
  const sheet =
    SpreadsheetApp.getActiveSpreadsheet().getSheetByName(WORKSHEET_NAME);
  const dates = sheet
    .getRange(1, DATE_COLUMN, sheet.getLastRow(), 1)
    .getDisplayValues()
    .map(function (row) { return row[0]; });

  const byRow = {};
  workouts.forEach(function (workout) {
    const row = dates.indexOf(workout.date) + 1;
    if (row === 0) return; // no row for this date: skip the workout
    (byRow[row] = byRow[row] || []).push(workout);
  });

  Object.keys(byRow).forEach(function (row) {
    const day = byRow[row];
    const names = day.map(function (w) { return w.name; }).join(", ");
    const total = day.reduce(function (sum, w) { return sum + w.minutes; }, 0);
    sheet.getRange(Number(row), nameColumn, 1, 2).setValues([[names, total]]);
  });

  return Object.keys(byRow).length;
}

function reply(message) {
  return ContentService.createTextOutput(message);
}
