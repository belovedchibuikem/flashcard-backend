"""
Flashcards router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple, Dict
from datetime import datetime
from app.database import get_db
from app.models import (
    User,
    Flashcard,
    StudyMaterial,
    Topic,
    SpacedRepetition,
    ReviewSession,
    ReviewResponse,
    ReviewIdempotencyKey,
)
from app.schemas import (
    FlashcardCreate,
    FlashcardResponse,
    FlashcardListItem,
    FlashcardDecksSummaryResponse,
    FlashcardMaterialDeckSummary,
    FlashcardTopicDeckSummary,
    ReviewSessionCreate,
    ReviewSessionResponse,
    SpacedRepetitionSnapshot,
)
from app.routers.auth import get_current_user
from app.services.enhanced_ai_service import EnhancedAIService
from app.services.spaced_repetition import SpacedRepetitionService
from app.services.visual_aid import VisualAidService

router = APIRouter()
ai_service = EnhancedAIService()
spaced_repetition_service = SpacedRepetitionService()
visual_aid_service = VisualAidService()


def _flashcard_list_query(db: Session, user_id: int):
    """Base query: flashcard + optional study material title + topic name (same user)."""
    return (
        db.query(Flashcard, StudyMaterial.title, Topic.name)
        .outerjoin(
            StudyMaterial,
            and_(
                Flashcard.study_material_id == StudyMaterial.id,
                StudyMaterial.user_id == user_id,
            ),
        )
        .outerjoin(
            Topic,
            and_(
                Flashcard.topic_id == Topic.id,
                Topic.user_id == user_id,
            ),
        )
        .filter(Flashcard.user_id == user_id)
    )


def _apply_deck_filters(
    q,
    *,
    study_material_id: Optional[int] = None,
    uncategorized: bool = False,
    topic_id: Optional[int] = None,
):
    if uncategorized:
        q = q.filter(Flashcard.study_material_id.is_(None))
    elif study_material_id is not None:
        q = q.filter(Flashcard.study_material_id == study_material_id)
    if topic_id is not None:
        q = q.filter(Flashcard.topic_id == topic_id)
    return q


def _mastery_to_str(m) -> str:
    if m is None:
        return "learning"
    if hasattr(m, "value"):
        return str(m.value)
    return str(m)


def _sr_to_snapshot(sr: SpacedRepetition) -> SpacedRepetitionSnapshot:
    return SpacedRepetitionSnapshot(
        ease_factor=sr.ease_factor,
        interval_days=sr.interval_days,
        repetitions=sr.repetitions,
        last_reviewed_at=sr.last_reviewed_at,
        next_review_at=sr.next_review_at,
        mastery_level=_mastery_to_str(sr.mastery_level),
        consecutive_correct=sr.consecutive_correct,
        consecutive_incorrect=sr.consecutive_incorrect,
    )


def _sr_map_by_flashcard_id(
    db: Session, user_id: int, flashcard_ids: List[int]
) -> Dict[int, SpacedRepetitionSnapshot]:
    if not flashcard_ids:
        return {}
    q = (
        db.query(SpacedRepetition)
        .filter(
            SpacedRepetition.user_id == user_id,
            SpacedRepetition.flashcard_id.in_(flashcard_ids),
        )
    )
    return {r.flashcard_id: _sr_to_snapshot(r) for r in q.all()}


def _rows_to_list_items(
    db: Session, user_id: int, rows: List[Tuple]
) -> List[FlashcardListItem]:
    if not rows:
        return []
    card_ids = [row[0].id for row in rows]
    sr_map = _sr_map_by_flashcard_id(db, user_id, card_ids)
    out: List[FlashcardListItem] = []
    for row in rows:
        card, mat_title, topic_name = row[0], row[1], row[2]
        data = FlashcardResponse.model_validate(card).model_dump()
        data["study_material_title"] = mat_title
        data["topic_name"] = topic_name
        if sr_map.get(card.id) is not None:
            data["spaced_repetition"] = sr_map[card.id]
        else:
            data["spaced_repetition"] = None
        out.append(FlashcardListItem.model_validate(data))
    return out


def _coerce_tags(raw) -> list:
    """LLMs sometimes return tags as dict or non-list; DB/JSON expects list of strings."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, dict):
        return []
    return []


@router.post("/generate/{material_id}", response_model=List[FlashcardResponse])
async def generate_flashcards(
    material_id: int,
    count: int = 10,
    enrich_visuals: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate flashcards from study material using AI.

    enrich_visuals: When True, runs extra OpenAI calls per card (description + DALL·E).
    Default False — fast, cheap, fits serverless timeouts; set True only if you need images.
    """
    material = db.query(StudyMaterial).filter(
        StudyMaterial.id == material_id,
        StudyMaterial.user_id == current_user.id
    ).first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    if not (material.extracted_text or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Material has no extractable text yet. For PDFs wait for processing; for scanned PDFs/images ensure OCR APIs are configured.",
        )
    
    # Generate flashcards using AI
    ai_flashcards = await ai_service.generate_flashcards(material.extracted_text, count)
    
    if not ai_flashcards:
        if not ai_service.has_any_llm():
            raise HTTPException(
                status_code=503,
                detail=(
                    "AI flashcard generation is not configured. "
                    "Add OPENAI_API_KEY or GOOGLE_GEMINI_API_KEY in Vercel → Settings → Environment Variables, "
                    "then redeploy so the serverless function receives them."
                ),
            )
        hint = getattr(ai_service, "_last_flashcard_error", None) or ""
        msg = (
            "AI returned no flashcards. Check API keys, billing, and OPENAI_MODEL / GOOGLE_GEMINI_MODEL. "
            "See Vercel function logs for details."
        )
        if hint:
            msg = f"{msg} Provider: {hint}"
        raise HTTPException(status_code=502, detail=msg)
    
    created_flashcards = []
    for ai_card in ai_flashcards:
        visual_aid_url = None
        if enrich_visuals:
            visual_description = await ai_service.generate_visual_description(
                ai_card.get('question', ''),
                ai_card.get('type', 'concept')
            )
            visual_aid_url = await visual_aid_service.generate_visual_aid(
                ai_card.get('question', ''),
                visual_description
            )

        flashcard = Flashcard(
            user_id=current_user.id,
            study_material_id=material_id,
            question=ai_card.get('question', ''),
            answer=ai_card.get('answer', ''),
            flashcard_type=ai_card.get('type', 'concept'),
            difficulty_level=ai_card.get('difficulty', 'medium'),
            visual_aid_url=visual_aid_url,
            mnemonic_device=ai_card.get('mnemonic', ''),
            importance_score=ai_card.get('importance_score', 5),
            tags=_coerce_tags(ai_card.get('tags')),
        )
        db.add(flashcard)
        db.flush()
        
        # Initialize spaced repetition
        spaced_repetition_service.initialize_spaced_repetition(
            current_user.id,
            flashcard.id,
            db
        )
        
        created_flashcards.append(flashcard)
    
    db.commit()
    
    return created_flashcards


@router.post("/", response_model=FlashcardResponse, status_code=status.HTTP_201_CREATED)
async def create_flashcard(
    flashcard_data: FlashcardCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a manual flashcard"""
    flashcard = Flashcard(
        user_id=current_user.id,
        topic_id=flashcard_data.topic_id,
        study_material_id=flashcard_data.study_material_id,
        question=flashcard_data.question,
        answer=flashcard_data.answer,
        flashcard_type=flashcard_data.flashcard_type,
        difficulty_level=flashcard_data.difficulty_level,
        tags=flashcard_data.tags,
        importance_score=flashcard_data.importance_score
    )
    db.add(flashcard)
    db.commit()
    db.refresh(flashcard)
    
    # Initialize spaced repetition
    spaced_repetition_service.initialize_spaced_repetition(
        current_user.id,
        flashcard.id,
        db
    )
    
    return flashcard


@router.get("/decks/summary", response_model=FlashcardDecksSummaryResponse)
async def get_flashcard_decks_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deck/course picker: counts per uploaded material (e.g. PDF) and per topic."""
    mat_rows = (
        db.query(
            StudyMaterial.id,
            StudyMaterial.title,
            StudyMaterial.file_type,
            func.count(Flashcard.id).label("cnt"),
        )
        .join(Flashcard, Flashcard.study_material_id == StudyMaterial.id)
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
            func.count(Flashcard.id).label("cnt"),
        )
        .join(Flashcard, Flashcard.topic_id == Topic.id)
        .filter(Topic.user_id == current_user.id)
        .group_by(Topic.id, Topic.name, Topic.color_code)
        .order_by(Topic.name.asc())
        .all()
    )
    uncategorized_count = (
        db.query(func.count(Flashcard.id))
        .filter(
            Flashcard.user_id == current_user.id,
            Flashcard.study_material_id.is_(None),
        )
        .scalar()
        or 0
    )
    return FlashcardDecksSummaryResponse(
        by_material=[
            FlashcardMaterialDeckSummary(
                id=r[0],
                title=r[1],
                file_type=str(r[2]),
                flashcard_count=int(r[3]),
            )
            for r in mat_rows
        ],
        by_topic=[
            FlashcardTopicDeckSummary(
                id=r[0],
                name=r[1],
                color_code=r[2],
                flashcard_count=int(r[3]),
            )
            for r in topic_rows
        ],
        uncategorized_count=int(uncategorized_count),
    )


@router.get("/", response_model=List[FlashcardListItem])
async def get_flashcards(
    topic_id: Optional[int] = None,
    study_material_id: Optional[int] = None,
    uncategorized: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get flashcards; filter by topic and/or source material (course deck) or uncategorized only."""
    q = _flashcard_list_query(db, current_user.id)
    q = _apply_deck_filters(
        q,
        study_material_id=study_material_id,
        uncategorized=uncategorized,
        topic_id=topic_id,
    )
    rows = q.order_by(Flashcard.created_at.desc()).all()
    return _rows_to_list_items(db, current_user.id, rows)


@router.get("/due", response_model=List[FlashcardListItem])
async def get_due_flashcards(
    study_material_id: Optional[int] = None,
    uncategorized: bool = False,
    topic_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get flashcards due for review (SM-2 order), optionally scoped to one deck/course."""
    due_sr = spaced_repetition_service.get_due_flashcards(current_user.id, db)
    if not due_sr:
        return []

    q = _flashcard_list_query(db, current_user.id)
    q = _apply_deck_filters(
        q,
        study_material_id=study_material_id,
        uncategorized=uncategorized,
        topic_id=topic_id,
    )
    rows = q.all()
    by_id = {row[0].id: row for row in rows}
    ordered_rows: List[Tuple] = [
        by_id[sr.flashcard_id]
        for sr in due_sr
        if sr.flashcard_id in by_id
    ]
    if not ordered_rows:
        return []
    return _rows_to_list_items(db, current_user.id, ordered_rows)


@router.get("/mastered", response_model=List[FlashcardListItem])
async def get_mastered_flashcards(
    study_material_id: Optional[int] = None,
    uncategorized: bool = False,
    topic_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get mastered flashcards only, optionally scoped to one deck/course."""
    mastered_sr = db.query(SpacedRepetition).filter(
        SpacedRepetition.user_id == current_user.id,
        SpacedRepetition.mastery_level == "mastered",
    ).all()
    flashcard_ids = [sr.flashcard_id for sr in mastered_sr]
    if not flashcard_ids:
        return []

    q = _flashcard_list_query(db, current_user.id).filter(Flashcard.id.in_(flashcard_ids))
    q = _apply_deck_filters(
        q,
        study_material_id=study_material_id,
        uncategorized=uncategorized,
        topic_id=topic_id,
    )
    rows = q.order_by(Flashcard.id.asc()).all()
    return _rows_to_list_items(db, current_user.id, rows)


@router.get("/{flashcard_id}", response_model=FlashcardResponse)
async def get_flashcard(
    flashcard_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific flashcard"""
    flashcard = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id,
        Flashcard.user_id == current_user.id
    ).first()
    
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    sr = (
        db.query(SpacedRepetition)
        .filter(
            SpacedRepetition.user_id == current_user.id,
            SpacedRepetition.flashcard_id == flashcard_id,
        )
        .first()
    )
    data = FlashcardResponse.model_validate(flashcard).model_dump()
    if sr:
        data["spaced_repetition"] = _sr_to_snapshot(sr)
    else:
        data["spaced_repetition"] = None
    return FlashcardResponse.model_validate(data)


@router.post("/review", response_model=ReviewSessionResponse)
async def create_review_session(
    review_data: ReviewSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a review session and record responses"""
    if review_data.idempotency_key:
        found = (
            db.query(ReviewIdempotencyKey)
            .filter(
                ReviewIdempotencyKey.user_id == current_user.id,
                ReviewIdempotencyKey.idempotency_key == review_data.idempotency_key,
            )
            .first()
        )
        if found:
            prev = (
                db.query(ReviewSession)
                .filter(ReviewSession.id == found.review_session_id)
                .first()
            )
            if prev:
                return prev
    # Create review session
    session = ReviewSession(
        user_id=current_user.id,
        session_type=review_data.session_type,
        topic_id=review_data.topic_id,
        flashcards_reviewed=len(review_data.responses),
        correct_count=sum(1 for r in review_data.responses if r.is_correct),
        incorrect_count=sum(1 for r in review_data.responses if not r.is_correct)
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    # Record individual responses and update spaced repetition
    for response_data in review_data.responses:
        # Create review response
        review_response = ReviewResponse(
            review_session_id=session.id,
            flashcard_id=response_data.flashcard_id,
            is_correct=response_data.is_correct,
            confidence_level=response_data.confidence_level,
            response_time_seconds=response_data.response_time_seconds
        )
        db.add(review_response)
        
        # Update spaced repetition
        sr = db.query(SpacedRepetition).filter(
            SpacedRepetition.user_id == current_user.id,
            SpacedRepetition.flashcard_id == response_data.flashcard_id
        ).first()
        
        if sr:
            spaced_repetition_service.record_review(
                sr,
                response_data.is_correct,
                response_data.confidence_level,
                db
            )
    
    session.completed_at = datetime.now()
    if review_data.idempotency_key:
        db.add(
            ReviewIdempotencyKey(
                user_id=current_user.id,
                idempotency_key=review_data.idempotency_key,
                review_session_id=session.id,
            )
        )
    db.commit()
    db.refresh(session)
    
    return session


@router.delete("/{flashcard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flashcard(
    flashcard_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete flashcard"""
    flashcard = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id,
        Flashcard.user_id == current_user.id
    ).first()
    
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    db.delete(flashcard)
    db.commit()
    return None

