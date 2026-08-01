"""Golden pricing cases. These lock the money boundary."""

import pytest

from app.models.pricing import Selection
from app.money import fmt
from app.services.pricing_service import PricingError, quote


def sel(**kwargs) -> list[Selection]:
    return [Selection(group_id=k, choice_id=v) for k, v in kwargs.items()]


def test_ready_made_wheel_is_just_its_base_price():
    # Wheels are ready-made products the shop does not rework, so they carry no
    # options — a wheel quote is exactly its base price, one line, no deltas.
    q = quote("amg", [])
    assert q.total == 6_200_000
    assert q.total_formatted == "6 200 000"
    assert len(q.lines) == 1


def test_a_wheel_rejects_any_option():
    # Nothing to configure — a stray option group is an error, not ignored.
    with pytest.raises(PricingError):
        quote("amg", sel(insert="leather"))


def test_addons_priced_individually():
    # A category that still configures (front camera): each delta lands on top.
    q = quote("cf1", sel(q="fhd", night="on", lines="on"))
    assert q.total == 600_000 + 300_000 + 200_000 + 250_000


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
        quote("cf1", sel(q="titanium"))  # cf1 has a `q` group, but no such choice


@pytest.mark.parametrize(
    "amount,expected",
    [(0, "0"), (750_000, "750 000"), (6_800_000, "6 800 000"), (1_000, "1 000")],
)
def test_sum_formatting(amount, expected):
    assert fmt(amount) == expected
