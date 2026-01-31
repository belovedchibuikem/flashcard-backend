"""
Advanced AI Features router - Smart difficulty, concept mapping, adaptive learning
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.database import get_db
from app.models import (
    User, UserKnowledgeProfile, ConceptMap, AdaptiveLearningPath,
    Flashcard, ReviewResponse, ReviewSession, Topic
)
from app.routers.auth import get_current_user
from app.services.enhanced_ai_service import EnhancedAIService
from pydantic import BaseModel

router = APIRouter()
ai_service = EnhancedAIService()


# Schemas
class DifficultyAnalysisResponse(BaseModel):
    current_difficulty: str
    recommended_difficulty: str
    knowledge_gaps: List[str]
    mistake_patterns: List[str]
    mastery_score: float


class ConceptMapResponse(BaseModel):
    id: int
    title: str
    map_data: Dict[str, Any]
    generated_at: str
    
    class Config:
        from_attributes = True


class AdaptivePathResponse(BaseModel):
    id: int
    path_sequence: List[int]
    current_position: int
    
    class Config:
        from_attributes = True


@router.get("/difficulty-analysis/{flashcard_id}", response_model=DifficultyAnalysisResponse)
async def analyze_difficulty(
    flashcard_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze user performance and suggest difficulty adjustment"""
    flashcard = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    # Get user's review responses for this flashcard
    reviews = db.query(ReviewResponse).join(ReviewSession).filter(
        and_(
            ReviewSession.user_id == current_user.id,
            ReviewResponse.flashcard_id == flashcard_id
        )
    ).order_by(ReviewResponse.reviewed_at.desc()).limit(20).all()
    
    user_responses = [
        {
            "is_correct": r.is_correct,
            "confidence": r.confidence_level,
            "response_time": r.response_time_seconds
        }
        for r in reviews
    ]
    
    if not user_responses:
        return {
            "current_difficulty": flashcard.difficulty_level,
            "recommended_difficulty": flashcard.difficulty_level,
            "knowledge_gaps": [],
            "mistake_patterns": [],
            "mastery_score": 50.0
        }
    
    # Use AI to analyze
    analysis = await ai_service.analyze_difficulty(user_responses, flashcard_id)
    
    # Update or create knowledge profile
    profile = db.query(UserKnowledgeProfile).filter(
        and_(
            UserKnowledgeProfile.user_id == current_user.id,
            UserKnowledgeProfile.topic_id == flashcard.topic_id
        )
    ).first()
    
    if not profile:
        profile = UserKnowledgeProfile(
            user_id=current_user.id,
            topic_id=flashcard.topic_id,
            difficulty_level=analysis.get("recommended_difficulty", "medium"),
            mastery_score=analysis.get("mastery_score", 50.0),
            weak_areas=analysis.get("knowledge_gaps", []),
            mistake_patterns=analysis.get("mistake_patterns", [])
        )
        db.add(profile)
    else:
        profile.difficulty_level = analysis.get("recommended_difficulty", profile.difficulty_level)
        profile.mastery_score = analysis.get("mastery_score", profile.mastery_score)
        profile.weak_areas = analysis.get("knowledge_gaps", [])
        profile.mistake_patterns = analysis.get("mistake_patterns", [])
    
    db.commit()
    
    return {
        "current_difficulty": flashcard.difficulty_level,
        "recommended_difficulty": analysis.get("recommended_difficulty", flashcard.difficulty_level),
        "knowledge_gaps": analysis.get("knowledge_gaps", []),
        "mistake_patterns": analysis.get("mistake_patterns", []),
        "mastery_score": analysis.get("mastery_score", 50.0)
    }


@router.post("/concept-maps", response_model=ConceptMapResponse)
async def generate_concept_map(
    topic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a concept map for a topic"""
    topic = db.query(Topic).filter(
        and_(
            Topic.id == topic_id,
            Topic.user_id == current_user.id
        )
    ).first()
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    # Get flashcards for this topic
    flashcards = db.query(Flashcard).filter(
        and_(
            Flashcard.topic_id == topic_id,
            Flashcard.user_id == current_user.id
        )
    ).all()
    
    # Extract concepts from flashcards
    concepts = []
    for fc in flashcards:
        concepts.append(fc.question)
        concepts.append(fc.answer)
    
    if not concepts:
        raise HTTPException(status_code=400, detail="No flashcards found for this topic")
    
    # Generate concept map using AI
    map_data = await ai_service.generate_concept_map(concepts[:50], topic.name)  # Limit to 50 concepts
    
    concept_map = ConceptMap(
        user_id=current_user.id,
        topic_id=topic_id,
        title=f"Concept Map: {topic.name}",
        map_data=map_data
    )
    db.add(concept_map)
    db.commit()
    db.refresh(concept_map)
    
    return {
        "id": concept_map.id,
        "title": concept_map.title,
        "map_data": concept_map.map_data,
        "generated_at": concept_map.generated_at.isoformat()
    }


@router.get("/concept-maps", response_model=List[ConceptMapResponse])
async def get_concept_maps(
    topic_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's concept maps"""
    query = db.query(ConceptMap).filter(ConceptMap.user_id == current_user.id)
    
    if topic_id:
        query = query.filter(ConceptMap.topic_id == topic_id)
    
    maps = query.order_by(ConceptMap.generated_at.desc()).all()
    
    return [
        {
            "id": m.id,
            "title": m.title,
            "map_data": m.map_data,
            "generated_at": m.generated_at.isoformat()
        }
        for m in maps
    ]


@router.post("/adaptive-path", response_model=AdaptivePathResponse)
async def create_adaptive_path(
    topic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create an adaptive learning path"""
    topic = db.query(Topic).filter(
        and_(
            Topic.id == topic_id,
            Topic.user_id == current_user.id
        )
    ).first()
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    # Get user's performance data
    knowledge_profile = db.query(UserKnowledgeProfile).filter(
        and_(
            UserKnowledgeProfile.user_id == current_user.id,
            UserKnowledgeProfile.topic_id == topic_id
        )
    ).first()
    
    # Get flashcards for this topic
    flashcards = db.query(Flashcard).filter(
        and_(
            Flashcard.topic_id == topic_id,
            Flashcard.user_id == current_user.id
        )
    ).all()
    
    performance_data = {
        "weak_areas": knowledge_profile.weak_areas if knowledge_profile else [],
        "strong_areas": knowledge_profile.strong_areas if knowledge_profile else [],
        "mastery_score": float(knowledge_profile.mastery_score) if knowledge_profile else 50.0,
        "flashcard_ids": [f.id for f in flashcards]
    }
    
    # Use AI to suggest path
    path_sequence = await ai_service.suggest_adaptive_path(current_user.id, topic_id, performance_data)
    
    # If AI doesn't return sequence, create default order
    if not path_sequence:
        path_sequence = [f.id for f in flashcards]
    
    adaptive_path = AdaptiveLearningPath(
        user_id=current_user.id,
        topic_id=topic_id,
        path_sequence=path_sequence,
        current_position=0
    )
    db.add(adaptive_path)
    db.commit()
    db.refresh(adaptive_path)
    
    return {
        "id": adaptive_path.id,
        "path_sequence": adaptive_path.path_sequence,
        "current_position": adaptive_path.current_position
    }


@router.get("/adaptive-path/{path_id}", response_model=AdaptivePathResponse)
async def get_adaptive_path(
    path_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get adaptive learning path"""
    path = db.query(AdaptiveLearningPath).filter(
        and_(
            AdaptiveLearningPath.id == path_id,
            AdaptiveLearningPath.user_id == current_user.id
        )
    ).first()
    
    if not path:
        raise HTTPException(status_code=404, detail="Path not found")
    
    return {
        "id": path.id,
        "path_sequence": path.path_sequence,
        "current_position": path.current_position
    }


@router.put("/adaptive-path/{path_id}/advance")
async def advance_adaptive_path(
    path_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Advance to next item in adaptive learning path"""
    path = db.query(AdaptiveLearningPath).filter(
        and_(
            AdaptiveLearningPath.id == path_id,
            AdaptiveLearningPath.user_id == current_user.id
        )
    ).first()
    
    if not path:
        raise HTTPException(status_code=404, detail="Path not found")
    
    if path.current_position < len(path.path_sequence) - 1:
        path.current_position += 1
        db.commit()
    
    return {
        "id": path.id,
        "path_sequence": path.path_sequence,
        "current_position": path.current_position
    }


@router.post("/questions-from-notes")
async def generate_questions_from_notes(
    notes_text: str,
    count: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate questions directly from notes/text"""
    if len(notes_text) < 50:
        raise HTTPException(status_code=400, detail="Notes text too short (minimum 50 characters)")
    
    questions = await ai_service.generate_questions_from_notes(notes_text, count)
    
    return {
        "questions": questions,
        "count": len(questions)
    }


# AI Tutor Chat Endpoints
class TutorMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class TutorResponse(BaseModel):
    response: str
    conversation_id: str
    suggestions: Optional[List[str]] = None


@router.post("/tutor/chat", response_model=TutorResponse)
async def chat_with_tutor(
    message_data: TutorMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Chat with AI tutor about concepts"""
    if not message_data.message or len(message_data.message.strip()) < 3:
        raise HTTPException(status_code=400, detail="Message too short")
    
    # Get user's recent study context
    recent_flashcards = db.query(Flashcard).filter(
        Flashcard.user_id == current_user.id
    ).order_by(Flashcard.created_at.desc()).limit(10).all()
    
    context = ""
    if recent_flashcards:
        context = "Recent flashcards studied:\n"
        for card in recent_flashcards[:5]:
            context += f"Q: {card.question}\nA: {card.answer}\n\n"
    
    # Create prompt for AI tutor
    prompt = f"""
    You are an AI tutor helping a student learn. The student is asking about concepts related to their flashcards.
    
    {context}
    
    Student's question: {message_data.message}
    
    Provide a helpful, educational response. If relevant, reference their recent study materials.
    Keep responses concise but informative. If the question is unclear, ask for clarification.
    """
    
    try:
        response = ai_service.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful AI tutor. Provide clear, educational explanations. Keep responses concise (2-3 paragraphs max)."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        tutor_response = response.choices[0].message.content.strip()
        
        # Generate conversation ID if not provided
        conversation_id = message_data.conversation_id or f"conv_{current_user.id}_{datetime.now().timestamp()}"
        
        # Generate follow-up suggestions
        suggestions_prompt = f"""
        Based on this conversation:
        Student: {message_data.message}
        Tutor: {tutor_response}
        
        Suggest 2-3 follow-up questions the student might want to ask.
        Return as a JSON array of strings.
        """
        
        suggestions_response = ai_service.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Return only a JSON array of suggested questions."},
                {"role": "user", "content": suggestions_prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        import json
        try:
            suggestions = json.loads(suggestions_response.choices[0].message.content.strip())
            if not isinstance(suggestions, list):
                suggestions = []
        except:
            suggestions = []
        
        return {
            "response": tutor_response,
            "conversation_id": conversation_id,
            "suggestions": suggestions[:3] if suggestions else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating tutor response: {str(e)}")
