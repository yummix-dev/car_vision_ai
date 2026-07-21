"""Authoritative pricing. This is the money boundary.

The prototype computed totals client-side where anyone could edit them, and used
two separate code paths (a bespoke one for wheels, a generic one for everything
else). Here there is exactly one path: base price plus the deltas of the selected
option choices. Wheel add-ons are ordinary option groups in catalog.yaml.

Installation is always bundled — that rule lives here, not in client-droppable data.
"""

from app.models.catalog import Catalog, Category, Product
from app.models.pricing import PriceBreakdown, PriceLine, Selection
from app.money import fmt
from app.services import services_repo
from app.services.catalog_service import get_catalog


class PricingError(ValueError):
    pass


def resolve_selections(
    category: Category, product: Product, selections: list[Selection]
) -> dict[str, str]:
    """Merge the caller's selections over the product's defaults.

    Unknown groups or choices are rejected rather than silently ignored — a
    client sending garbage should not quietly get the base price.
    """
    resolved: dict[str, str] = {}
    for group in category.option_groups:
        resolved[group.id] = product.default_config.get(group.id, group.default)

    for sel in selections:
        group = category.group(sel.group_id)
        if group is None:
            raise PricingError(f"Unknown option group: {sel.group_id}")
        valid = {c.id for c in group.choices}
        if group.type == "toggle":
            valid |= {"off"}
        if sel.choice_id not in valid:
            raise PricingError(
                f"Unknown choice {sel.choice_id!r} for group {sel.group_id!r}"
            )
        resolved[group.id] = sel.choice_id

    return resolved


def quote(
    product_id: str,
    selections: list[Selection],
    service_ids: list[int] | None = None,
    catalog: Catalog | None = None,
) -> PriceBreakdown:
    catalog = catalog or get_catalog()
    found = catalog.find_product(product_id)
    if found is None:
        raise PricingError(f"Unknown product: {product_id}")
    category, product = found

    resolved = resolve_selections(category, product, selections)

    lines = [
        PriceLine(
            label=product.name,
            amount=product.base_price,
            amount_formatted=fmt(product.base_price),
        )
    ]
    total = product.base_price

    for group in category.option_groups:
        choice_id = resolved.get(group.id)
        if choice_id in (None, "off"):
            continue
        choice = group.choice(choice_id)
        if choice is None or choice.price_delta == 0:
            continue
        label = (
            choice.label
            if group.type == "toggle"
            else f"{group.label}: {choice.label}"
        )
        lines.append(
            PriceLine(
                label=label,
                amount=choice.price_delta,
                amount_formatted=fmt(choice.price_delta),
            )
        )
        total += choice.price_delta

    # Paid services (installation, rework, ...). Priced from the DB, validated
    # against the product's category — a client cannot attach a service that
    # belongs to another category or an inactive one.
    try:
        services = services_repo.resolve(category.id, service_ids or [])
    except services_repo.ServiceError as exc:
        raise PricingError(str(exc)) from exc
    for service in services:
        lines.append(
            PriceLine(
                label=service["name"],
                amount=service["price"],
                amount_formatted=fmt(service["price"]),
            )
        )
        total += service["price"]

    return PriceBreakdown(
        product_id=product.id,
        product_name=product.name,
        lines=lines,
        total=total,
        total_formatted=fmt(total),
    )
