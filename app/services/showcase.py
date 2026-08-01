"""The shop's real installs — "Реальные сборки".

Owner-curated social proof, not user content: the shop adds a finished job
(before/after photos, the car, what was done) in /admin, and the client shows a
public feed filterable by car model. A customer who sees their exact car already
done is the strongest nudge there is.

Photos live in the normal media pipeline (photos.save_upload) and are exempted
from the cleanup sweep while their row exists — see cleanup.protected ids.
"""

import time

from app.db import connect


class ShowcaseError(ValueError):
    pass


def create(
    *,
    car_brand: str,
    car_model: str,
    car_year: int | None,
    category_id: str | None,
    title: str,
    before_photo_id: str,
    after_photo_id: str,
) -> dict:
    car_brand = (car_brand or "").strip()
    car_model = (car_model or "").strip()
    title = (title or "").strip()
    if not (car_brand and car_model and title):
        raise ShowcaseError("Марка, модель и описание обязательны")

    now = int(time.time())
    with connect(immediate=True) as conn:
        nxt = conn.execute(
            "SELECT COALESCE(MAX(sort),0)+1 FROM showcase_builds"
        ).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO showcase_builds(car_brand, car_model, car_year, category_id,"
            " title, before_photo_id, after_photo_id, active, sort, created_at)"
            " VALUES(?,?,?,?,?,?,?,1,?,?)",
            (car_brand, car_model, car_year, category_id or None, title,
             before_photo_id, after_photo_id, nxt, now),
        )
        return dict(conn.execute(
            "SELECT * FROM showcase_builds WHERE id=?", (cur.lastrowid,)
        ).fetchone())


def list_public(limit: int = 60) -> list[dict]:
    """Active builds, newest first — the public feed."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM showcase_builds WHERE active=1 "
            "ORDER BY sort DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def all_admin() -> list[dict]:
    """Every build, active or not — for the admin list."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM showcase_builds ORDER BY sort DESC, id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def deactivate(build_id: int) -> None:
    with connect(immediate=True) as conn:
        conn.execute(
            "UPDATE showcase_builds SET active=0 WHERE id=?", (build_id,)
        )


def delete(build_id: int) -> None:
    """Remove a build. Its media then ages out with the normal sweep."""
    with connect(immediate=True) as conn:
        conn.execute("DELETE FROM showcase_builds WHERE id=?", (build_id,))


def protected_photo_ids() -> set[str]:
    """Before/after photos of every stored build (active or not) — the media
    sweep must not reclaim them while the row exists."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT before_photo_id, after_photo_id FROM showcase_builds"
        ).fetchall()
    ids: set[str] = set()
    for r in rows:
        ids.add(r["before_photo_id"])
        ids.add(r["after_photo_id"])
    return ids
