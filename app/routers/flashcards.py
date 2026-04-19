"""
Flashcards router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models import User, Flashcard, StudyMaterial, SpacedRepetition, ReviewSession, ReviewResponse
from app.schemas import FlashcardCreate, FlashcardResponse, ReviewSessionCreate, ReviewSessionResponse
from app.routers.auth import get_current_user
from app.services.enhanced_ai_service import EnhancedAIService
from app.services.spaced_repetition import SpacedRepetitionService
from app.services.visual_aid import VisualAidService

router = APIRouter()
ai_service = EnhancedAIService()
spaced_repetition_service = SpacedRepetitionService()
visual_aid_service = VisualAidService()


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


@router.get("/", response_model=List[FlashcardResponse])
async def get_flashcards(
    topic_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all flashcards for current user"""
    query = db.query(Flashcard).filter(Flashcard.user_id == current_user.id)
    
    if topic_id:
        query = query.filter(Flashcard.topic_id == topic_id)
    
    flashcards = query.all()
    return flashcards


@router.get("/due", response_model=List[FlashcardResponse])
async def get_due_flashcards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get flashcards due for review"""
    due_sr = spaced_repetition_service.get_due_flashcards(current_user.id, db)
    flashcard_ids = [sr.flashcard_id for sr in due_sr]

    flashcards = db.query(Flashcard).filter(Flashcard.id.in_(flashcard_ids)).all()
    return flashcards


@router.get("/mastered", response_model=List[FlashcardResponse])
async def get_mastered_flashcards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get mastered flashcards only"""
    from app.models import SpacedRepetition
    mastered_sr = db.query(SpacedRepetition).filter(
        SpacedRepetition.user_id == current_user.id,
        SpacedRepetition.mastery_level == "mastered"
    ).all()
    flashcard_ids = [sr.flashcard_id for sr in mastered_sr]
    if not flashcard_ids:
        return []
    flashcards = db.query(Flashcard).filter(
        Flashcard.id.in_(flashcard_ids),
        Flashcard.user_id == current_user.id
    ).all()
    return flashcards


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
    
    return flashcard


@router.post("/review", response_model=ReviewSessionResponse)
async def create_review_session(
    review_data: ReviewSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a review session and record responses"""
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

