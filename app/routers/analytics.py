"""
Analytics and Progress Tracking router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List
from datetime import datetime, date, timedelta
from app.database import get_db
from app.models import User, ProgressAnalytics, SpacedRepetition, ReviewSession, PracticeExamAttempt, Flashcard
from app.schemas import ProgressAnalyticsResponse, ExamReadinessResponse
from app.routers.auth import get_current_user

router = APIRouter()


@router.get("/progress", response_model=List[ProgressAnalyticsResponse])
async def get_progress(
    days: int = 30,
    topic_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get progress analytics for specified period.
    Computes from ReviewSession/SpacedRepetition when ProgressAnalytics is empty."""
    start_date = date.today() - timedelta(days=days)
    
    # Try stored ProgressAnalytics first
    query = db.query(ProgressAnalytics).filter(
        ProgressAnalytics.user_id == current_user.id,
        ProgressAnalytics.date >= start_date
    )
    if topic_id:
        query = query.filter(ProgressAnalytics.topic_id == topic_id)
    analytics = query.order_by(ProgressAnalytics.date.asc()).all()
    
    if analytics:
        return analytics
    
    # Compute from ReviewSession when no stored data
    from decimal import Decimal
    from sqlalchemy import cast, Date
    
    session_query = db.query(
        func.date(ReviewSession.started_at).label('session_date'),
        func.sum(ReviewSession.flashcards_reviewed).label('studied'),
        func.sum(ReviewSession.correct_count).label('correct'),
    ).filter(
        ReviewSession.user_id == current_user.id,
        func.date(ReviewSession.started_at) >= start_date
    )
    if topic_id:
        session_query = session_query.filter(ReviewSession.topic_id == topic_id)
    session_query = session_query.group_by(func.date(ReviewSession.started_at))
    rows = session_query.all()
    
    # Build daily progress
    result = []
    for row in rows:
        d = row.session_date
        if isinstance(d, datetime):
            d = d.date()
        studied = int(row.studied or 0)
        correct = int(row.correct or 0)
        mastery = (Decimal(correct) / Decimal(studied) * 100) if studied > 0 else Decimal(0)
        result.append({
            "date": d,
            "flashcards_studied": studied,
            "flashcards_mastered": correct,
            "practice_questions_answered": 0,
            "practice_questions_correct": 0,
            "study_time_minutes": 0,
            "mastery_percentage": mastery,
            "exam_readiness_score": mastery,
        })
    
    # Sort by date ascending for chart
    result.sort(key=lambda x: x["date"])
    return result


@router.get("/readiness", response_model=ExamReadinessResponse)
async def get_exam_readiness(
    topic_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calculate exam readiness score"""
    # Get mastery statistics
    sr_query = db.query(SpacedRepetition).filter(
        SpacedRepetition.user_id == current_user.id
    )
    
    if topic_id:
        flashcards = db.query(Flashcard).filter(Flashcard.topic_id == topic_id).all()
        flashcard_ids = [f.id for f in flashcards]
        sr_query = sr_query.filter(SpacedRepetition.flashcard_id.in_(flashcard_ids))
    
    spaced_repetitions = sr_query.all()
    
    total_flashcards = len(spaced_repetitions)
    mastered = sum(1 for sr in spaced_repetitions if sr.mastery_level == "mastered")
    reviewing = sum(1 for sr in spaced_repetitions if sr.mastery_level == "reviewing")
    
    # Calculate overall readiness
    if total_flashcards == 0:
        overall_readiness = 0.0
    else:
        overall_readiness = ((mastered * 1.0 + reviewing * 0.6) / total_flashcards) * 100
    
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
    """Get overall statistics"""
    # Total flashcards
    total_flashcards = db.query(Flashcard).filter(Flashcard.user_id == current_user.id).count()
    
    # Mastered flashcards
    mastered_sr = db.query(SpacedRepetition).filter(
        SpacedRepetition.user_id == current_user.id,
        SpacedRepetition.mastery_level == "mastered"
    ).count()
    
    # Study sessions
    total_sessions = db.query(ReviewSession).filter(
        ReviewSession.user_id == current_user.id
    ).count()
    
    # Practice exams
    total_exams = db.query(PracticeExamAttempt).filter(
        PracticeExamAttempt.user_id == current_user.id
    ).count()
    
    # Study streak (consecutive days with study sessions)
    today = date.today()
    streak = 0
    check_date = today
    while True:
        sessions_today = db.query(ReviewSession).filter(
            ReviewSession.user_id == current_user.id,
            func.date(ReviewSession.started_at) == check_date
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


