"""Pure decimal rounding shared by deterministic tools."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def round_half_up(value: float, places: int = 2) -> float:
    """Round a finite number to decimal places using the half-up rule."""
    quantum = Decimal(1).scaleb(-places)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))
