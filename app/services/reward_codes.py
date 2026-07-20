"""One-time codes: a visit, a purchase, or a manual make-good.

Activation is the one place a customer can add to their own balance, so it is
the one place that has to be airtight. Two guarantees, both from the database
rather than from the order of checks above them:

  * `reward_code_activations.idempotency_key` is UNIQUE per (code, user) — a
    double tap on "Активировать" cannot grant twice;
  * the activation count is incremented conditionally inside the same
    transaction, so two simultaneous requests cannot both take the last slot.
"""

import secrets
import sqlite3
import time

from app.config import get_settings
from app.db import connect
from app.services import quota

# Unambiguous alphabet: these get read off a receipt and typed by hand.
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

VISIT = "visit"
PURCHASE = "purchase"
MANUAL = "manual"

ACTIVE = "active"
USED = "used"
EXPIRED = "expired"
CANCELLED = "cancelled"


class CodeError(Exception):
    """Activation refused. The message is shown to the customer verbatim."""


NOT_FOUND = "Код не найден"
ALREADY_USED = "Код уже использован"
IS_EXPIRED = "Срок действия кода истёк"
WRONG_USER = "Этот код предназначен для другого пользователя"
GENERIC = "Не удалось активировать код. Попробуйте позже"


def _now() -> int:
    return int(time.time())


def _new_code(conn, length: int = 8) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(_ALPHABET) for _ in range(length))
        if not conn.execute(
            "SELECT 1 FROM reward_codes WHERE code=?", (code,)
        ).fetchone():
            return code
    raise RuntimeError("Could not allocate a unique code")


def create(
    reward_type: str,
    *,
    bonus_amount: int | None = None,
    restores_free: bool | None = None,
    max_activations: int = 1,
    valid_days: int | None = None,
    assigned_user_id: int | None = None,
    related_order_id: str | None = None,
    note: str = "",
    created_by: str = "admin",
) -> dict:
    """Mint a code. Defaults come from configuration, not from the caller."""
    settings = get_settings()
    if bonus_amount is None:
        bonus_amount = (
            settings.purchase_bonus if reward_type == PURCHASE else settings.visit_bonus
        )
    if restores_free is None:
        restores_free = reward_type == PURCHASE
    days = valid_days if valid_days is not None else settings.reward_code_valid_days

    with connect(immediate=True) as conn:
        code = _new_code(conn)
        cur = conn.execute(
            "INSERT INTO reward_codes(code, reward_type, bonus_amount, restores_free,"
            " expires_at, max_activations, assigned_user_id, related_order_id,"
            " status, note, created_by, created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                code, reward_type, bonus_amount, int(bool(restores_free)),
                _now() + days * 86400 if days else None,
                max_activations, assigned_user_id, related_order_id,
                ACTIVE, note or None, created_by, _now(),
            ),
        )
        return dict(
            conn.execute(
                "SELECT * FROM reward_codes WHERE id=?", (cur.lastrowid,)
            ).fetchone()
        )


def activate(user_id: int, raw_code: str) -> dict:
    """Redeem a code for this user. Raises CodeError with a customer-facing text."""
    code = (raw_code or "").strip().upper()
    if not code:
        raise CodeError(NOT_FOUND)

    with connect(immediate=True) as conn:
        row = conn.execute("SELECT * FROM reward_codes WHERE code=?", (code,)).fetchone()
        if row is None:
            raise CodeError(NOT_FOUND)
        if row["status"] == CANCELLED:
            raise CodeError(NOT_FOUND)
        if row["expires_at"] and row["expires_at"] < _now():
            conn.execute(
                "UPDATE reward_codes SET status=? WHERE id=?", (EXPIRED, row["id"])
            )
            raise CodeError(IS_EXPIRED)
        if row["assigned_user_id"] and row["assigned_user_id"] != user_id:
            raise CodeError(WRONG_USER)
        if row["activation_count"] >= row["max_activations"]:
            raise CodeError(ALREADY_USED)

        key = f"code:{row['id']}:{user_id}"
        try:
            conn.execute(
                "INSERT INTO reward_code_activations(code_id, user_id, activated_at,"
                " idempotency_key) VALUES(?,?,?,?)",
                (row["id"], user_id, _now(), key),
            )
        except sqlite3.IntegrityError as exc:
            # This user already redeemed this code. Not an error worth alarming
            # them about, but definitely not a second payout.
            raise CodeError(ALREADY_USED) from exc

        conn.execute(
            "UPDATE reward_codes SET activation_count=activation_count+1,"
            " status=CASE WHEN activation_count+1>=max_activations THEN ? ELSE status END"
            " WHERE id=?",
            (USED, row["id"]),
        )

        restored = 0
        if row["restores_free"]:
            restored = quota.restore_free(
                user_id, f"code_{row['reward_type']}", conn=conn
            )
        if row["bonus_amount"]:
            quota._apply(
                conn,
                user_id=user_id,
                category_id=None,
                balance_type=quota.BONUS,
                amount=row["bonus_amount"],
                transaction_type=quota.TX_GRANT,
                source=f"code_{row['reward_type']}",
                idempotency_key=key,
            )

    referred_client = None
    if row["reward_type"] == PURCHASE:
        referred_client = _reward_the_inviter(user_id)

    return {
        "reward_type": row["reward_type"],
        "bonus_amount": row["bonus_amount"],
        "restored_free": restored,
        "referred_client": referred_client,
    }


def _reward_the_inviter(buyer_user_id: int) -> dict | None:
    """A purchase by someone who arrived through a referral pays their inviter.

    Separate from, and on top of, the single bonus already paid for that
    person's first try-on: this one is for a completed purchase, which is the
    outcome the shop actually cares about. Once per invited person, guaranteed
    by the ledger's unique key rather than by this check.
    """
    settings = get_settings()
    if not settings.referrals_enabled or not settings.referred_client_bonus:
        return None

    with connect() as conn:
        referral = conn.execute(
            "SELECT inviter_user_id FROM referrals"
            " WHERE invited_user_id=? AND reward_issued_at IS NOT NULL",
            (buyer_user_id,),
        ).fetchone()
    if referral is None:
        return None

    try:
        quota.grant(
            referral["inviter_user_id"],
            settings.referred_client_bonus,
            "referred_client",
            idempotency_key=f"referred_client:{buyer_user_id}",
        )
    except sqlite3.IntegrityError:
        # Already paid for this buyer — a second purchase is not a second bonus.
        return None
    return {
        "inviter_id": referral["inviter_user_id"],
        "amount": settings.referred_client_bonus,
    }


def cancel(code_id: int, by: str = "admin") -> bool:
    with connect(immediate=True) as conn:
        cur = conn.execute(
            "UPDATE reward_codes SET status=? WHERE id=? AND status=?",
            (CANCELLED, code_id, ACTIVE),
        )
        return cur.rowcount > 0


def recent(limit: int = 20) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM reward_codes ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
