"""Application database: connections and migrations.

Separate file from the analytics database on purpose. Analytics is append-heavy,
purged on a schedule and cheap to lose; balances are transactional and are the
one thing in this app a user would notice going missing. The periodic event
purge has no business running next to them.

No ORM and no Alembic: Alembic drags in SQLAlchemy, which this project does not
use, for one small set of tables. Migrations are numbered .sql files applied in
order against a `schema_version` table.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

_migrated: set[Path] = set()


def _apply_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version("
        "version INTEGER PRIMARY KEY, applied_at INTEGER NOT NULL DEFAULT (strftime('%s','now')))"
    )
    applied = {r[0] for r in conn.execute("SELECT version FROM schema_version")}
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version = int(path.name.split("_", 1)[0])
        if version in applied:
            continue
        conn.executescript(path.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO schema_version(version) VALUES(?)", (version,))
    conn.commit()


@contextmanager
def connect(immediate: bool = False):
    """A connection per operation.

    `immediate=True` takes the write lock up front. Every read-modify-write on a
    balance must use it: with SQLite's default deferred transactions two writers
    can both read a remaining count of 1 and both decrement it.
    """
    path = get_settings().app_db_path
    conn = sqlite3.connect(path, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        if path not in _migrated:
            conn.execute("PRAGMA journal_mode=WAL")
            _apply_migrations(conn)
            _migrated.add(path)

        conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        try:
            yield conn
        except Exception:
            conn.execute("ROLLBACK")
            raise
        else:
            conn.execute("COMMIT")
    finally:
        conn.close()


def reset_for_tests() -> None:
    """Forget which files were migrated, so a fresh tmp database gets a schema."""
    _migrated.clear()
