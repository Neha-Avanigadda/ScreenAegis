"""
Logger (SQLite)
---------------
Stores detection events and recorder-process alerts in data/logs.db.

PRIVACY DESIGN: we log the CATEGORY and COUNT of sensitive items (e.g.
"EMAIL: 1"), never the sensitive text itself. A security tool whose log
file contains the credit card numbers would defeat its own purpose.
"""

import json
import os
import sqlite3
import threading
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(BASE_DIR, "..", "data", "logs.db")

_lock = threading.Lock()


def _connect(db_path):
    return sqlite3.connect(db_path)


def init_db(db_path=DEFAULT_DB):
    """Creates the database and tables if they don't exist yet."""
    db_path = os.path.abspath(db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with _lock, _connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp     TEXT NOT NULL,
                trigger       TEXT,
                active_app    TEXT,
                items_masked  INTEGER,
                categories    TEXT,
                ocr_seconds   REAL,
                total_seconds REAL,
                masked_path   TEXT
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS process_events (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp    TEXT NOT NULL,
                process_name TEXT,
                pid          INTEGER
            )""")
    return db_path


def log_detection(trigger, active_app, flagged, timings, masked_path="",
                  db_path=DEFAULT_DB):
    """Records one capture event. `flagged` is the list from pattern_matcher."""
    counts = {}
    for item in flagged:
        counts[item["category"]] = counts.get(item["category"], 0) + 1

    with _lock, _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO detections (timestamp, trigger, active_app, items_masked,"
            " categories, ocr_seconds, total_seconds, masked_path)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), trigger, active_app,
             len(flagged), json.dumps(counts), timings.get("ocr"),
             timings.get("total"), masked_path),
        )


def log_process_event(process_name, pid, db_path=DEFAULT_DB):
    with _lock, _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO process_events (timestamp, process_name, pid) VALUES (?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), process_name, pid),
        )


def get_recent_detections(limit=20, db_path=DEFAULT_DB):
    with _lock, _connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM detections ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_stats(db_path=DEFAULT_DB):
    """Summary numbers for the dashboard and your Results slide."""
    today = datetime.now().strftime("%Y-%m-%d")
    with _lock, _connect(db_path) as conn:
        total, masked, avg_total = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(items_masked),0), AVG(total_seconds)"
            " FROM detections").fetchone()
        today_count = conn.execute(
            "SELECT COUNT(*) FROM detections WHERE timestamp LIKE ?",
            (today + "%",)).fetchone()[0]
        last = conn.execute(
            "SELECT timestamp FROM detections ORDER BY id DESC LIMIT 1").fetchone()
        proc_alerts = conn.execute(
            "SELECT COUNT(*) FROM process_events").fetchone()[0]
        cat_rows = conn.execute("SELECT categories FROM detections").fetchall()

    by_category = {}
    for (cat_json,) in cat_rows:
        for cat, n in json.loads(cat_json or "{}").items():
            by_category[cat] = by_category.get(cat, 0) + n

    return {
        "total_captures": total,
        "total_items_masked": masked,
        "captures_today": today_count,
        "last_detection": last[0] if last else None,
        "avg_scan_seconds": round(avg_total, 2) if avg_total else None,
        "recorder_alerts": proc_alerts,
        "by_category": by_category,
    }
