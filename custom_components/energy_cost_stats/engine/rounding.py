"""Output rounding helpers (tasks/006-pricing-and-grouping.md, SPEC §4).

Pure Python, stdlib only (CLAUDE.md principle 4). The engine keeps exact ``Decimal``
values in the ``Report``; only the stage 3 serializer calls these helpers, at output
time. Money gets 2 decimals, kWh 3 and prices 4, all ``ROUND_HALF_UP``. The helpers
take ``Decimal`` only: the serializer maps ``None`` itself.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, localcontext

MONEY_QUANTUM = Decimal("0.01")
KWH_QUANTUM = Decimal("0.001")
PRICE_QUANTUM = Decimal("0.0001")


def _round(value: Decimal, quantum: Decimal) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise ValueError(f"value must be a Decimal, got {type(value).__name__}")
    if not value.is_finite():
        raise ValueError(f"value must be finite, got {value}")
    # A high precision keeps quantize from signalling InvalidOperation on large values
    # and makes the result independent of the caller's decimal context.
    with localcontext(prec=50):
        result = value.quantize(quantum, rounding=ROUND_HALF_UP)
        if result.is_zero():
            # quantize keeps the sign of a negative zero; never output "-0.00".
            result = abs(result)
    return result


def round_money(value: Decimal) -> Decimal:
    """Round money to 2 decimals, ``ROUND_HALF_UP``."""
    return _round(value, MONEY_QUANTUM)


def round_kwh(value: Decimal) -> Decimal:
    """Round energy to 3 decimals, ``ROUND_HALF_UP``."""
    return _round(value, KWH_QUANTUM)


def round_price(value: Decimal) -> Decimal:
    """Round a price to 4 decimals, ``ROUND_HALF_UP``."""
    return _round(value, PRICE_QUANTUM)
