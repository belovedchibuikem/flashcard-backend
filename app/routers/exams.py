"""
Exams router - Exam management, history, question banks, readiness predictor
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

from app.database import get_db
from app.models import (
    User, Exam, ExamHistory, QuestionBank, QuestionBankItem, PracticeQuestion,
    ReviewResponse, ReviewSession, Flashcard, Topic
)
from app.routers.auth import get_current_user
from app.services.enhanced_ai_service import EnhancedAIService
from pydantic import BaseModel

router = APIRouter()
ai_service = EnhancedAIService()


# Schemas
class ExamCreate(BaseModel):
    name: str
    description: Optional[str] = None
    exam_date: datetime
    subject: Optional[str] = None
    topic_id: Optional[int] = None


class ExamResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    exam_date: datetime
    subject: Optional[str]
    topic_id: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ExamHistoryCreate(BaseModel):
    exam_id: int
    score_percentage: Decimal
    total_questions: int
    correct_answers: int
    time_spent_minutes: int
    weak_topics: Optional[List[str]] = None


class ExamHistoryResponse(BaseModel):
    id: int
    exam_id: int
    attempt_number: int
    score_percentage: Decimal
    total_questions: int
    correct_answers: int
    time_spent_minutes: int
    weak_topics: Optional[List[str]]
    completed_at: datetime
    
    class Config:
        from_attributes = True


class QuestionBankCreate(BaseModel):
    name: str
    description: Optional[str] = None
    exam_id: Optional[int] = None
    topic_id: Optional[int] = None


class QuestionBankResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    question_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ExamReadinessResponse(BaseModel):
    predicted_score: float
    confidence: float
    weak_areas: List[str]
    recommended_study_time: int
    readiness_level: str


@router.post("/", response_model=ExamResponse)
async def create_exam(
    exam_data: ExamCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new exam"""
    exam = Exam(
        user_id=current_user.id,
        name=exam_data.name,
        description=exam_data.description,
        exam_date=exam_data.exam_date,
        subject=exam_data.subject,
        topic_id=exam_data.topic_id
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


@router.get("/", response_model=List[ExamResponse])
async def get_exams(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's exams"""
    exams = db.query(Exam).filter(Exam.user_id == current_user.id).order_by(Exam.exam_date).all()
    return exams


@router.post("/history", response_model=ExamHistoryResponse)
async def create_exam_history(
    history_data: ExamHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record exam attempt history"""
    # Get last attempt number
    last_attempt = db.query(func.max(ExamHistory.attempt_number)).filter(
        and_(
            ExamHistory.exam_id == history_data.exam_id,
            ExamHistory.user_id == current_user.id
        )
    ).scalar() or 0
    
    history = ExamHistory(
        exam_id=history_data.exam_id,
        user_id=current_user.id,
        attempt_number=last_attempt + 1,
        score_percentage=history_data.score_percentage,
        total_questions=history_data.total_questions,
        correct_answers=history_data.correct_answers,
        time_spent_minutes=history_data.time_spent_minutes,
        weak_topics=history_data.weak_topics or []
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    
    return history


@router.get("/history", response_model=List[ExamHistoryResponse])
async def get_exam_history(
    exam_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get exam history"""
    query = db.query(ExamHistory).filter(ExamHistory.user_id == current_user.id)
    
    if exam_id:
        query = query.filter(ExamHistory.exam_id == exam_id)
    
    return query.order_by(ExamHistory.completed_at.desc()).all()


@router.post("/question-banks", response_model=QuestionBankResponse)
async def create_question_bank(
    bank_data: QuestionBankCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a question bank"""
    bank = QuestionBank(
        user_id=current_user.id,
        name=bank_data.name,
        description=bank_data.description,
        exam_id=bank_data.exam_id,
        topic_id=bank_data.topic_id
    )
    db.add(bank)
    db.commit()
    db.refresh(bank)
    
    return bank


@router.get("/question-banks", response_model=List[QuestionBankResponse])
async def get_question_banks(
    exam_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get question banks"""
    query = db.query(QuestionBank).filter(QuestionBank.user_id == current_user.id)
    
    if exam_id:
        query = query.filter(QuestionBank.exam_id == exam_id)
    
    banks = query.all()
    
    # Get question counts
    result = []
    for bank in banks:
        count = db.query(func.count(QuestionBankItem.id)).filter(
            QuestionBankItem.bank_id == bank.id
        ).scalar()
        bank.question_count = count
        result.append(bank)
    
    return result


@router.post("/question-banks/{bank_id}/add-question")
async def add_question_to_bank(
    bank_id: int,
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a question to a question bank"""
    bank = db.query(QuestionBank).filter(
        and_(
            QuestionBank.id == bank_id,
            QuestionBank.user_id == current_user.id
        )
    ).first()
    
    if not bank:
        raise HTTPException(status_code=404, detail="Question bank not found")
    
    # Check if question already in bank
    existing = db.query(QuestionBankItem).filter(
        and_(
            QuestionBankItem.bank_id == bank_id,
            QuestionBankItem.practice_question_id == question_id
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Question already in bank")
    
    item = QuestionBankItem(
        bank_id=bank_id,
        practice_question_id=question_id
    )
    db.add(item)
    
    # Update question count
    bank.question_count = db.query(func.count(QuestionBankItem.id)).filter(
        QuestionBankItem.bank_id == bank_id
    ).scalar()
    
    db.commit()
    
    return {"message": "Question added to bank"}


@router.get("/{exam_id}/readiness", response_model=ExamReadinessResponse)
async def predict_exam_readiness(
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Predict exam readiness based on performance"""
    # Get user's performance history
    history = db.query(ExamHistory).filter(
        and_(
            ExamHistory.exam_id == exam_id,
            ExamHistory.user_id == current_user.id
        )
    ).order_by(ExamHistory.completed_at.desc()).limit(10).all()
    
    # Get recent review responses
    recent_reviews = db.query(ReviewResponse).join(
        ReviewSession
    ).filter(
        ReviewSession.user_id == current_user.id
    ).order_by(ReviewResponse.reviewed_at.desc()).limit(50).all()
    
    # Prepare performance data
    performance_data = {
        "exam_history": [
            {
                "score": float(h.score_percentage),
                "attempt": h.attempt_number,
                "weak_topics": h.weak_topics or []
            }
            for h in history
        ],
        "recent_reviews": [
            {
                "is_correct": r.is_correct,
                "confidence": r.confidence_level
            }
            for r in recent_reviews
        ]
    }
    
    # Get exam topic (would need Exam model)
    # For now, use a default
    exam_topic = "General"
    
    # Use AI to predict readiness
    prediction = await ai_service.predict_exam_score(performance_data, exam_topic)
    
    return {
        "predicted_score": prediction.get("predicted_score", 70.0),
        "confidence": prediction.get("confidence", 0.7),
        "weak_areas": prediction.get("weak_areas", []),
        "recommended_study_time": prediction.get("recommended_study_time", 10),
        "readiness_level": prediction.get("readiness_level", "almost_ready")
    }


@router.get("/weak-topics")
async def get_weak_topics(
    exam_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get weak topics that need focus"""
    # Get exam history with weak topics
    query = db.query(ExamHistory).filter(ExamHistory.user_id == current_user.id)
    
    if exam_id:
        query = query.filter(ExamHistory.exam_id == exam_id)
    
    histories = query.all()
    
    # Aggregate weak topics
    weak_topics_map = {}
    for history in histories:
        weak_topics = history.weak_topics or []
        for topic in weak_topics:
            weak_topics_map[topic] = weak_topics_map.get(topic, 0) + 1
    
    # Sort by frequency
    weak_topics = sorted(weak_topics_map.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "weak_topics": [{"topic": topic, "frequency": freq} for topic, freq in weak_topics[:10]]
    }
