"""
Practice Questions and Exams router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models import User, PracticeQuestion, PracticeExamAttempt, PracticeExamResponse as PracticeExamResponseModel, StudyMaterial
from app.schemas import PracticeQuestionResponse, PracticeExamCreate
from app.routers.auth import get_current_user
from app.services.enhanced_ai_service import EnhancedAIService

router = APIRouter()
ai_service = EnhancedAIService()


@router.post("/generate/{material_id}", response_model=List[PracticeQuestionResponse])
async def generate_practice_questions(
    material_id: int,
    question_type: str = "mcq",
    count: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate practice questions from study material"""
    material = db.query(StudyMaterial).filter(
        StudyMaterial.id == material_id,
        StudyMaterial.user_id == current_user.id
    ).first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    if not material.extracted_text:
        raise HTTPException(status_code=400, detail="Material not processed yet")
    
    # Generate questions using AI
    ai_questions = await ai_service.generate_practice_questions(
        material.extracted_text,
        question_type,
        count
    )
    
    created_questions = []
    for ai_q in ai_questions:
        question = PracticeQuestion(
            user_id=current_user.id,
            study_material_id=material_id,
            question_text=ai_q.get('question_text', ''),
            question_type=question_type,
            correct_answer=ai_q.get('correct_answer', ''),
            options=ai_q.get('options', []),
            explanation=ai_q.get('explanation', ''),
            difficulty_level=ai_q.get('difficulty', 'medium'),
            predicted_exam_relevance=float(ai_q.get('predicted_exam_relevance', 0.5))
        )
        db.add(question)
        created_questions.append(question)
    
    db.commit()
    
    return created_questions


@router.get("/questions", response_model=List[PracticeQuestionResponse])
async def get_practice_questions(
    topic_id: Optional[int] = None,
    difficulty: Optional[str] = None,
    count: Optional[int] = 10,
    auto_generate: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get practice questions. Use count to limit results.
    When auto_generate=true and no questions exist, generates from first available material."""
    query = db.query(PracticeQuestion).filter(PracticeQuestion.user_id == current_user.id)
    
    if topic_id:
        query = query.filter(PracticeQuestion.topic_id == topic_id)
    if difficulty:
        query = query.filter(PracticeQuestion.difficulty_level == difficulty)
    
    questions = query.all()
    
    # Auto-generate from first material when empty and requested
    if not questions and auto_generate:
        materials = db.query(StudyMaterial).filter(
            StudyMaterial.user_id == current_user.id
        ).all()
        material = next((m for m in materials if m.extracted_text and len((m.extracted_text or "").strip()) >= 50), None)
        if material:
            ai_questions = await ai_service.generate_practice_questions(
                material.extracted_text, "mcq", count or 10
            )
            for ai_q in ai_questions:
                q = PracticeQuestion(
                    user_id=current_user.id,
                    study_material_id=material.id,
                    question_text=ai_q.get('question_text', ''),
                    question_type='mcq',
                    correct_answer=ai_q.get('correct_answer', ''),
                    options=ai_q.get('options', []),
                    explanation=ai_q.get('explanation', ''),
                    difficulty_level=ai_q.get('difficulty', 'medium'),
                    predicted_exam_relevance=float(ai_q.get('predicted_exam_relevance', 0.5))
                )
                db.add(q)
                questions.append(q)
            db.commit()
    
    if count is not None and count > 0:
        questions = questions[:count]
    return questions


@router.get("/exams")
async def get_recent_exams(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent practice exam attempts"""
    exams = db.query(PracticeExamAttempt).filter(
        PracticeExamAttempt.user_id == current_user.id
    ).order_by(PracticeExamAttempt.completed_at.desc()).limit(limit).all()
    return [
        {
            "id": e.id,
            "exam_type": e.exam_type,
            "score_percentage": float(e.score_percentage) if e.score_percentage else 0,
            "correct_answers": e.correct_answers,
            "total_questions": e.total_questions,
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
        }
        for e in exams
    ]


@router.post("/exam", status_code=status.HTTP_201_CREATED)
async def create_practice_exam(
    exam_data: PracticeExamCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create and submit practice exam"""
    # Create exam attempt
    exam_attempt = PracticeExamAttempt(
        user_id=current_user.id,
        topic_id=exam_data.topic_id,
        exam_type=exam_data.exam_type,
        total_questions=len(exam_data.responses),
        correct_answers=sum(1 for r in exam_data.responses if r.is_correct),
        time_limit_minutes=exam_data.time_limit_minutes
    )
    db.add(exam_attempt)
    db.commit()
    db.refresh(exam_attempt)
    
    # Record responses
    total_points = 0
    for response_data in exam_data.responses:
        question = db.query(PracticeQuestion).filter(
            PracticeQuestion.id == response_data.question_id
        ).first()
        
        points = 1.0 if response_data.is_correct else 0.0
        
        exam_response = PracticeExamResponseModel(
            exam_attempt_id=exam_attempt.id,
            question_id=response_data.question_id,
            user_answer=response_data.user_answer,
            is_correct=response_data.is_correct,
            points_earned=points
        )
        db.add(exam_response)
        total_points += points
    
    # Calculate score
    exam_attempt.score_percentage = (total_points / len(exam_data.responses)) * 100 if exam_data.responses else 0
    exam_attempt.completed_at = datetime.now()
    
    db.commit()
    db.refresh(exam_attempt)
    
    return {
        "exam_id": exam_attempt.id,
        "score_percentage": exam_attempt.score_percentage,
        "correct_answers": exam_attempt.correct_answers,
        "total_questions": exam_attempt.total_questions
    }


@router.get("/exam/{exam_id}")
async def get_exam_results(
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get practice exam results"""
    exam = db.query(PracticeExamAttempt).filter(
        PracticeExamAttempt.id == exam_id,
        PracticeExamAttempt.user_id == current_user.id
    ).first()
    
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    responses = db.query(PracticeExamResponseModel).filter(
        PracticeExamResponseModel.exam_attempt_id == exam_id
    ).all()
    
    return {
        "exam": exam,
        "responses": responses
    }

