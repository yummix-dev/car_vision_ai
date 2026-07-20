"""Funnel analytics: one SQLite table of events, plus the queries /admin renders.

Why events and not entities: the most valuable fact about a funnel is where
people *stop*, and stopping produces no request. Only the client can report it,
so `POST /api/events` accepts what the browser sends — which is exactly why the
event vocabulary is closed and the timestamp is assigned here rather than taken
from the payload.

No ORM and no migration tool: one table, created on first use.
"""

import asyncio
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from app.config import get_settings

# Closed vocabulary. An unknown name is rejected rather than stored: a typo that
# silently lands in the table splits a funnel step in two and the numbers stop
# adding up long after anyone remembers why.
EVENT_NAMES = frozenset(
    {
        "screen_view",
        "photo_uploaded",
        "vehicle_confirmed",
        "vehicle_corrected",
        "category_picked",
        "product_opened",
        "option_changed",
        "generation_started",
        "generation_done",
        "generation_failed",
        "result_saved",
        "result_shared",
        "cart_add",
        "cart_remove",
        "booking_submitted",
    }
)

# The ordered funnel rendered on /admin. Each step counts distinct sessions that
# reached it, so revisiting a screen never inflates a step.
FUNNEL = [
    ("category_picked", "Выбрал раздел"),
    ("photo_uploaded", "Загрузил фото"),
    ("product_opened", "Открыл товар"),
    ("generation_started", "Запустил генерацию"),
    ("generation_done", "Увидел результат"),
    ("cart_add", "Добавил в корзину"),
    ("booking_submitted", "Оставил заявку"),
]

MAX_BATCH = 50
MAX_PAYLOAD_CHARS = 2000

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  session_id TEXT NOT NULL,
  user_id INTEGER,
  name TEXT NOT NULL,
  screen TEXT,
  category_id TEXT,
  product_id TEXT,
  payload TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_name_ts ON events(name, ts);
"""

_initialised: set[Path] = set()


@contextmanager
def _connect():
    """A fresh connection per operation.

    sqlite3 connections are not safe to share across threads, and everything
    here runs in a worker thread. WAL keeps the periodic cleanup from blocking
    ingestion.
    """
    path = get_settings().analytics_db_path
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        if path not in _initialised:
            conn.executescript(_SCHEMA)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.commit()
            _initialised.add(path)
        yield conn
    finally:
        conn.close()


def reset_for_tests() -> None:
    """Forget which files have been initialised, so a new tmp db gets a schema."""
    _initialised.clear()


def _record_sync(events: list[dict], user_id: int | None) -> int:
    now = int(time.time())
    rows = [
        (
            now,  # server clock: a phone's is not evidence of anything
            e["session_id"],
            user_id,
            e["name"],
            e.get("screen"),
            e.get("category_id"),
            e.get("product_id"),
            json.dumps(e.get("payload"), ensure_ascii=False)
            if e.get("payload") is not None
            else None,
        )
        for e in events
    ]
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO events(ts,session_id,user_id,name,screen,category_id,"
            "product_id,payload) VALUES(?,?,?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
    return len(rows)


async def record(events: list[dict], user_id: int | None = None) -> int:
    """Store a batch. sqlite3 is synchronous, so it goes to a worker thread."""
    if not get_settings().analytics_enabled or not events:
        return 0
    return await asyncio.to_thread(_record_sync, events, user_id)


def record_server_event(
    name: str, session_id: str = "server", **fields
) -> None:
    """Fire-and-forget from server-side code paths (bookings, generation).

    Deliberately swallows failures: analytics must never be the reason a booking
    or a render fails.
    """
    if not get_settings().analytics_enabled:
        return
    try:
        _record_sync([{"session_id": session_id, "name": name, **fields}], None)
    except Exception:  # noqa: BLE001 - analytics is never load-bearing
        pass


# ── queries behind /admin ─────────────────────────────────────


def _since(days: int) -> int:
    return int(time.time()) - days * 86400


def funnel(days: int = 7) -> list[dict]:
    """Sessions reaching each step, with conversion from the previous one."""
    since = _since(days)
    with _connect() as conn:
        counts = {
            name: conn.execute(
                "SELECT COUNT(DISTINCT session_id) c FROM events "
                "WHERE name=? AND ts>=?",
                (name, since),
            ).fetchone()["c"]
            for name, _ in FUNNEL
        }

    out, previous = [], None
    for name, label in FUNNEL:
        n = counts[name]
        out.append(
            {
                "name": name,
                "label": label,
                "sessions": n,
                # None on the first step: there is nothing to convert from.
                "conversion": None if previous is None else _pct(n, previous),
                "dropped": None if previous is None else max(0, previous - n),
            }
        )
        previous = n
    return out


def _pct(part: int, whole: int) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


def top(field: str, days: int = 7, limit: int = 8) -> list[dict]:
    if field not in {"category_id", "product_id"}:
        raise ValueError(f"Not a groupable field: {field}")
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT {field} AS key, COUNT(DISTINCT session_id) AS sessions "  # noqa: S608 - field is whitelisted above
            "FROM events WHERE ts>=? AND "
            f"{field} IS NOT NULL AND {field}!='' "
            "GROUP BY key ORDER BY sessions DESC LIMIT ?",
            (_since(days), limit),
        ).fetchall()
    return [dict(r) for r in rows]


def totals(days: int = 7) -> dict:
    since = _since(days)
    with _connect() as conn:
        one = lambda sql, *a: conn.execute(sql, a).fetchone()[0]  # noqa: E731
        sessions = one(
            "SELECT COUNT(DISTINCT session_id) FROM events WHERE ts>=?", since
        )
        done = one(
            "SELECT COUNT(*) FROM events WHERE name='generation_done' AND ts>=?",
            since,
        )
        failed = one(
            "SELECT COUNT(*) FROM events WHERE name='generation_failed' AND ts>=?",
            since,
        )
        bookings = one(
            "SELECT COUNT(*) FROM events WHERE name='booking_submitted' AND ts>=?",
            since,
        )
    attempted = done + failed
    return {
        "sessions": sessions,
        "generations": attempted,
        "failure_rate": _pct(failed, attempted),
        "bookings": bookings,
    }


def purge_old(days: int) -> int:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM events WHERE ts<?", (_since(days),))
        conn.commit()
        return cur.rowcount
