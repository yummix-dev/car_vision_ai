"""Public feed of the shop's real installs — "Реальные сборки".

Read-only. Builds are curated in /admin; here they are served to the client with
image URLs resolved and the category label localized to the caller's language.
The client filters by car model locally (the feed is small).
"""

from fastapi import APIRouter, Header

from app.i18n import lang_of
from app.services import photos, showcase
from app.services.catalog_service import localized_catalog

router = APIRouter(prefix="/api/showcase", tags=["showcase"])


def _category_labels(lang: str) -> dict[str, str]:
    return {c["id"]: c["label"] for c in localized_catalog(lang)["categories"]}


def _to_public(row: dict, labels: dict[str, str]) -> dict | None:
    try:
        before_url = photos.url_for(row["before_photo_id"])
        after_url = photos.url_for(row["after_photo_id"])
    except photos.PhotoError:
        return None
    car_label = " ".join(
        str(p) for p in (row["car_brand"], row["car_model"], row["car_year"]) if p
    )
    return {
        "id": row["id"],
        "car_model": row["car_model"],
        "car_label": car_label,
        "category_id": row["category_id"] or "",
        "category_label": labels.get(row["category_id"], "") if row["category_id"] else "",
        "title": row["title"],
        "before_url": before_url,
        "after_url": after_url,
    }


@router.get("")
def read_showcase(x_lang: str | None = Header(default=None)) -> list[dict]:
    """Active builds, newest first, with resolved image URLs and a localized
    category label. Never empty-errors — an empty shop simply has no builds yet."""
    labels = _category_labels(lang_of(x_lang))
    items = [_to_public(row, labels) for row in showcase.list_public()]
    return [i for i in items if i is not None]
