"""
Pure SuperMemo 2 (SM-2) scheduling — no database or FastAPI imports.

Used by SpacedRepetitionService and unit-tested in isolation.
"""

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple

_MIN_EASE = Decimal("1.3")
INITIAL_EASE_FACTOR = Decimal("2.5")


def quality_from_review(is_correct: bool, confidence_level: Optional[str]) -> int:
    """
    Map UI outcome + confidence to SM-2 quality (0–5).

    Correct answers must be >= 3 (successful recall). "Hard" means difficult
    but remembered — the minimum pass grade.
    """
    if not is_correct:
        return 0
    c = (confidence_level or "medium").strip().lower()
    if c == "easy":
        return 5
    if c == "hard":
        return 3
    if c == "medium":
        return 4
    return 4


def ease_delta_for_quality(quality: int) -> Decimal:
    """SM-2 EF change: 0.1 - (5-q) * (0.08 + (5-q) * 0.02)."""
    q = Decimal(str(quality))
    five = Decimal("5")
    t = five - q
    return Decimal("0.1") - t * (Decimal("0.08") + t * Decimal("0.02"))


def calculate_next_review(
    current_ease_factor: Decimal,
    current_interval: int,
    repetitions: int,
    quality: int,
    *,
    initial_ease_factor: Decimal = INITIAL_EASE_FACTOR,
    now: Optional[datetime] = None,
) -> Tuple[Decimal, int, datetime, int]:
    """
    One SM-2 step. ``repetitions`` = successful reviews in the current streak
    *before* this grade.

    Returns: (new_ease_factor, new_interval_days, next_review_at, new_repetitions)
    """
    current_ef = (
        current_ease_factor
        if current_ease_factor is not None
        else initial_ease_factor
    )
    current_interval = max(1, int(current_interval or 1))
    clock = now or datetime.now()

    if quality < 3:
        new_ef = max(_MIN_EASE, current_ef - Decimal("0.2"))
        new_repetitions = 0
        new_interval = 1
    else:
        delta = ease_delta_for_quality(quality)
        new_ef = max(_MIN_EASE, current_ef + delta)
        new_repetitions = repetitions + 1

        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            prod = Decimal(current_interval) * new_ef
            new_interval = max(
                1,
                int(prod.quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
            )

    next_review_at = clock + timedelta(days=new_interval)
    return new_ef, new_interval, next_review_at, new_repetitions
