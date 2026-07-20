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


def load_catalog(path: Path = CATALOG_PATH) -> Catalog:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    catalog = Catalog.model_validate(raw)
    _validate_references(catalog)
    return catalog


@lru_cache
def get_catalog() -> Catalog:
    return load_catalog()
