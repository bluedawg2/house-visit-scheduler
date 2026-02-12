import sqlite3
import secrets
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calendar.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS config (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS availability (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            start_date TEXT NOT NULL,
            end_date   TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_active  INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS visit_requests (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_name    TEXT NOT NULL,
            visitor_email   TEXT NOT NULL,
            check_in_date   TEXT NOT NULL,
            check_out_date  TEXT NOT NULL,
            notes           TEXT DEFAULT '',
            status          TEXT NOT NULL DEFAULT 'pending',
            admin_notes     TEXT DEFAULT '',

            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            responded_at    TEXT DEFAULT NULL
        );
    """)
    conn.commit()
    conn.close()


# --- Config ---

def get_or_create_admin_key() -> str:
    conn = _get_conn()
    row = conn.execute("SELECT value FROM config WHERE key = 'admin_key'").fetchone()
    if row:
        key = row["value"]
        conn.close()
        return key
    new_key = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO config (key, value) VALUES ('admin_key', ?)", (new_key,))
    conn.commit()
    conn.close()
    return new_key


# --- Availability ---

def add_availability(start_date: str, end_date: str) -> int:
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO availability (start_date, end_date) VALUES (?, ?)",
        (start_date, end_date),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_all_availability() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, start_date, end_date, created_at FROM availability WHERE is_active = 1 ORDER BY start_date"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def remove_availability(avail_id: int) -> None:
    conn = _get_conn()
    conn.execute("UPDATE availability SET is_active = 0 WHERE id = ?", (avail_id,))
    # Auto-reject pending requests that no longer fall within any active availability
    pending = conn.execute(
        "SELECT id, check_in_date, check_out_date FROM visit_requests WHERE status = 'pending'"
    ).fetchall()
    for req in pending:
        if not _is_range_covered(conn, req["check_in_date"], req["check_out_date"]):
            conn.execute(
                "UPDATE visit_requests SET status = 'rejected', admin_notes = 'Availability removed', responded_at = ? WHERE id = ?",
                (datetime.now().isoformat(), req["id"]),
            )
    conn.commit()
    conn.close()


def _is_range_covered(conn, check_in: str, check_out: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM availability WHERE is_active = 1 AND start_date <= ? AND end_date >= ?",
        (check_in, check_out),
    ).fetchone()
    return row["cnt"] > 0


# --- Visit Requests ---

def create_visit_request(name: str, email: str, check_in: str, check_out: str, notes: str) -> int:
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO visit_requests (visitor_name, visitor_email, check_in_date, check_out_date, notes) VALUES (?, ?, ?, ?, ?)",
        (name, email, check_in, check_out, notes),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_pending_requests() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM visit_requests WHERE status = 'pending' ORDER BY created_at"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_requests() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM visit_requests ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_accepted_requests() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM visit_requests WHERE status = 'accepted' ORDER BY check_in_date"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_requests_by_email(email: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM visit_requests WHERE visitor_email = ? ORDER BY created_at DESC",
        (email,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_request_status(request_id: int, status: str, admin_notes: str = "") -> None:
    conn = _get_conn()
    conn.execute(
        "UPDATE visit_requests SET status = ?, admin_notes = ?, responded_at = ? WHERE id = ?",
        (status, admin_notes, datetime.now().isoformat(), request_id),
    )
    conn.commit()
    conn.close()


# --- Validation ---

def is_range_within_availability(check_in: str, check_out: str) -> bool:
    conn = _get_conn()
    result = _is_range_covered(conn, check_in, check_out)
    conn.close()
    return result


def has_overlap_conflict(check_in: str, check_out: str) -> bool:
    conn = _get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM visit_requests WHERE status = 'accepted' AND check_in_date <= ? AND check_out_date >= ?",
        (check_out, check_in),
    ).fetchone()
    conn.close()
    return row["cnt"] > 0


# --- SMTP Config ---

_SMTP_KEYS = ("smtp_server", "smtp_port", "smtp_username", "smtp_password", "smtp_from_address")


def get_smtp_config() -> dict | None:
    """Return SMTP config dict or None if not configured."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT key, value FROM config WHERE key IN (?, ?, ?, ?, ?)", _SMTP_KEYS
    ).fetchall()
    conn.close()
    if len(rows) < len(_SMTP_KEYS):
        return None
    cfg = {r["key"].removeprefix("smtp_"): r["value"] for r in rows}
    if not all(cfg.values()):
        return None
    return cfg


def save_smtp_config(server: str, port: str, username: str, password: str, from_address: str) -> None:
    conn = _get_conn()
    for key, value in zip(_SMTP_KEYS, (server, port, username, password, from_address)):
        conn.execute(
            "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (key, value, value),
        )
    conn.commit()
    conn.close()


# --- Stay Limits ---

def get_stay_limits() -> tuple:
    """Return (min_nights, max_nights) from config. None means no limit."""
    conn = _get_conn()
    min_row = conn.execute("SELECT value FROM config WHERE key = 'min_stay_nights'").fetchone()
    max_row = conn.execute("SELECT value FROM config WHERE key = 'max_stay_nights'").fetchone()
    conn.close()
    min_val = int(min_row["value"]) if min_row and min_row["value"] else None
    max_val = int(max_row["value"]) if max_row and max_row["value"] else None
    # Treat 0 as "no limit"
    return (min_val if min_val and min_val > 0 else None,
            max_val if max_val and max_val > 0 else None)


def save_stay_limits(min_nights: int, max_nights: int) -> None:
    conn = _get_conn()
    for key, val in [("min_stay_nights", str(min_nights)), ("max_stay_nights", str(max_nights))]:
        conn.execute(
            "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (key, val, val),
        )
    conn.commit()
    conn.close()
