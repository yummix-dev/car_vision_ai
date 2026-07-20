from fastapi import APIRouter, HTTPException

from app.models.catalog import Catalog
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
