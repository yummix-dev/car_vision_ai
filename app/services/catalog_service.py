"""Loads and validates the catalog once at startup.

The catalog is small, static and shop-owned, so it lives in a version-controlled
YAML file rather than a database. Validation happens on load, so a mistyped price
or a dangling option-id reference fails at startup instead of at checkout.
"""

from functools import lru_cache
from pathlib import Path

import yaml

from app.models.catalog import Catalog

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.yaml"


class CatalogError(RuntimeError):
    pass


def _validate_references(catalog: Catalog) -> None:
    """Every product's default_config must name real groups and choices."""
    for cat in catalog.categories:
        group_ids = {g.id for g in cat.option_groups}
        for group in cat.option_groups:
            choice_ids = {c.id for c in group.choices}
            if group.type == "toggle":
                if group.default not in ("on", "off"):
                    raise CatalogError(
                        f"{cat.id}.{group.id}: toggle default must be 'on' or 'off', "
                        f"got {group.default!r}"
                    )
                if "on" not in choice_ids:
                    raise CatalogError(
                        f"{cat.id}.{group.id}: toggle needs a choice with id 'on'"
                    )
            elif group.default not in choice_ids:
                raise CatalogError(
                    f"{cat.id}.{group.id}: default {group.default!r} is not a choice"
                )

        for product in cat.products:
            if product.category != cat.id:
                raise CatalogError(
                    f"product {product.id} declares category {product.category!r} "
                    f"but sits under {cat.id!r}"
                )
            for gid, cid in product.default_config.items():
                if gid not in group_ids:
                    raise CatalogError(
                        f"product {product.id}: unknown option group {gid!r}"
                    )
                group = cat.group(gid)
                assert group is not None
                valid = {c.id for c in group.choices} | (
                    {"off"} if group.type == "toggle" else set()
                )
                if cid not in valid:
                    raise CatalogError(
                        f"product {product.id}: {gid}={cid!r} is not a valid choice"
                    )


WEB_IMG_DIR = Path(__file__).resolve().parent.parent.parent / "web" / "img"
PRODUCT_IMAGE_DIR = WEB_IMG_DIR / "products"
CATEGORY_IMAGE_DIR = WEB_IMG_DIR / "categories"


def product_photo_path(product) -> Path | None:
    """Where a product's reference photo lives, or None if it has none."""
    if not product.photo:
        return None
    return PRODUCT_IMAGE_DIR / product.photo


def category_photo_path(category) -> Path | None:
    if not category.photo:
        return None
    return CATEGORY_IMAGE_DIR / category.photo


def _validate_photos(catalog: Catalog) -> None:
    """A named photo that is not on disk fails at startup.

    The alternative is a silent fallback, which would mean the shop believes
    customers are seeing a real part while the model quietly invents one.
    """
    for cat in catalog.categories:
        path = category_photo_path(cat)
        if path is not None and not path.is_file():
            raise CatalogError(
                f"category {cat.id}: photo {cat.photo!r} not found at {path}"
            )
        for product in cat.products:
            path = product_photo_path(product)
            if path is not None and not path.is_file():
                raise CatalogError(
                    f"product {product.id}: photo {product.photo!r} not found at {path}"
                )


def load_catalog(path: Path = CATALOG_PATH) -> Catalog:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    catalog = Catalog.model_validate(raw)
    _validate_references(catalog)
    _validate_photos(catalog)
    return catalog


@lru_cache
def get_catalog() -> Catalog:
    return load_catalog()


# Tags are short marketing words shared across products; translating them via a
# small map keeps the YAML free of per-product tag translations. Unmapped tags
# (LED, brand words) pass through unchanged.
TAG_UZ = {
    "Карбон": "Karbon",
    "LED": "LED",
    "Лепестки": "Kurakchalar",
    "Спорт": "Sport",
    "Комфорт": "Komfort",
    "Классика": "Klassika",
    "Android": "Android",
    "CarPlay": "CarPlay",
    "Широкий": "Keng",
    "Диффузор": "Diffuzor",
    "Ночь": "Tungi",
    "Разметка": "Chiziqlar",
    "4 датчика": "4 datchik",
    "Дисплей": "Displey",
}

# Which fields carry a `<field>_uz` sibling to swap in for Uzbek.
_LOCALIZED_FIELDS = (
    "label", "noun_cap", "title", "sub", "shoot_title", "pick_sub",
    "gen_steps", "material", "time",
)


def _localize_node(node: dict, lang: str) -> dict:
    """Recursively replace `field` with `field_uz` (when present) and drop the
    `_uz` keys, so the client keeps reading plain `.label` etc."""
    out = {}
    for key, value in node.items():
        if key.endswith("_uz"):
            continue
        if isinstance(value, dict):
            out[key] = _localize_node(value, lang)
        elif isinstance(value, list):
            out[key] = [
                _localize_node(v, lang) if isinstance(v, dict) else v for v in value
            ]
        else:
            out[key] = value
        if lang == "uz" and key in _LOCALIZED_FIELDS:
            alt = node.get(f"{key}_uz")
            if alt:
                out[key] = alt
    if lang == "uz" and "tags" in out:
        out["tags"] = [TAG_UZ.get(tag, tag) for tag in out["tags"]]
    return out


def localized_catalog(lang: str) -> dict:
    """The catalog as a plain dict with fields resolved to `lang` (ru fallback)."""
    return _localize_node(get_catalog().model_dump(), lang)
