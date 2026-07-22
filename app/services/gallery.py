"""A user's saved AI renders — "Мои примерки".

Every successful generation by a Telegram user is recorded here, so the render
survives the media sweep and the user can return to it. A browser visitor has no
durable identity and is not saved (the same line drawn by quotas and referrals).

Nothing here is load-bearing for a render: saving is best-effort at job
completion, and a failure to save must never fail the generation the customer is
watching.
"""

import time

from app.db import connect


def save(
    *,
    user_id: int,
    job_id: str,
    product_id: str,
    category_id: str,
    before_photo_id: str,
    after_photo_id: str,
    car_label: str | None,
) -> None:
    """Record a finished render. Idempotent: a job saved twice (a retried poll,
    a re-run of the completion path) is one row, enforced by UNIQUE(job_id)."""
    with connect(immediate=True) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO saved_generations"
            "(user_id, job_id, product_id, category_id, before_photo_id,"
            " after_photo_id, car_label, created_at) VALUES(?,?,?,?,?,?,?,?)",
            (
                user_id, job_id, product_id, category_id,
                before_photo_id, after_photo_id, car_label, int(time.time()),
            ),
        )


def list_for_user(user_id: int, limit: int = 60) -> list[dict]:
    """A user's saved renders, newest first."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM saved_generations WHERE user_id=? "
            "ORDER BY created_at DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def delete(user_id: int, gallery_id: int) -> bool:
    """Remove one saved render the user owns. The media files are left for the
    sweep to reclaim once nothing protects them — deleting them here would race
    a share still in flight and buys nothing.

    Scoped by user_id: a client cannot delete another person's render by id.
    """
    with connect(immediate=True) as conn:
        cur = conn.execute(
            "DELETE FROM saved_generations WHERE id=? AND user_id=?",
            (gallery_id, user_id),
        )
        return cur.rowcount > 0


def protected_photo_ids() -> set[str]:
    """Photo ids the media sweep must not reclaim — every saved render's before
    and after image. Empty set is fine (nothing saved yet)."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT before_photo_id, after_photo_id FROM saved_generations"
        ).fetchall()
    ids: set[str] = set()
    for r in rows:
        ids.add(r["before_photo_id"])
        ids.add(r["after_photo_id"])
    return ids
