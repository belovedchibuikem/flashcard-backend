"""
Practice Questions and Exams router
"""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models import (
    User,
    PracticeQuestion,
    PracticeExamAttempt,
    PracticeExamResponse as PracticeExamResponseModel,
    StudyMaterial,
    Topic,
    DifficultyLevel,
)
from app.schemas import (
    PracticeQuestionResponse,
    PracticeExamCreate,
    PracticeDecksSummaryResponse,
    PracticeMaterialDeckSummary,
    PracticeTopicDeckSummary,
)
from app.routers.auth import get_current_user
from app.services.enhanced_ai_service import EnhancedAIService

router = APIRouter()
ai_service = EnhancedAIService()
logger = logging.getLogger(__name__)

# Must match database/schema_postgresql.sql question_type_enum
_PRACTICE_QUESTION_TYPES = frozenset(
    {"mcq", "short_answer", "essay", "true_false", "case_study"}
)


def _normalize_practice_question_type(raw: str) -> str:
    t = (raw or "mcq").strip().lower()
    if t in _PRACTICE_QUESTION_TYPES:
        return t
    if t in ("multiple_choice", "multiple-choice", "multi"):
        return "mcq"
    if t in ("tf", "true/false"):
        return "true_false"
    return "mcq"


def _coerce_difficulty(raw) -> DifficultyLevel:
    """Map LLM output to DB enum; invalid values cause Postgres/MySQL enum errors."""
    if raw is None:
        return DifficultyLevel.MEDIUM
    s = str(raw).strip().lower()
    for level in DifficultyLevel:
        if level.value == s:
            return level
    return DifficultyLevel.MEDIUM


def _coerce_options(raw) -> list:
    """Ensure JSON-serializable list of strings for MCQ options."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if x is not None]
    if isinstance(raw, dict):
        return [str(v) for v in raw.values() if v is not None]
    return [str(raw)]


def _coerce_relevance(raw) -> float:
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, v))


def _practice_question_rows_query(db: Session, user_id: int):
    return (
        db.query(PracticeQuestion, StudyMaterial.title)
        .outerjoin(
            StudyMaterial,
            and_(
                PracticeQuestion.study_material_id == StudyMaterial.id,
                StudyMaterial.user_id == user_id,
            ),
        )
        .filter(PracticeQuestion.user_id == user_id)
    )


def _apply_practice_question_filters(
    q,
    *,
    topic_id: Optional[int],
    study_material_id: Optional[int],
    uncategorized: bool,
    difficulty: Optional[str],
):
    if topic_id is not None:
        q = q.filter(PracticeQuestion.topic_id == topic_id)
    if uncategorized:
        q = q.filter(PracticeQuestion.study_material_id.is_(None))
    elif study_material_id is not None:
        q = q.filter(PracticeQuestion.study_material_id == study_material_id)
    if difficulty:
        q = q.filter(PracticeQuestion.difficulty_level == _coerce_difficulty(difficulty))
    return q


def _rows_to_practice_responses(rows) -> List[PracticeQuestionResponse]:
    out: List[PracticeQuestionResponse] = []
    for r in rows:
        pq, title = r[0], r[1]
        data = PracticeQuestionResponse.model_validate(pq).model_dump()
        data["study_material_title"] = title
        out.append(PracticeQuestionResponse(**data))
    return out


def _practice_question_from_ai(
    ai_q: dict,
    *,
    user_id: int,
    study_material_id: int,
    question_type: str,
) -> PracticeQuestion:
    qt = _normalize_practice_question_type(question_type)
    rel = Decimal(str(round(_coerce_relevance(ai_q.get("predicted_exam_relevance")), 2)))
    return PracticeQuestion(
        user_id=user_id,
        study_material_id=study_material_id,
        question_text=str(ai_q.get("question_text") or "").strip() or "(No question text)",
        question_type=qt,
        correct_answer=str(ai_q.get("correct_answer") or "").strip(),
        options=_coerce_options(ai_q.get("options")),
        explanation=str(ai_q.get("explanation") or "").strip() or None,
        difficulty_level=_coerce_difficulty(ai_q.get("difficulty")),
        predicted_exam_relevance=rel,
    )


@router.post("/generate/{material_id}", response_model=List[PracticeQuestionResponse])
async def generate_practice_questions(
    material_id: int,
    question_type: str = "mcq",
    count: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate practice questions from study material"""
    question_type = _normalize_practice_question_type(question_type)
    material = db.query(StudyMaterial).filter(
        StudyMaterial.id == material_id,
        StudyMaterial.user_id == current_user.id
    ).first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    if not (material.extracted_text or "").strip():
        raise HTTPException(status_code=400, detail="Material not processed yet")
    
    # Generate questions using AI
    ai_questions = await ai_service.generate_practice_questions(
        material.extracted_text,
        question_type,
        count
    )
    if not ai_questions:
        raise HTTPException(
            status_code=502,
            detail="No questions were generated. Check OpenAI API key and quota, then try again.",
        )

    created_questions = []
    for ai_q in ai_questions:
        if not isinstance(ai_q, dict):
            continue
        question = _practice_question_from_ai(
            ai_q,
            user_id=current_user.id,
            study_material_id=material_id,
            question_type=question_type,
        )
        db.add(question)
        created_questions.append(question)

    if not created_questions:
        raise HTTPException(
            status_code=500,
            detail="AI returned data but no valid question objects could be built.",
        )

    try:
        db.commit()
        for q in created_questions:
            db.refresh(q)
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("practice questions commit failed")
        detail = str(getattr(e, "orig", None) or e)
        if len(detail) > 480:
            detail = detail[:480] + "…"
        raise HTTPException(
            status_code=500,
            detail=f"Could not save generated questions: {detail}",
        )

    return created_questions


@router.get("/decks/summary", response_model=PracticeDecksSummaryResponse)
async def practice_decks_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Counts of practice questions per course (material) and topic — for exam picker UI."""
    mat_rows = (
        db.query(
            StudyMaterial.id,
            StudyMaterial.title,
            StudyMaterial.file_type,
            func.count(PracticeQuestion.id),
        )
        .join(PracticeQuestion, PracticeQuestion.study_material_id == StudyMaterial.id)
        .filter(StudyMaterial.user_id == current_user.id)
        .group_by(StudyMaterial.id, StudyMaterial.title, StudyMaterial.file_type)
        .order_by(StudyMaterial.title.asc())
        .all()
    )
    topic_rows = (
        db.query(
            Topic.id,
            Topic.name,
            Topic.color_code,
            func.count(PracticeQuestion.id),
        )
        .join(PracticeQuestion, PracticeQuestion.topic_id == Topic.id)
        .filter(Topic.user_id == current_user.id)
        .group_by(Topic.id, Topic.name, Topic.color_code)
        .order_by(Topic.name.asc())
        .all()
    )
    uncategorized = (
        db.query(func.count(PracticeQuestion.id))
        .filter(
            PracticeQuestion.user_id == current_user.id,
            PracticeQuestion.study_material_id.is_(None),
        )
        .scalar()
        or 0
    )
    return PracticeDecksSummaryResponse(
        by_material=[
            PracticeMaterialDeckSummary(
                id=r[0],
                title=r[1],
                file_type=str(r[2]),
                question_count=int(r[3]),
            )
            for r in mat_rows
        ],
        by_topic=[
            PracticeTopicDeckSummary(
                id=r[0],
                name=r[1],
                color_code=r[2],
                question_count=int(r[3]),
            )
            for r in topic_rows
        ],
        uncategorized_count=int(uncategorized),
    )


@router.get("/questions", response_model=List[PracticeQuestionResponse])
async def get_practice_questions(
    topic_id: Optional[int] = None,
    study_material_id: Optional[int] = None,
    uncategorized: bool = False,
    difficulty: Optional[str] = None,
    count: Optional[int] = 10,
    auto_generate: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get practice questions. Filter by study_material_id (course deck), topic, or uncategorized only."""

    def fetch_rows():
        q = _practice_question_rows_query(db, current_user.id)
        q = _apply_practice_question_filters(
            q,
            topic_id=topic_id,
            study_material_id=study_material_id,
            uncategorized=uncategorized,
            difficulty=difficulty,
        )
        return q.order_by(PracticeQuestion.id.asc()).all()

    rows = fetch_rows()

    if not rows and auto_generate:
        materials = db.query(StudyMaterial).filter(
            StudyMaterial.user_id == current_user.id
        ).all()
        material = next(
            (
                m
                for m in materials
                if m.extracted_text and len((m.extracted_text or "").strip()) >= 50
            ),
            None,
        )
        if material:
            ai_questions = await ai_service.generate_practice_questions(
                material.extracted_text, "mcq", count or 10
            )
            created: List[PracticeQuestion] = []
            for ai_q in ai_questions:
                if not isinstance(ai_q, dict):
                    continue
                q_obj = _practice_question_from_ai(
                    ai_q,
                    user_id=current_user.id,
                    study_material_id=material.id,
                    question_type="mcq",
                )
                db.add(q_obj)
                created.append(q_obj)
            try:
                db.commit()
                for q_obj in created:
                    db.refresh(q_obj)
            except SQLAlchemyError as e:
                db.rollback()
                logger.exception("practice auto_generate commit failed")
                detail = str(getattr(e, "orig", None) or e)
                if len(detail) > 480:
                    detail = detail[:480] + "…"
                raise HTTPException(
                    status_code=500,
                    detail=f"Could not save generated questions: {detail}",
                )
            rows = fetch_rows()

    items = _rows_to_practice_responses(rows)
    if count is not None and count > 0:
        items = items[:count]
    return items


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
            "exam_label": getattr(e, "exam_label", None),
            "study_material_id": getattr(e, "study_material_id", None),
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
    exam_label = (exam_data.exam_label or "").strip()
    if len(exam_label) > 255:
        exam_label = exam_label[:255]

    exam_attempt = PracticeExamAttempt(
        user_id=current_user.id,
        topic_id=exam_data.topic_id,
        study_material_id=exam_data.study_material_id,
        exam_label=exam_label or None,
        exam_type=exam_data.exam_type,
        total_questions=len(exam_data.responses),
        correct_answers=sum(1 for r in exam_data.responses if r.is_correct),
        time_limit_minutes=exam_data.time_limit_minutes,
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

