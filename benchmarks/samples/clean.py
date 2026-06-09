"""Well-structured utility module — used to measure false positive rate."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Result:
    """Encapsulates a value or an error string."""

    value: Optional[float]
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        """Returns True when no error is present."""
        return self.error is None


def safe_divide(numerator: float, denominator: float) -> Result:
    """Divides two numbers, returning Result(error=...) on zero denominator."""
    if denominator == 0.0:
        return Result(value=None, error="division by zero")
    return Result(value=numerator / denominator)


def clamp(value: float, lo: float, hi: float) -> float:
    """Returns value clamped to the inclusive range [lo, hi].

    Raises ValueError if lo > hi.
    """
    if lo > hi:
        raise ValueError(f"lo ({lo}) must not exceed hi ({hi})")
    return max(lo, min(hi, value))


def chunk(items: list, size: int) -> list[list]:
    """Splits items into sublists of at most size elements."""
    if size <= 0:
        raise ValueError("size must be a positive integer")
    return [items[i : i + size] for i in range(0, len(items), size)]
