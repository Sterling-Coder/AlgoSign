"""SQLite store — the app's first piece of persistent, per-user state.

Stateless until now: every page was request→fetch→render. Alerts, paper bots,
and the prediction track record need state that survives when no one's on the
page, so this is where it lives. SQLite in WAL mode handles our concurrency
(request threads + the scheduler thread) without a server.

One connection per call. SQLite + WAL makes that cheap and safe; no pool needed
at this scale. All writes are short and parameterised.
"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "algosign.db"
_INIT_LOCK = threading.Lock()
_initialised = False

_SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    device       TEXT    NOT NULL,
    symbol       TEXT    NOT NULL,
    kind         TEXT    NOT NULL,          -- price | pct_change | signal
    direction    TEXT    NOT NULL,          -- above | below
    threshold    REAL    NOT NULL,
    note         TEXT,
    active       INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT    NOT NULL,
    last_fired_at TEXT,
    last_value   REAL
);
CREATE INDEX IF NOT EXISTS idx_alerts_device ON alerts(device);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(active);

CREATE TABLE IF NOT EXISTS bot_positions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device      TEXT    NOT NULL,
    symbol      TEXT    NOT NULL,
    side        TEXT    NOT NULL,           -- long | short
    qty         REAL    NOT NULL,
    entry_price REAL    NOT NULL,
    stop        REAL,
    target      REAL,
    status      TEXT    NOT NULL,           -- open | closed | halted
    opened_at   TEXT    NOT NULL,
    closed_at   TEXT,
    exit_price  REAL,
    pnl         REAL
);
CREATE INDEX IF NOT EXISTS idx_bot_device ON bot_positions(device);
CREATE INDEX IF NOT EXISTS idx_bot_status ON bot_positions(status);

CREATE TABLE IF NOT EXISTS predictions_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT    NOT NULL,
    made_at     TEXT    NOT NULL,
    horizon     INTEGER NOT NULL,
    direction   TEXT    NOT NULL,
    probability REAL    NOT NULL,
    entry_price REAL    NOT NULL,
    resolve_on  TEXT    NOT NULL,           -- date the call is due
    outcome     TEXT,                       -- correct | wrong | (null = pending)
    resolved_at TEXT,
    exit_price  REAL,
    UNIQUE(symbol, made_at, horizon)
);
CREATE INDEX IF NOT EXISTS idx_pred_pending ON predictions_log(outcome);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init() -> None:
    """Create tables once. Safe to call on every startup."""
    global _initialised
    with _INIT_LOCK:
        if _initialised:
            return
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = _connect()
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()
        _initialised = True


def query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    conn = _connect()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def execute(sql: str, params: tuple = ()) -> int:
    """Run a write; return lastrowid (for INSERT) or rowcount."""
    conn = _connect()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid or cur.rowcount
    finally:
        conn.close()
