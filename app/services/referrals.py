"""Referrals: attribution, qualification, and the bonus that follows.

The rule that shapes this module: **a bonus is never paid for a click.** It is
paid when an invited person has actually used the product — confirmed a car,
uploaded a photograph of their own, and completed a try-on that produced a real
image. Everything cheaper than that is free to fake, so everything cheaper than
that pays nothing.

Paying at most once per invited person is enforced by the database, twice over:
`referrals.invited_user_id` is UNIQUE, and the grant is written with the ledger's
UNIQUE `idempotency_key`. A duplicate call cannot pay twice even if both checks
above it are somehow passed.
"""

import json
import secrets
import sqlite3
import time

from app.config import get_settings
from app.db import connect
from app.services import notifications, photos, quota

PENDING = "pending"
QUALIFIED = "qualified"
CAPPED = "capped"
FROZEN = "frozen"
REJECTED = "rejected"

SOURCE_LINK = "link"
SOURCE_SHARE = "share"

_CODE_ALPHABET = "abcdefghijkmnpqrstuvwxyz23456789"


class AttributionRefused(Exception):
    """The visit cannot be attributed — self-invite, repeat, or already active."""


def _now() -> int:
    return int(time.time())


def _month_start() -> int:
    t = time.gmtime()
    return int(time.mktime((t.tm_year, t.tm_mon, 1, 0, 0, 0, 0, 0, 0)))


# ── links ─────────────────────────────────────────────────────


def start_param(ref_code: str, share_code: str | None = None) -> str:
    """Telegram's startapp payload. Its charset is limited to A-Za-z0-9_-."""
    return f"ref_{ref_code}" + (f"-s-{share_code}" if share_code else "")


def parse_start_param(raw: str) -> tuple[str | None, str | None]:
    if not raw or not raw.startswith("ref_"):
        return None, None
    body = raw[4:]
    if "-s-" in body:
        code, share = body.split("-s-", 1)
        return code or None, share or None
    return body or None, None


def link_for(ref_code: str, share_code: str | None = None) -> str:
    settings = get_settings()
    bot = settings.telegram_bot_username
    if not bot:
        return ""
    app = settings.telegram_app_name
    path = f"{bot}/{app}" if app else bot
    return f"https://t.me/{path}?startapp={start_param(ref_code, share_code)}"


def _new_code(conn, table: str, column: str, length: int = 8) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))
        if not conn.execute(
            f"SELECT 1 FROM {table} WHERE {column}=?", (code,)  # noqa: S608 - fixed literals
        ).fetchone():
            return code
    raise RuntimeError("Could not allocate a unique code")


def create_share_link(owner_user_id: int, **fields) -> dict:
    with connect(immediate=True) as conn:
        code = _new_code(conn, "share_links", "public_code")
        cur = conn.execute(
            "INSERT INTO share_links(owner_user_id, public_code, job_id,"
            " result_photo_id, product_id, category_id, car_label, channel,"
            " share_type, created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                owner_user_id, code, fields.get("job_id"),
                fields.get("result_photo_id"), fields.get("product_id"),
                fields.get("category_id"), fields.get("car_label"),
                fields.get("channel"), fields.get("share_type", "result"), _now(),
            ),
        )
        return dict(
            conn.execute(
                "SELECT * FROM share_links WHERE id=?", (cur.lastrowid,)
            ).fetchone()
        )


# ── attribution ───────────────────────────────────────────────


def attribute(invited_user: dict, raw_start_param: str, ip: str | None = None) -> dict:
    """Bind an arriving user to whoever invited them. Once, and never again."""
    code, share_code = parse_start_param(raw_start_param)
    if not code:
        raise AttributionRefused("no referral code")

    invited_id = invited_user["id"]

    with connect(immediate=True) as conn:
        if conn.execute(
            "SELECT 1 FROM referrals WHERE invited_user_id=?", (invited_id,)
        ).fetchone():
            # Attribution is permanent. A second link never reassigns credit.
            raise AttributionRefused("already attributed")

        inviter = conn.execute(
            "SELECT * FROM users WHERE ref_code=?", (code,)
        ).fetchone()
        if inviter is None:
            raise AttributionRefused("unknown code")
        if inviter["id"] == invited_id:
            raise AttributionRefused("self-invite")

        # Somebody who has already produced a try-on is not a new user, no
        # matter whose link they open next.
        if invited_user.get("first_generation_at"):
            raise AttributionRefused("not a new user")

        share = None
        if share_code:
            share = conn.execute(
                "SELECT * FROM share_links WHERE public_code=?", (share_code,)
            ).fetchone()
            if share is not None:
                conn.execute(
                    "UPDATE share_links SET opens_count=opens_count+1 WHERE id=?",
                    (share["id"],),
                )

        conn.execute(
            "INSERT INTO referrals(inviter_user_id, invited_user_id, referral_code,"
            " source_type, source_share_id, source_channel, first_opened_at,"
            " status, invited_ip) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                inviter["id"], invited_id, code,
                SOURCE_SHARE if share is not None else SOURCE_LINK,
                share["id"] if share is not None else None,
                share["channel"] if share is not None else None,
                _now(), PENDING, ip,
            ),
        )
        return {"inviter_id": inviter["id"], "source": SOURCE_SHARE if share else SOURCE_LINK}


def pending_for(user_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM referrals WHERE invited_user_id=? AND status=?",
            (user_id, PENDING),
        ).fetchone()
        return dict(row) if row else None


# ── qualification ─────────────────────────────────────────────


def _fraud_signals(conn, referral, invited_user_id: int, source_photo_id: str) -> tuple[int, list]:
    """Weak signals, scored rather than acted on individually.

    Deliberately excludes device fingerprinting: it is invasive, defeated in a
    minute, and adds nothing next to a Telegram id that cannot be forged
    without breaking the initData HMAC.
    """
    score, reasons = 0, []
    settings = get_settings()

    elapsed = _now() - referral["first_opened_at"]
    if elapsed < settings.referral_min_seconds:
        score += 2
        reasons.append(f"qualified in {elapsed}s")

    # Many accounts, one photograph — the actual farming pattern.
    row = conn.execute(
        "SELECT sha256 FROM photo_uploads WHERE photo_id=?", (source_photo_id,)
    ).fetchone()
    if row:
        others = conn.execute(
            "SELECT COUNT(DISTINCT user_id) c FROM photo_uploads "
            "WHERE sha256=? AND user_id IS NOT NULL AND user_id!=?",
            (row["sha256"], invited_user_id),
        ).fetchone()["c"]
        if others:
            score += 3
            reasons.append(f"photo reused by {others} other account(s)")

    if referral["invited_ip"]:
        same_ip = conn.execute(
            "SELECT COUNT(*) c FROM referrals WHERE inviter_user_id=? "
            "AND invited_ip=? AND invited_user_id!=?",
            (referral["inviter_user_id"], referral["invited_ip"], invited_user_id),
        ).fetchone()["c"]
        if same_ip:
            score += 2
            reasons.append(f"{same_ip} other invite(s) from this address")

    return score, reasons


def _rewards_this_month(conn, inviter_id: int) -> int:
    return conn.execute(
        "SELECT COUNT(*) c FROM referrals WHERE inviter_user_id=? "
        "AND reward_issued_at>=?",
        (inviter_id, _month_start()),
    ).fetchone()["c"]


def on_first_generation(user_id: int, source_photo_id: str | None) -> dict | None:
    """Called after a try-on produced a real image. Idempotent.

    Returns the reward description when a bonus was issued, else None.
    """
    settings = get_settings()
    if not settings.referrals_enabled:
        return None

    with connect(immediate=True) as conn:
        user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if user is None:
            return None

        first_time = user["first_generation_at"] is None
        if first_time:
            conn.execute(
                "UPDATE users SET first_generation_at=? WHERE id=?", (_now(), user_id)
            )
        if not first_time:
            # The reward is for the *first* try-on only.
            return None

        referral = conn.execute(
            "SELECT * FROM referrals WHERE invited_user_id=? AND status=?",
            (user_id, PENDING),
        ).fetchone()
        if referral is None:
            return None

        # §8: the invited person must have confirmed a car and used their own
        # photograph. The demo photo is not evidence of anything.
        if not user["car_confirmed_at"]:
            return None
        if not source_photo_id or source_photo_id == photos.DEMO_PHOTO_ID:
            return None

        score, reasons = _fraud_signals(conn, referral, user_id, source_photo_id)
        now = _now()

        if score >= settings.referral_fraud_threshold:
            # Held for review rather than refused: a weak signal is not proof,
            # and a wrongly refused bonus is invisible to everyone.
            conn.execute(
                "UPDATE referrals SET status=?, qualified_at=?, fraud_score=?,"
                " fraud_reasons=? WHERE id=?",
                (FROZEN, now, score, json.dumps(reasons, ensure_ascii=False), referral["id"]),
            )
            frozen_inviter = referral["inviter_user_id"]
        else:
            frozen_inviter = None

        if frozen_inviter is not None:
            # Told, not left guessing: silence about a held bonus reads exactly
            # like a bonus that never existed.
            notifications.referral_frozen(frozen_inviter)
            return None

        if _rewards_this_month(conn, referral["inviter_user_id"]) >= settings.referral_monthly_limit:
            conn.execute(
                "UPDATE referrals SET status=?, qualified_at=?, fraud_score=? WHERE id=?",
                (CAPPED, now, score, referral["id"]),
            )
            return None

        conn.execute(
            "UPDATE referrals SET status=?, qualified_at=?, reward_issued_at=?,"
            " fraud_score=? WHERE id=?",
            (QUALIFIED, now, now, score, referral["id"]),
        )
        if referral["source_share_id"]:
            conn.execute(
                "UPDATE share_links SET qualified_users_count=qualified_users_count+1"
                " WHERE id=?",
                (referral["source_share_id"],),
            )
        inviter_id = referral["inviter_user_id"]

    # Outside the transaction: quota.grant opens its own. The ledger's UNIQUE
    # idempotency key is the final guarantee of one bonus per invited person —
    # a second attempt raises rather than paying again.
    quota.grant(
        inviter_id,
        settings.referral_bonus,
        "referral",
        idempotency_key=f"referral:{user_id}",
    )
    return {"inviter_id": inviter_id, "amount": settings.referral_bonus}


# ── review ────────────────────────────────────────────────────


def list_frozen(limit: int = 50) -> list[dict]:
    """Referrals held for review, with enough context to actually judge them."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT r.*, iu.telegram_id AS inviter_telegram_id,"
            " vu.telegram_id AS invited_telegram_id"
            " FROM referrals r"
            " JOIN users iu ON iu.id = r.inviter_user_id"
            " JOIN users vu ON vu.id = r.invited_user_id"
            " WHERE r.status=? ORDER BY r.id DESC LIMIT ?",
            (FROZEN, limit),
        ).fetchall()

    out = []
    for row in rows:
        entry = dict(row)
        try:
            entry["reasons"] = json.loads(entry["fraud_reasons"] or "[]")
        except json.JSONDecodeError:
            entry["reasons"] = []
        out.append(entry)
    return out


def _settle_review(referral_id: int, status: str, note: str, by: str) -> dict | None:
    """Move a frozen referral to a final state. Returns it, or None if it was
    not frozen — a second click must do nothing rather than something."""
    with connect(immediate=True) as conn:
        row = conn.execute(
            "SELECT * FROM referrals WHERE id=? AND status=?", (referral_id, FROZEN)
        ).fetchone()
        if row is None:
            return None
        now = _now()
        conn.execute(
            "UPDATE referrals SET status=?, reviewed_at=?, review_note=?,"
            " reviewed_by=?, qualified_at=COALESCE(qualified_at,?),"
            " reward_issued_at=CASE WHEN ?=? THEN ? ELSE reward_issued_at END"
            " WHERE id=?",
            (status, now, note or None, by, now, status, QUALIFIED, now, referral_id),
        )
        return dict(row)


def approve(referral_id: int, note: str = "", by: str = "admin") -> bool:
    """Pay a held bonus after a human looked at it.

    Deliberately ignores the monthly cap: the cap guards against farming, and
    somebody has now examined this specific case. The ledger records it as
    `referral_approved` so manual decisions stay distinguishable from automatic
    ones when the numbers are audited later.
    """
    referral = _settle_review(referral_id, QUALIFIED, note, by)
    if referral is None:
        return False

    try:
        quota.grant(
            referral["inviter_user_id"],
            get_settings().referral_bonus,
            "referral_approved",
            idempotency_key=f"referral:{referral['invited_user_id']}",
        )
    except sqlite3.IntegrityError:
        # The unique idempotency key already holds a payment for this invited
        # person. Nothing more is owed; the status change above still stands.
        return True

    notifications.referral_rewarded(
        referral["inviter_user_id"], get_settings().referral_bonus
    )
    return True


def reject(referral_id: int, note: str = "", by: str = "admin") -> bool:
    return _settle_review(referral_id, REJECTED, note, by) is not None


# ── reporting ─────────────────────────────────────────────────


def stats(user: dict) -> dict:
    settings = get_settings()
    with connect() as conn:
        invited = conn.execute(
            "SELECT COUNT(*) c FROM referrals WHERE inviter_user_id=?", (user["id"],)
        ).fetchone()["c"]
        qualified = conn.execute(
            "SELECT COUNT(*) c FROM referrals WHERE inviter_user_id=? AND status=?",
            (user["id"], QUALIFIED),
        ).fetchone()["c"]
        this_month = _rewards_this_month(conn, user["id"])

    return {
        "code": user["ref_code"],
        "link": link_for(user["ref_code"]),
        "invited": invited,
        "qualified": qualified,
        "bonus_earned": qualified * settings.referral_bonus,
        "monthly_limit": settings.referral_monthly_limit,
        "monthly_remaining": max(0, settings.referral_monthly_limit - this_month),
    }
