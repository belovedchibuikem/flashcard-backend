"""
Spaced Repetition Algorithm Service
Based on SM-2 algorithm (SuperMemo 2)
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from app.models import SpacedRepetition, MasteryLevel


class SpacedRepetitionService:
    """Service for managing spaced repetition algorithm"""
    
    def __init__(self):
        # SM-2 algorithm parameters
        self.initial_ease_factor = Decimal('2.5')
        self.min_ease_factor = Decimal('1.3')
        self.max_ease_factor = Decimal('2.5')
    
    def calculate_next_review(
        self,
        current_ease_factor: Decimal,
        current_interval: int,
        repetitions: int,
        quality: int  # 0-5 scale (0=complete blackout, 5=perfect response)
    ) -> tuple[Decimal, int, datetime]:
        """
        Calculate next review date based on SM-2 algorithm
        
        Returns: (new_ease_factor, new_interval_days, next_review_date)
        """
        # Update ease factor based on quality
        if quality >= 3:
            # Correct response
            new_ease_factor = current_ease_factor + Decimal('0.1') - Decimal('0.8') * (Decimal('5') - Decimal(str(quality)))
            new_ease_factor = max(self.min_ease_factor, min(self.max_ease_factor, new_ease_factor))
            
            if repetitions == 0:
                new_interval = 1
            elif repetitions == 1:
                new_interval = 6
            else:
                new_interval = int(float(current_interval * new_ease_factor))
            
            new_repetitions = repetitions + 1
        else:
            # Incorrect response - reset
            new_ease_factor = max(self.min_ease_factor, current_ease_factor - Decimal('0.2'))
            new_interval = 1
            new_repetitions = 0
        
        next_review_date = datetime.now() + timedelta(days=new_interval)
        
        return new_ease_factor, new_interval, next_review_date
    
    def update_mastery_level(
        self,
        repetitions: int,
        consecutive_correct: int,
        consecutive_incorrect: int
    ) -> MasteryLevel:
        """
        Determine mastery level based on performance
        """
        if consecutive_incorrect >= 3:
            return MasteryLevel.LEARNING
        elif repetitions >= 5 and consecutive_correct >= 3:
            return MasteryLevel.MASTERED
        elif repetitions >= 2:
            return MasteryLevel.REVIEWING
        else:
            return MasteryLevel.LEARNING
    
    def get_due_flashcards(
        self,
        user_id: int,
        db
    ) -> list[SpacedRepetition]:
        """
        Get flashcards that are due for review
        """
        now = datetime.now()
        return db.query(SpacedRepetition).filter(
            SpacedRepetition.user_id == user_id,
            SpacedRepetition.next_review_at <= now
        ).order_by(SpacedRepetition.next_review_at.asc()).all()
    
    def initialize_spaced_repetition(
        self,
        user_id: int,
        flashcard_id: int,
        db
    ) -> SpacedRepetition:
        """
        Initialize spaced repetition tracking for a new flashcard.
        New cards are due immediately (next_review_at = now) so they appear in Due list.
        """
        next_review = datetime.now()
        
        sr = SpacedRepetition(
            user_id=user_id,
            flashcard_id=flashcard_id,
            ease_factor=self.initial_ease_factor,
            interval_days=1,
            repetitions=0,
            next_review_at=next_review,
            mastery_level=MasteryLevel.LEARNING
        )
        
        db.add(sr)
        db.commit()
        db.refresh(sr)
        
        return sr
    
    def record_review(
        self,
        spaced_repetition: SpacedRepetition,
        is_correct: bool,
        confidence_level: str,
        db
    ) -> SpacedRepetition:
        """
        Record a review and update spaced repetition parameters
        """
        # Map confidence level to quality (0-5)
        quality_map = {
            'easy': 5,
            'medium': 3,
            'hard': 1
        }
        
        if not is_correct:
            quality = 0
        else:
            quality = quality_map.get(confidence_level, 3)
        
        # Update consecutive counts
        if is_correct:
            spaced_repetition.consecutive_correct += 1
            spaced_repetition.consecutive_incorrect = 0
        else:
            spaced_repetition.consecutive_incorrect += 1
            spaced_repetition.consecutive_correct = 0
        
        # Calculate new parameters
        new_ease, new_interval, next_review = self.calculate_next_review(
            spaced_repetition.ease_factor,
            spaced_repetition.interval_days,
            spaced_repetition.repetitions,
            quality
        )
        
        # Update spaced repetition record
        spaced_repetition.ease_factor = new_ease
        spaced_repetition.interval_days = new_interval
        spaced_repetition.repetitions = spaced_repetition.repetitions + 1 if is_correct else 0
        spaced_repetition.last_reviewed_at = datetime.now()
        spaced_repetition.next_review_at = next_review
        spaced_repetition.mastery_level = self.update_mastery_level(
            spaced_repetition.repetitions,
            spaced_repetition.consecutive_correct,
            spaced_repetition.consecutive_incorrect
        )
        
        db.commit()
        db.refresh(spaced_repetition)
        
        return spaced_repetition


