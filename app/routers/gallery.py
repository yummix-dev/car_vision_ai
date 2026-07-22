"""A user's saved AI renders — "Мои примерки".

Read-only listing plus a delete. Saving is not an endpoint: a render is recorded
server-side when its job completes (app/services/generation_service.py), where
the success is certain, rather than trusted from a client that may have navigated
away.
"""

from fastapi import APIRouter, Depends, Header, HTTPException

from app.i18n import lang_of, t
from app.routers.deps import current_user
from app.services import gallery, photos
from app.services.catalog_service import localized_catalog

router = APIRouter(prefix="/api/gallery", tags=["gallery"])


def _catalog_labels(lang: str) -> dict[str, tuple[str, str]]:
    """product_id -> (product_name, category_label) in the caller's language.

    Product names are brands and stay as-is; category labels are localized.
    """
    out: dict[str, tuple[str, str]] = {}
    for cat in localized_catalog(lang)["categories"]:
        for product in cat["products"]:
            out[product["id"]] = (product["name"], cat["label"])
    return out


def _to_public(row: dict, labels: dict[str, tuple[str, str]]) -> dict | None:
    """Shape a saved row for the client, or None if its images are gone.

    A render whose files the sweep already reclaimed (it should not — they are
    protected — but a manual deletion is possible) is dropped rather than shown
    as a broken image.
    """
    try:
        before_url = photos.url_for(row["before_photo_id"])
        after_url = photos.url_for(row["after_photo_id"])
    except photos.PhotoError:
        return None
    name, category_label = labels.get(row["product_id"], (row["product_id"], ""))
    return {
        "id": row["id"],
        "product_id": row["product_id"],
        "product_name": name,
        "category_label": category_label,
        "car_label": row["car_label"] or "",
        "before_url": before_url,
        "after_url": after_url,
        "created_at": row["created_at"],
    }


@router.get("")
def read_gallery(
    user: dict | None = Depends(current_user),
    x_lang: str | None = Header(default=None),
) -> list[dict]:
    """The caller's saved renders, newest first. Empty for a browser visitor —
    who has no durable identity and so no gallery."""
    if user is None:
        return []
    labels = _catalog_labels(lang_of(x_lang))
    items = [_to_public(row, labels) for row in gallery.list_for_user(user["id"])]
    return [i for i in items if i is not None]


@router.delete("/{gallery_id}")
def delete_item(
    gallery_id: int,
    user: dict | None = Depends(current_user),
    x_lang: str | None = Header(default=None),
) -> dict:
    if user is None:
        raise HTTPException(status_code=401, detail=t("err.no_telegram", lang_of(x_lang)))
    if not gallery.delete(user["id"], gallery_id):
        raise HTTPException(status_code=404, detail=t("err.result_not_found", lang_of(x_lang)))
    return {"status": "deleted"}
