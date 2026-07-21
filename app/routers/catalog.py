from fastapi import APIRouter, HTTPException

from app.models.catalog import Catalog
from app.services import services_repo
from app.services.catalog_service import get_catalog

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("")
def read_catalog() -> Catalog:
    """Full bootstrap payload — the SPA fetches this once at boot."""
    return get_catalog()


@router.get("/{category_id}")
def read_category(category_id: str):
    category = get_catalog().category(category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Раздел не найден")
    return category


@router.get("/{category_id}/services")
def read_services(category_id: str):
    """Active paid services for a category — what the configurator offers.

    Only public fields: id, name, price and whether it is pre-selected. active
    and bookkeeping columns stay server-side.
    """
    if get_catalog().category(category_id) is None:
        raise HTTPException(status_code=404, detail="Раздел не найден")
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "price": s["price"],
            "default_on": bool(s["default_on"]),
        }
        for s in services_repo.list_for_category(category_id, active_only=True)
    ]
