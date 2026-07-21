"""Per-category paid services, editable in /admin.

Prices here feed the same `pricing_service.quote()` that computes every total —
a service is charged exactly like an option delta, and the server is the only
thing that knows a service's price. A client sends service ids, never amounts.
"""

import time

from app.db import connect
from app.services.catalog_service import get_catalog


class ServiceError(ValueError):
    pass


def _now() -> int:
    return int(time.time())


def seed_installation() -> None:
    """Give every catalog category a default 'Установка' service.

    Installation used to be a free bundled line; it is now an ordinary service.
    Seeding it at price 0 keeps today's behaviour (nothing extra charged) until
    the shop sets a price in the admin — a category never silently gains a fee.
    """
    catalog = get_catalog()
    now = _now()
    with connect(immediate=True) as conn:
        for cat in catalog.categories:
            exists = conn.execute(
                "SELECT 1 FROM services WHERE category_id=? AND name=?",
                (cat.id, "Установка"),
            ).fetchone()
            if exists:
                continue
            conn.execute(
                "INSERT INTO services(category_id, name, price, default_on, active,"
                " sort, created_at, updated_at) VALUES(?,?,0,1,1,0,?,?)",
                (cat.id, "Установка", now, now),
            )


def list_for_category(category_id: str, *, active_only: bool = True) -> list[dict]:
    sql = "SELECT * FROM services WHERE category_id=?"
    params: list = [category_id]
    if active_only:
        sql += " AND active=1"
    sql += " ORDER BY sort, id"
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def all_grouped() -> dict[str, list[dict]]:
    """Every service, active or not, grouped by category — for the admin page."""
    with connect() as conn:
        rows = conn.execute("SELECT * FROM services ORDER BY category_id, sort, id").fetchall()
    grouped: dict[str, list[dict]] = {}
    for r in rows:
        grouped.setdefault(r["category_id"], []).append(dict(r))
    return grouped


def resolve(category_id: str, service_ids: list[int]) -> list[dict]:
    """Validated, active services for these ids, in display order.

    An id that is unknown, inactive, or belongs to another category is rejected
    rather than skipped — the same rigor as an unknown option choice, so a
    client cannot smuggle a service onto a category it does not belong to.
    """
    if not service_ids:
        return []
    available = {s["id"]: s for s in list_for_category(category_id, active_only=True)}
    resolved: list[dict] = []
    seen: set[int] = set()
    for sid in service_ids:
        if sid in seen:
            continue  # a repeated id must not double-charge
        service = available.get(sid)
        if service is None:
            raise ServiceError(f"Unknown or inactive service {sid} for {category_id}")
        seen.add(sid)
        resolved.append(service)
    return resolved


# ── admin mutations ───────────────────────────────────────────


def create(category_id: str, name: str, price: int, default_on: bool = False) -> dict:
    name = (name or "").strip()
    if not name:
        raise ServiceError("Название услуги обязательно")
    if price < 0:
        raise ServiceError("Цена не может быть отрицательной")
    if get_catalog().category(category_id) is None:
        raise ServiceError(f"Unknown category {category_id}")

    now = _now()
    with connect(immediate=True) as conn:
        nxt = conn.execute(
            "SELECT COALESCE(MAX(sort),0)+1 FROM services WHERE category_id=?",
            (category_id,),
        ).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO services(category_id, name, price, default_on, active,"
            " sort, created_at, updated_at) VALUES(?,?,?,?,1,?,?,?)",
            (category_id, name, price, int(bool(default_on)), nxt, now, now),
        )
        return dict(conn.execute("SELECT * FROM services WHERE id=?", (cur.lastrowid,)).fetchone())


def update(service_id: int, *, name: str, price: int, default_on: bool, active: bool) -> None:
    name = (name or "").strip()
    if not name:
        raise ServiceError("Название услуги обязательно")
    if price < 0:
        raise ServiceError("Цена не может быть отрицательной")
    with connect(immediate=True) as conn:
        conn.execute(
            "UPDATE services SET name=?, price=?, default_on=?, active=?, updated_at=?"
            " WHERE id=?",
            (name, price, int(bool(default_on)), int(bool(active)), _now(), service_id),
        )


def deactivate(service_id: int) -> None:
    with connect(immediate=True) as conn:
        conn.execute(
            "UPDATE services SET active=0, updated_at=? WHERE id=?", (_now(), service_id)
        )
