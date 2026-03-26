"""
Lunch Assistant Database (Layer 3 - Execution)
SQLite persistence for order history, blacklist, suggestions, and user config.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "lunch_history.db"


def _connect():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS user_config (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS order_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            order_date      DATE NOT NULL,
            restaurant_name TEXT NOT NULL,
            restaurant_code TEXT,
            items           TEXT,
            cuisine         TEXT,
            rating_given    REAL,
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS restaurant_blacklist (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_name TEXT NOT NULL,
            restaurant_code TEXT,
            reason          TEXT,
            blacklisted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS daily_suggestions (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            suggestion_date       DATE NOT NULL,
            restaurants_suggested TEXT NOT NULL,
            restaurant_picked     TEXT,
            created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


# ── User Config ───────────────────────────────────────────────────────

def save_config(key: str, value: str):
    conn = _connect()
    conn.execute(
        "INSERT INTO user_config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
        (key, value, value),
    )
    conn.commit()
    conn.close()


def get_config(key: str, default: str = None) -> str | None:
    conn = _connect()
    row = conn.execute("SELECT value FROM user_config WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def get_all_config() -> dict:
    conn = _connect()
    rows = conn.execute("SELECT key, value FROM user_config").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


# ── Order History ─────────────────────────────────────────────────────

def save_order(
    restaurant_name: str,
    restaurant_code: str = None,
    items: list[str] = None,
    cuisine: str = None,
    rating_given: float = None,
    notes: str = None,
    order_date: date = None,
):
    conn = _connect()
    conn.execute(
        """INSERT INTO order_history
           (order_date, restaurant_name, restaurant_code, items, cuisine, rating_given, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            (order_date or date.today()).isoformat(),
            restaurant_name,
            restaurant_code,
            json.dumps(items) if items else None,
            cuisine,
            rating_given,
            notes,
        ),
    )
    conn.commit()
    conn.close()


def get_recent_orders(days: int = 7) -> list[dict]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM order_history WHERE order_date >= ? ORDER BY order_date DESC",
        (cutoff,),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("items"):
            d["items"] = json.loads(d["items"])
        result.append(d)
    return result


def get_all_orders() -> list[dict]:
    conn = _connect()
    rows = conn.execute("SELECT * FROM order_history ORDER BY order_date DESC").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("items"):
            d["items"] = json.loads(d["items"])
        result.append(d)
    return result


# ── Restaurant Blacklist ──────────────────────────────────────────────

def blacklist_restaurant(restaurant_name: str, restaurant_code: str = None, reason: str = None):
    conn = _connect()
    conn.execute(
        "INSERT INTO restaurant_blacklist (restaurant_name, restaurant_code, reason) VALUES (?, ?, ?)",
        (restaurant_name, restaurant_code, reason),
    )
    conn.commit()
    conn.close()


def is_blacklisted(restaurant_name: str = None, restaurant_code: str = None) -> bool:
    conn = _connect()
    if restaurant_code:
        row = conn.execute(
            "SELECT 1 FROM restaurant_blacklist WHERE restaurant_code = ?", (restaurant_code,)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT 1 FROM restaurant_blacklist WHERE LOWER(restaurant_name) = LOWER(?)",
            (restaurant_name,),
        ).fetchone()
    conn.close()
    return row is not None


def get_blacklist() -> list[dict]:
    conn = _connect()
    rows = conn.execute("SELECT * FROM restaurant_blacklist ORDER BY blacklisted_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def remove_from_blacklist(restaurant_name: str):
    conn = _connect()
    conn.execute(
        "DELETE FROM restaurant_blacklist WHERE LOWER(restaurant_name) = LOWER(?)",
        (restaurant_name,),
    )
    conn.commit()
    conn.close()


# ── Daily Suggestions ─────────────────────────────────────────────────

def save_daily_suggestions(restaurants: list[dict], suggestion_date: date = None):
    conn = _connect()
    conn.execute(
        "INSERT INTO daily_suggestions (suggestion_date, restaurants_suggested) VALUES (?, ?)",
        (
            (suggestion_date or date.today()).isoformat(),
            json.dumps(restaurants),
        ),
    )
    conn.commit()
    conn.close()


def get_today_suggestions() -> list[dict] | None:
    conn = _connect()
    row = conn.execute(
        "SELECT restaurants_suggested FROM daily_suggestions WHERE suggestion_date = ? ORDER BY id DESC LIMIT 1",
        (date.today().isoformat(),),
    ).fetchone()
    conn.close()
    if row:
        return json.loads(row["restaurants_suggested"])
    return None


def mark_suggestion_picked(restaurant_name: str, suggestion_date: date = None):
    conn = _connect()
    conn.execute(
        "UPDATE daily_suggestions SET restaurant_picked = ? WHERE suggestion_date = ? AND restaurant_picked IS NULL",
        (restaurant_name, (suggestion_date or date.today()).isoformat()),
    )
    conn.commit()
    conn.close()


# Auto-init on import
init_db()
