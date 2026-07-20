"""Single source of truth for сум formatting.

Prices are whole сум held as ``int`` — never floats.
"""

# Written as an escape so the separator can't be silently swapped for U+00A0.
SEP = " "


def fmt(amount: int) -> str:
    """6800000 -> '6 800 000' (space thousands separator, as in the prototype)."""
    return f"{amount:,}".replace(",", SEP)


def fmt_sum(amount: int) -> str:
    """6800000 -> '6 800 000 сум'"""
    return f"{fmt(amount)}{SEP}сум"
