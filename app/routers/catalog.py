from fastapi import APIRouter, Header, HTTPException

from app.i18n import lang_of
from app.services import services_repo
from app.services.catalog_service import get_catalog, localized_catalog

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("")
def read_catalog(x_lang: str | None = Header(default=None)):
    """Full bootstrap payload — the SPA fetches this once at boot, localized to
    the caller's language (X-Lang), Russian by default."""
    return localized_catalog(lang_of(x_lang))


@router.get("/{category_id}/services")
def read_services(category_id: str, x_lang: str | None = Header(default=None)):
    """Active paid services for a category — what the configurator offers.

    Only public fields: id, name, price and whether it is pre-selected. active
    and bookkeeping columns stay server-side.
    """
    if get_catalog().category(category_id) is None:
        raise HTTPException(status_code=404, detail="Раздел не найден")
    lang = lang_of(x_lang)
    out = []
    for s in services_repo.list_for_category(category_id, active_only=True):
        name = s["name_uz"] if (lang == "uz" and s.get("name_uz")) else s["name"]
        out.append(
            {"id": s["id"], "name": name, "price": s["price"],
             "default_on": bool(s["default_on"])}
        )
    return out
