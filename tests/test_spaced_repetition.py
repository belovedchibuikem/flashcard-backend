"""Unit tests for SM-2 core math (no database or app settings)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.sm2_core import (
    INITIAL_EASE_FACTOR,
    calculate_next_review,
    ease_delta_for_quality,
    quality_from_review,
)


def test_quality_correct_hard_is_minimum_pass() -> None:
    assert quality_from_review(True, "hard") == 3


def test_quality_correct_easy_and_medium() -> None:
    assert quality_from_review(True, "easy") == 5
    assert quality_from_review(True, "medium") == 4


def test_quality_incorrect_ignores_confidence() -> None:
    assert quality_from_review(False, "easy") == 0


def test_first_success_sets_interval_one() -> None:
    ef, interval, _dt, reps = calculate_next_review(
        INITIAL_EASE_FACTOR, 1, 0, quality=5
    )
    assert interval == 1
    assert reps == 1
    assert ef == INITIAL_EASE_FACTOR + ease_delta_for_quality(5)


def test_second_success_sets_interval_six() -> None:
    _, interval, _dt, reps = calculate_next_review(
        INITIAL_EASE_FACTOR, 1, 1, quality=5
    )
    assert interval == 6
    assert reps == 2


def test_third_success_uses_interval_times_ease() -> None:
    _, interval, _dt, reps = calculate_next_review(
        INITIAL_EASE_FACTOR, 6, 2, quality=5
    )
    assert reps == 3
    assert interval == 16  # round(6 * 2.6)


def test_lapse_resets_repetitions_and_short_interval() -> None:
    ef, interval, _dt, reps = calculate_next_review(
        INITIAL_EASE_FACTOR, 20, 5, quality=0
    )
    assert reps == 0
    assert interval == 1
    assert ef == Decimal("2.3")


def test_ease_unchanged_for_quality_four() -> None:
    old = INITIAL_EASE_FACTOR
    ef, _, _, _ = calculate_next_review(old, 6, 2, quality=4)
    assert ef == old


def test_deterministic_clock() -> None:
    t = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    _, _, next_at, _ = calculate_next_review(
        INITIAL_EASE_FACTOR, 1, 0, quality=5, now=t
    )
    assert next_at == t + timedelta(days=1)
