"""Golden pricing cases. These lock the money boundary."""

import pytest

from app.models.pricing import Selection
from app.money import fmt
from app.services.pricing_service import PricingError, quote


def sel(**kwargs) -> list[Selection]:
    return [Selection(group_id=k, choice_id=v) for k, v in kwargs.items()]


def test_wheel_defaults_apply_product_preset():
    # AMG Carbon LED ships with carbon insert, logo mark, LED and paddles on.
    q = quote("amg", [])
    assert q.total == 6_200_000 + 300_000 + 150_000 + 250_000 + 200_000
    assert q.total == 7_100_000
    assert q.total_formatted == "7 100 000"


def test_wheel_stripped_to_base():
    q = quote("amg", sel(insert="leather", mark="none", led="off", paddles="off"))
    assert q.total == 6_200_000


def test_wheel_addons_priced_individually():
    q = quote("urban", sel(insert="carbon", mark="carbon", led="on", paddles="on"))
    assert q.total == 3_400_000 + 300_000 + 250_000 + 250_000 + 200_000


def test_audio_segment_and_toggle():
    q = quote("au1", sel(size="s13", carplay="on"))
    assert q.total == 3_200_000 + 1_200_000 + 350_000
    assert q.total_formatted == "4 750 000"


def test_parking_sensors():
    q = quote("pk1", sel(sensors="s8", display="on"))
    assert q.total == 750_000 + 800_000 + 300_000


def test_bumper_paint_zero_delta_is_not_a_line():
    q = quote("bf1", sel(paint="primer", pdc="off"))
    assert q.total == 2_000_000
    labels = [line.label for line in q.lines]
    assert not any("Покраска" in label for label in labels)


def test_no_bundled_free_installation_line():
    """Installation is no longer a free bundled line — it is a paid service,
    priced from the DB and only added when selected (see test_services.py)."""
    q = quote("cf1", [])
    assert not any(line.amount_formatted == "включена" for line in q.lines)
    # With no services selected, the breakdown is just base + option deltas.
    assert q.lines[0].label  # base price line
    assert all(line.amount != 0 for line in q.lines[1:])


def test_unknown_product_rejected():
    with pytest.raises(PricingError):
        quote("nope", [])


def test_unknown_group_rejected():
    with pytest.raises(PricingError):
        quote("amg", sel(bogus="x"))


def test_unknown_choice_rejected():
    with pytest.raises(PricingError):
        quote("amg", sel(insert="titanium"))


@pytest.mark.parametrize(
    "amount,expected",
    [(0, "0"), (750_000, "750 000"), (6_800_000, "6 800 000"), (1_000, "1 000")],
)
def test_sum_formatting(amount, expected):
    assert fmt(amount) == expected
