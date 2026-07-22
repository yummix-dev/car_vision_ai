"""Persistent users, keyed by Telegram id.

The app had no user entity at all before this: identity existed only as a
validated Telegram id inside a single request. Quotas need somebody to belong
to, so this is where that somebody starts existing.

Only Telegram users get a row. A browser visitor has no durable identity and is
not metered — see `app/services/quota.py`.
"""

import secrets
import time

from app.db import connect
from app.models.telegram import TelegramUser

# Unambiguous alphabet: no O/0, I/1 — the code gets read aloud and retyped.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 7


def _new_ref_code(conn) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))
        taken = conn.execute(
            "SELECT 1 FROM users WHERE ref_code=?", (code,)
        ).fetchone()
        if not taken:
            return code
    raise RuntimeError("Could not allocate a unique referral code")


def get_or_create(telegram_user: TelegramUser, lang: str | None = None) -> dict:
    """Resolve the internal user for a validated Telegram identity.

    `lang` (from the X-Lang header) is stored so notifications sent outside a
    request — a friend qualifying, a code activating — reach the user in the
    language they chose.
    """
    with connect(immediate=True) as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE telegram_id=?", (telegram_user.id,)
        ).fetchone()
        if row:
            if lang and lang in ("ru", "uz") and row["lang"] != lang:
                conn.execute(
                    "UPDATE users SET lang=? WHERE id=?", (lang, row["id"])
                )
                return dict(conn.execute(
                    "SELECT * FROM users WHERE id=?", (row["id"],)
                ).fetchone())
            return dict(row)

        now = int(time.time())
        conn.execute(
            "INSERT INTO users(telegram_id, ref_code, lang, created_at) VALUES(?,?,?,?)",
            (telegram_user.id, _new_ref_code(conn), lang if lang in ("ru", "uz") else "ru", now),
        )
        conn.execute(
            "INSERT INTO user_balances(user_id, bonus_remaining, updated_at) "
            "SELECT id, 0, ? FROM users WHERE telegram_id=?",
            (now, telegram_user.id),
        )
        return dict(
            conn.execute(
                "SELECT * FROM users WHERE telegram_id=?", (telegram_user.id,)
            ).fetchone()
        )


def confirm_car(user_id: int, brand: str, model: str, year: int) -> None:
    """Record the confirmed vehicle — the "car project" of the referral rules.

    A separate project entity would carry nothing the car screen does not
    already produce.
    """
    with connect(immediate=True) as conn:
        conn.execute(
            "UPDATE users SET car_brand=?, car_model=?, car_year=?, "
            "car_confirmed_at=? WHERE id=?",
            (brand, model, year, int(time.time()), user_id),
        )
