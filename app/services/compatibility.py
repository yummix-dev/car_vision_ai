"""Vehicle -> compatible categories.

Deliberately separate from recognition so it stays independently mockable. This is
a data lookup, not a model call — the real version consults a fitment table rather
than asking an LLM.
"""

from app.models.catalog import Catalog
from app.services.catalog_service import get_catalog


def compatible_categories(
    make: str, model: str, year: int, catalog: Catalog | None = None
) -> list[str]:
    catalog = catalog or get_catalog()
    # v1: the shop stocks universal-fit parts for every supported car, so all
    # categories are compatible. Replace with a real fitment lookup when the shop
    # supplies per-model data.
    return [c.id for c in catalog.categories]


def car_label(make: str, model: str, year: int) -> str:
    return f"{make} {model} {year}"


def car_label_short(make: str, model: str) -> str:
    return f"{make} {model}"
