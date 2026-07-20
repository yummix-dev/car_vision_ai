"""The catalog must validate at startup, not fail at checkout."""

from app.services.catalog_service import load_catalog

catalog = load_catalog()


def test_all_seven_categories_present():
    assert [c.id for c in catalog.categories] == [
        "rul", "audio", "bumperF", "bumperR", "camF", "camR", "park",
    ]


def test_product_ids_are_globally_unique():
    ids = [p.id for c in catalog.categories for p in c.products]
    assert len(ids) == len(set(ids))


def test_every_category_has_products_and_five_gen_steps():
    for cat in catalog.categories:
        assert cat.products, f"{cat.id} has no products"
        assert len(cat.gen_steps) == 5, f"{cat.id} needs 5 pipeline steps"


def test_default_config_references_resolve():
    for cat in catalog.categories:
        for product in cat.products:
            for gid, cid in product.default_config.items():
                group = cat.group(gid)
                assert group is not None, f"{product.id}: unknown group {gid}"
                valid = {c.id for c in group.choices}
                if group.type == "toggle":
                    valid |= {"off"}
                assert cid in valid, f"{product.id}: {gid}={cid} invalid"


def test_group_defaults_are_valid_choices():
    for cat in catalog.categories:
        for group in cat.option_groups:
            if group.type == "toggle":
                assert group.default in ("on", "off")
                assert any(c.id == "on" for c in group.choices)
            else:
                assert group.default in {c.id for c in group.choices}


def test_prices_are_non_negative_integers():
    for cat in catalog.categories:
        for product in cat.products:
            assert isinstance(product.base_price, int) and product.base_price > 0
        for group in cat.option_groups:
            for choice in group.choices:
                assert isinstance(choice.price_delta, int)
                assert choice.price_delta >= 0


def test_wheel_category_swatches_carry_hex():
    rul = catalog.category("rul")
    for gid in ("leather", "stitch"):
        group = rul.group(gid)
        assert all(c.hex for c in group.choices), f"{gid} needs hex values"
