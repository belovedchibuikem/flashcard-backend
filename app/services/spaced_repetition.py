"""
Spaced repetition persistence — SuperMemo 2 math lives in ``app.sm2_core``.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import or_

from app import sm2_core
from app.models import SpacedRepetition, MasteryLevel


class SpacedRepetitionService:
    """SM-2 scheduling: ease factor, interval_days, and next_review_at."""

    def __init__(self) -> None:
        self.initial_ease_factor = sm2_core.INITIAL_EASE_FACTOR

    def quality_from_review(
        self, is_correct: bool, confidence_level: Optional[str]
    ) -> int:
        return sm2_core.quality_from_review(is_correct, confidence_level)

    def calculate_next_review(
        self,
        current_ease_factor: Decimal,
        current_interval: int,
        repetitions: int,
        quality: int,
    ):
        return sm2_core.calculate_next_review(
            current_ease_factor,
            current_interval,
            repetitions,
            quality,
            initial_ease_factor=self.initial_ease_factor,
        )

    def update_mastery_level(
        self,
        repetitions: int,
        consecutive_correct: int,
        consecutive_incorrect: int,
    ) -> MasteryLevel:
        if consecutive_incorrect >= 3:
            return MasteryLevel.LEARNING
        if repetitions >= 5 and consecutive_correct >= 3:
            return MasteryLevel.MASTERED
        if repetitions >= 2:
            return MasteryLevel.REVIEWING
        return MasteryLevel.LEARNING

    def get_due_flashcards(self, user_id: int, db) -> list[SpacedRepetition]:
        now = datetime.now()
        return (
            db.query(SpacedRepetition)
            .filter(
                SpacedRepetition.user_id == user_id,
                or_(
                    SpacedRepetition.next_review_at.is_(None),
                    SpacedRepetition.next_review_at <= now,
                ),
            )
            .order_by(SpacedRepetition.next_review_at.asc())
            .all()
        )

    def initialize_spaced_repetition(
        self, user_id: int, flashcard_id: int, db, *, commit: bool = True
    ) -> SpacedRepetition:
        next_review = datetime.now()

        sr = SpacedRepetition(
            user_id=user_id,
            flashcard_id=flashcard_id,
            ease_factor=self.initial_ease_factor,
            interval_days=1,
            repetitions=0,
            next_review_at=next_review,
            mastery_level=MasteryLevel.LEARNING,
        )

        db.add(sr)
        if commit:
            db.commit()
            db.refresh(sr)

        return sr

    def record_review(
        self,
        spaced_repetition: SpacedRepetition,
        is_correct: bool,
        confidence_level: str,
        db,
    ) -> SpacedRepetition:
        quality = self.quality_from_review(is_correct, confidence_level)
        passed = quality >= 3

        if passed:
            spaced_repetition.consecutive_correct += 1
            spaced_repetition.consecutive_incorrect = 0
        else:
            spaced_repetition.consecutive_incorrect += 1
            spaced_repetition.consecutive_correct = 0

        new_ease, new_interval, next_review, new_reps = self.calculate_next_review(
            spaced_repetition.ease_factor,
            spaced_repetition.interval_days,
            spaced_repetition.repetitions,
            quality,
        )

        spaced_repetition.ease_factor = new_ease
        spaced_repetition.interval_days = new_interval
        spaced_repetition.repetitions = new_reps
        spaced_repetition.last_reviewed_at = datetime.now()
        spaced_repetition.next_review_at = next_review
        spaced_repetition.mastery_level = self.update_mastery_level(
            spaced_repetition.repetitions,
            spaced_repetition.consecutive_correct,
            spaced_repetition.consecutive_incorrect,
        )

        db.commit()
        db.refresh(spaced_repetition)

        return spaced_repetition
