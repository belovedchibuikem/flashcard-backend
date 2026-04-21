"""
Analytics and Progress Tracking router
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from typing import List
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.database import get_db
from app.models import (
    User,
    ProgressAnalytics,
    SpacedRepetition,
    ReviewSession,
    PracticeExamAttempt,
    Flashcard,
    MasteryLevel,
)
from app.schemas import ProgressAnalyticsResponse, ExamReadinessResponse
from app.routers.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


def _safe_date_expr(column):
    """Use cast for portability across MySQL and PostgreSQL."""
    return cast(column, Date)


@router.get("/progress", response_model=List[ProgressAnalyticsResponse])
async def get_progress(
    days: int = 30,
    topic_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get progress analytics for specified period.
    Computes from ReviewSession/SpacedRepetition when ProgressAnalytics is empty."""
    try:
        return _get_progress_impl(days, topic_id, current_user, db)
    except Exception as e:
        logger.exception("Analytics progress error: %s", e)
        return []


def _get_progress_impl(days: int, topic_id, current_user, db):
    """Return one row per calendar day in the range (inclusive of today) for stable charts."""
    if days < 1:
        days = 7
    end = date.today()
    start = end - timedelta(days=days - 1)

    date_expr = _safe_date_expr(ReviewSession.started_at)
    session_query = db.query(
        date_expr.label('session_date'),
        func.sum(ReviewSession.flashcards_reviewed).label('studied'),
        func.sum(ReviewSession.correct_count).label('correct'),
    ).filter(
        ReviewSession.user_id == current_user.id,
        date_expr >= start,
        date_expr <= end,
    )
    if topic_id:
        session_query = session_query.filter(ReviewSession.topic_id == topic_id)
    session_query = session_query.group_by(date_expr)
    rows = session_query.all()

    by_day = {}
    for row in rows:
        d = row.session_date
        if isinstance(d, datetime):
            d = d.date()
        studied = int(row.studied or 0)
        correct = int(row.correct or 0)
        mastery = (Decimal(correct) / Decimal(studied) * 100) if studied > 0 else Decimal(0)
        by_day[d] = {
            "date": d,
            "flashcards_studied": studied,
            "flashcards_mastered": correct,
            "practice_questions_answered": 0,
            "practice_questions_correct": 0,
            "study_time_minutes": 0,
            "mastery_percentage": mastery,
            "exam_readiness_score": mastery,
        }

    # Merge stored analytics for days missing from sessions (e.g. legacy data)
    pa_query = db.query(ProgressAnalytics).filter(
        ProgressAnalytics.user_id == current_user.id,
        ProgressAnalytics.date >= start,
        ProgressAnalytics.date <= end,
    )
    if topic_id:
        pa_query = pa_query.filter(ProgressAnalytics.topic_id == topic_id)
    for pa in pa_query.all():
        d = pa.date
        if d not in by_day:
            by_day[d] = {
                "date": d,
                "flashcards_studied": int(pa.flashcards_studied or 0),
                "flashcards_mastered": int(pa.flashcards_mastered or 0),
                "practice_questions_answered": int(pa.practice_questions_answered or 0),
                "practice_questions_correct": int(pa.practice_questions_correct or 0),
                "study_time_minutes": int(pa.study_time_minutes or 0),
                "mastery_percentage": Decimal(pa.mastery_percentage or 0),
                "exam_readiness_score": Decimal(pa.exam_readiness_score or 0),
            }

    result = []
    for i in range(days):
        d = start + timedelta(days=i)
        if d in by_day:
            result.append(by_day[d])
        else:
            result.append({
                "date": d,
                "flashcards_studied": 0,
                "flashcards_mastered": 0,
                "practice_questions_answered": 0,
                "practice_questions_correct": 0,
                "study_time_minutes": 0,
                "mastery_percentage": Decimal(0),
                "exam_readiness_score": Decimal(0),
            })
    return result


@router.get("/readiness", response_model=ExamReadinessResponse)
async def get_exam_readiness(
    topic_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calculate exam readiness score"""
    try:
        return _get_readiness_impl(topic_id, current_user, db)
    except Exception as e:
        logger.exception("Analytics readiness error: %s", e)
        return {
            "overall_readiness": 0.0,
            "topic_readiness": {},
            "weak_areas": [],
            "recommended_study_time": 30
        }


def _get_readiness_impl(topic_id, current_user, db):
    # Scope flashcards for this user (optionally by topic)
    fc_q = db.query(Flashcard).filter(Flashcard.user_id == current_user.id)
    if topic_id:
        fc_q = fc_q.filter(Flashcard.topic_id == topic_id)
    total_user_cards = fc_q.count()

    # Mastery statistics from spaced repetition rows
    sr_query = db.query(SpacedRepetition).filter(
        SpacedRepetition.user_id == current_user.id
    )

    if topic_id:
        flashcards = db.query(Flashcard).filter(
            Flashcard.user_id == current_user.id,
            Flashcard.topic_id == topic_id,
        ).all()
        flashcard_ids = [f.id for f in flashcards]
        if flashcard_ids:
            sr_query = sr_query.filter(SpacedRepetition.flashcard_id.in_(flashcard_ids))
            spaced_repetitions = sr_query.all()
        else:
            spaced_repetitions = []
    else:
        spaced_repetitions = sr_query.all()

    total_flashcards = len(spaced_repetitions)
    mastered = sum(
        1 for sr in spaced_repetitions if sr.mastery_level == MasteryLevel.MASTERED
    )
    reviewing = sum(
        1 for sr in spaced_repetitions if sr.mastery_level == MasteryLevel.REVIEWING
    )

    # Calculate overall readiness
    if total_user_cards == 0:
        overall_readiness = 0.0
    elif total_flashcards == 0:
        # Cards exist but no review history yet — show partial readiness from inventory
        overall_readiness = 25.0
    else:
        overall_readiness = ((mastered * 1.0 + reviewing * 0.6) / total_flashcards) * 100
        if total_user_cards > total_flashcards:
            # Blend down when only some cards have been studied once
            overall_readiness = overall_readiness * (total_flashcards / total_user_cards)
    
    # Get practice exam performance
    exam_query = db.query(PracticeExamAttempt).filter(
        PracticeExamAttempt.user_id == current_user.id
    )
    
    if topic_id:
        exam_query = exam_query.filter(PracticeExamAttempt.topic_id == topic_id)
    
    recent_exams = exam_query.order_by(PracticeExamAttempt.started_at.desc()).limit(5).all()
    avg_exam_score = sum(e.score_percentage for e in recent_exams) / len(recent_exams) if recent_exams else 0
    
    # Combine readiness scores
    final_readiness = (overall_readiness * 0.6 + avg_exam_score * 0.4)
    
    # Identify weak areas
    weak_sr = [sr for sr in spaced_repetitions if sr.consecutive_incorrect >= 2]
    weak_areas = []
    for sr in weak_sr[:5]:  # Top 5 weak areas
        flashcard = db.query(Flashcard).filter(Flashcard.id == sr.flashcard_id).first()
        if flashcard:
            weak_areas.append(flashcard.question[:50] + "...")
    
    return {
        "overall_readiness": final_readiness,
        "topic_readiness": {},  # Would calculate per topic
        "weak_areas": weak_areas,
        "recommended_study_time": max(30, int((100 - final_readiness) / 2))
    }


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get overall statistics. Returns safe defaults on any error."""
    try:
        # Total flashcards
        total_flashcards = db.query(Flashcard).filter(Flashcard.user_id == current_user.id).count()
        
        # Mastered flashcards
        mastered_sr = db.query(SpacedRepetition).filter(
            SpacedRepetition.user_id == current_user.id,
            SpacedRepetition.mastery_level == MasteryLevel.MASTERED,
        ).count()
        
        # Study sessions
        total_sessions = db.query(ReviewSession).filter(
            ReviewSession.user_id == current_user.id
        ).count()
        
        # Practice exams
        total_exams = db.query(PracticeExamAttempt).filter(
            PracticeExamAttempt.user_id == current_user.id
        ).count()
        
        # Study streak (consecutive days with study sessions, max 365 to avoid runaway)
        today = date.today()
        streak = 0
        check_date = today
        date_expr = _safe_date_expr(ReviewSession.started_at)
        for _ in range(365):
            sessions_today = db.query(ReviewSession).filter(
                ReviewSession.user_id == current_user.id,
                date_expr == check_date
            ).count()
            
            if sessions_today > 0:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        
        return {
            "total_flashcards": total_flashcards,
            "mastered_flashcards": mastered_sr,
            "total_sessions": total_sessions,
            "total_exams": total_exams,
            "study_streak": streak,
            "mastery_percentage": (mastered_sr / total_flashcards * 100) if total_flashcards > 0 else 0
        }
    except Exception as e:
        logger.exception("Analytics stats error: %s", e)
        # Return safe defaults so dashboard still renders
        return {
            "total_flashcards": 0,
            "mastered_flashcards": 0,
            "total_sessions": 0,
            "total_exams": 0,
            "study_streak": 0,
            "mastery_percentage": 0
        }


