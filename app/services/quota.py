"""AI try-on quotas: free allowances per category, a shared bonus balance, and
the reserve/commit/release lifecycle around a generation.

Two rules shape everything here.

**A balance never changes without a ledger row.** `_apply` is the only writer,
and it records before/after for both balances. A disputed count is answerable.

**Reserving debits; failing refunds.** The literal reading of the spec — check
at the start, debit at the end — lets two concurrent requests both pass the
check and spend the same try twice. So the debit happens inside the reserving
transaction as a conditional UPDATE, and a failed or expired generation is
refunded. What the customer observes is identical (nothing is paid for a failed
render) and the race is gone.
"""

import json
import time

from app.config import get_settings
from app.db import connect

FREE = "free"
BONUS = "bonus"
NONE = "none"

# Ledger operation types.
TX_SPEND = "spend"
TX_REFUND = "refund"
TX_GRANT = "grant"
TX_RESTORE = "restore"


class QuotaExhausted(Exception):
    """No free tries left in the category and no bonus tries either."""


def _now() -> int:
    return int(time.time())


def _allowance(conn, user_id: int, category_id: str) -> dict:
    """Read a category allowance, creating it lazily at the configured default.

    Lazy creation is what makes a new category in catalog.yaml work with no
    migration and no admin action: the first time anyone touches it, it exists
    with a full free limit.
    """
    row = conn.execute(
        "SELECT * FROM user_category_allowances WHERE user_id=? AND category_id=?",
        (user_id, category_id),
    ).fetchone()
    if row:
        return dict(row)

    limit = get_settings().free_tries_per_category
    conn.execute(
        "INSERT INTO user_category_allowances"
        "(user_id, category_id, free_limit, free_remaining, updated_at) "
        "VALUES(?,?,?,?,?)",
        (user_id, category_id, limit, limit, _now()),
    )
    return {
        "user_id": user_id,
        "category_id": category_id,
        "free_limit": limit,
        "free_remaining": limit,
    }


def _bonus(conn, user_id: int) -> int:
    row = conn.execute(
        "SELECT bonus_remaining FROM user_balances WHERE user_id=?", (user_id,)
    ).fetchone()
    if row:
        return row["bonus_remaining"]
    conn.execute(
        "INSERT INTO user_balances(user_id, bonus_remaining, updated_at) VALUES(?,0,?)",
        (user_id, _now()),
    )
    return 0


def _apply(
    conn,
    *,
    user_id: int,
    category_id: str | None,
    balance_type: str,
    amount: int,
    transaction_type: str,
    source: str,
    job_id: str | None = None,
    idempotency_key: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Move a balance and write the ledger row. The only writer of balances.

    `amount` is negative for a spend and positive for a grant or refund.
    """
    free_before = free_after = bonus_before = bonus_after = None

    if balance_type == FREE:
        allowance = _allowance(conn, user_id, category_id)
        free_before = allowance["free_remaining"]
        free_after = free_before + amount
        conn.execute(
            "UPDATE user_category_allowances SET free_remaining=?, updated_at=? "
            "WHERE user_id=? AND category_id=?",
            (free_after, _now(), user_id, category_id),
        )
    else:
        bonus_before = _bonus(conn, user_id)
        bonus_after = bonus_before + amount
        conn.execute(
            "UPDATE user_balances SET bonus_remaining=?, updated_at=? WHERE user_id=?",
            (bonus_after, _now(), user_id),
        )

    conn.execute(
        "INSERT INTO generation_transactions"
        "(user_id, category_id, job_id, transaction_type, balance_type, amount,"
        " free_before, free_after, bonus_before, bonus_after, source,"
        " idempotency_key, status, metadata, created_at)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'done',?,?)",
        (
            user_id, category_id, job_id, transaction_type, balance_type, amount,
            free_before, free_after, bonus_before, bonus_after, source,
            idempotency_key, json.dumps(metadata, ensure_ascii=False) if metadata else None,
            _now(),
        ),
    )


# ── reading ───────────────────────────────────────────────────


def snapshot(user_id: int, category_id: str | None = None) -> dict:
    """Everything the UI needs: per-category remainders, bonus, next charge."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT category_id, free_limit, free_remaining "
            "FROM user_category_allowances WHERE user_id=?",
            (user_id,),
        ).fetchall()
        bonus = _bonus(conn, user_id)

    limit = get_settings().free_tries_per_category
    categories = {
        r["category_id"]: {"free_limit": r["free_limit"], "free_remaining": r["free_remaining"]}
        for r in rows
    }

    current = None
    if category_id:
        # A category never touched before still has its full free limit — it is
        # only written to the database when it is first used.
        current = categories.get(
            category_id, {"free_limit": limit, "free_remaining": limit}
        )

    next_charge = NONE
    if current:
        if current["free_remaining"] > 0:
            next_charge = FREE
        elif bonus > 0:
            next_charge = BONUS

    return {
        "categories": categories,
        "bonus_remaining": bonus,
        "category_id": category_id,
        "current": current,
        "next_charge": next_charge,
        "metered": True,
    }


def unmetered_snapshot(category_id: str | None = None) -> dict:
    """What a browser visitor sees: no quota, nothing to display."""
    return {
        "categories": {},
        "bonus_remaining": 0,
        "category_id": category_id,
        "current": None,
        "next_charge": FREE,
        "metered": False,
    }


def history(user_id: int, limit: int = 20) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT transaction_type, balance_type, amount, category_id, source,"
            " created_at FROM generation_transactions WHERE user_id=?"
            " ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ── the reservation lifecycle ─────────────────────────────────


def reserve(user_id: int, category_id: str, idempotency_key: str) -> dict:
    """Take one try, free first then bonus. Raises QuotaExhausted if neither.

    Repeating the call with the same key returns the existing reservation
    without charging again — this is what survives a double tap, a page reload
    and a retry over a slow connection.
    """
    with connect(immediate=True) as conn:
        existing = conn.execute(
            "SELECT * FROM generation_reservations WHERE idempotency_key=?",
            (idempotency_key,),
        ).fetchone()
        if existing:
            return dict(existing)

        allowance = _allowance(conn, user_id, category_id)
        if allowance["free_remaining"] > 0:
            balance_type = FREE
        elif _bonus(conn, user_id) > 0:
            balance_type = BONUS
        else:
            raise QuotaExhausted(category_id)

        _apply(
            conn,
            user_id=user_id,
            category_id=category_id,
            balance_type=balance_type,
            amount=-1,
            transaction_type=TX_SPEND,
            source="generation",
            idempotency_key=idempotency_key,
        )

        expires = _now() + get_settings().reservation_ttl_minutes * 60
        cur = conn.execute(
            "INSERT INTO generation_reservations"
            "(user_id, category_id, balance_type, status, idempotency_key,"
            " expires_at, created_at) VALUES(?,?,?,'open',?,?,?)",
            (user_id, category_id, balance_type, idempotency_key, expires, _now()),
        )
        return dict(
            conn.execute(
                "SELECT * FROM generation_reservations WHERE id=?",
                (cur.lastrowid,),
            ).fetchone()
        )


def attach_job(reservation_id: int, job_id: str) -> None:
    """Link the reservation to the job that will consume it."""
    with connect(immediate=True) as conn:
        conn.execute(
            "UPDATE generation_reservations SET job_id=? WHERE id=? AND status='open'",
            (job_id, reservation_id),
        )


def reservation_for(job_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM generation_reservations WHERE job_id=?", (job_id,)
        ).fetchone()
        return dict(row) if row else None


def commit(job_id: str) -> bool:
    """Confirm a delivered result. The debit already happened at reserve time."""
    with connect(immediate=True) as conn:
        cur = conn.execute(
            "UPDATE generation_reservations SET status='committed' "
            "WHERE job_id=? AND status='open'",
            (job_id,),
        )
        return cur.rowcount > 0


def release(job_id: str, reason: str = "generation_failed") -> bool:
    """Give the try back. Safe to call twice: only an open reservation refunds."""
    with connect(immediate=True) as conn:
        row = conn.execute(
            "SELECT * FROM generation_reservations WHERE job_id=? AND status='open'",
            (job_id,),
        ).fetchone()
        if row is None:
            return False
        _refund(conn, row, reason)
        return True


def release_by_id(reservation_id: int, reason: str) -> bool:
    """Refund a reservation that never got as far as having a job attached."""
    with connect(immediate=True) as conn:
        row = conn.execute(
            "SELECT * FROM generation_reservations WHERE id=? AND status='open'",
            (reservation_id,),
        ).fetchone()
        if row is None:
            return False
        _refund(conn, row, reason)
        return True


def _refund(conn, reservation, reason: str) -> None:
    _apply(
        conn,
        user_id=reservation["user_id"],
        category_id=reservation["category_id"],
        balance_type=reservation["balance_type"],
        amount=+1,
        transaction_type=TX_REFUND,
        source=reason,
        job_id=reservation["job_id"],
        metadata={"reservation_id": reservation["id"]},
    )
    conn.execute(
        "UPDATE generation_reservations SET status='released' WHERE id=?",
        (reservation["id"],),
    )


def expire_stale() -> int:
    """Refund reservations nobody ever finished.

    Without this a crash between reserving and generating would swallow a try
    permanently.
    """
    with connect(immediate=True) as conn:
        rows = conn.execute(
            "SELECT * FROM generation_reservations WHERE status='open' AND expires_at<?",
            (_now(),),
        ).fetchall()
        for row in rows:
            _refund(conn, row, "reservation_expired")
        return len(rows)


def grant(user_id: int, amount: int, source: str, idempotency_key: str | None = None) -> None:
    """Add bonus tries. Every caller goes through here so the ledger stays whole."""
    with connect(immediate=True) as conn:
        _apply(
            conn,
            user_id=user_id,
            category_id=None,
            balance_type=BONUS,
            amount=amount,
            transaction_type=TX_GRANT,
            source=source,
            idempotency_key=idempotency_key,
        )


def restore_free(user_id: int, source: str, conn=None) -> int:
    """Top every category back up to its free limit. Returns tries restored.

    Tops up, never adds: a category already at 3 of 3 stays at 3 of 3 rather
    than becoming 6. Bonuses are granted separately and stay separate — that is
    the whole reason free and bonus are different columns.

    Categories the user has never touched are left alone: they are already at
    full by definition, and writing rows for them would only invent history.
    """
    def _run(conn) -> int:
        rows = conn.execute(
            "SELECT category_id, free_limit, free_remaining"
            " FROM user_category_allowances WHERE user_id=? AND free_remaining < free_limit",
            (user_id,),
        ).fetchall()
        restored = 0
        for row in rows:
            missing = row["free_limit"] - row["free_remaining"]
            _apply(
                conn,
                user_id=user_id,
                category_id=row["category_id"],
                balance_type=FREE,
                amount=missing,
                transaction_type=TX_RESTORE,
                source=source,
            )
            restored += missing
        return restored

    if conn is not None:
        return _run(conn)
    with connect(immediate=True) as conn:
        return _run(conn)
