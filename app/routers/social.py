"""
Social features router - Study buddies, collaborative sessions, comments, ratings
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta

from app.database import get_db
from app.models import (
    User, StudyBuddy, CollaborativeSession, CollaborativeSessionParticipant,
    FlashcardComment, DeckRating, Flashcard, StudyGroup, StudyGroupMember,
    SharedDeck, Topic, UserProfile, DailyActivity
)
from app.routers.auth import get_current_user
from pydantic import BaseModel

router = APIRouter()


# Schemas
class StudyBuddyRequest(BaseModel):
    buddy_id: int


class StudyBuddyResponse(BaseModel):
    id: int
    buddy_id: int
    buddy_username: str
    status: str
    
    class Config:
        from_attributes = True


class CollaborativeSessionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    topic_id: Optional[int] = None
    max_participants: int = 10


class CollaborativeSessionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    host_username: str
    participant_count: int
    max_participants: int
    is_active: bool
    
    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    comment_text: str
    parent_comment_id: Optional[int] = None


class CommentResponse(BaseModel):
    id: int
    comment_text: str
    username: str
    parent_comment_id: Optional[int]
    is_edited: bool
    created_at: datetime
    replies: List['CommentResponse'] = []
    
    class Config:
        from_attributes = True


class RatingCreate(BaseModel):
    rating: int  # 1-5
    review_text: Optional[str] = None


class RatingResponse(BaseModel):
    id: int
    rating: int
    review_text: Optional[str]
    username: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Study Buddies Endpoints
@router.post("/buddies/request", response_model=StudyBuddyResponse)
async def request_study_buddy(
    request: StudyBuddyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a study buddy request"""
    if request.buddy_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot add yourself as buddy")
    
    buddy = db.query(User).filter(User.id == request.buddy_id).first()
    if not buddy:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if relationship already exists
    existing = db.query(StudyBuddy).filter(
        or_(
            and_(StudyBuddy.user_id == current_user.id, StudyBuddy.buddy_id == request.buddy_id),
            and_(StudyBuddy.user_id == request.buddy_id, StudyBuddy.buddy_id == current_user.id)
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Buddy relationship already exists")
    
    study_buddy = StudyBuddy(
        user_id=current_user.id,
        buddy_id=request.buddy_id,
        status="pending"
    )
    db.add(study_buddy)
    db.commit()
    db.refresh(study_buddy)
    
    return {
        "id": study_buddy.id,
        "buddy_id": study_buddy.buddy_id,
        "buddy_username": buddy.username,
        "status": study_buddy.status
    }


@router.get("/buddies", response_model=List[StudyBuddyResponse])
async def get_study_buddies(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's study buddies"""
    query = db.query(StudyBuddy, User).join(
        User, StudyBuddy.buddy_id == User.id
    ).filter(StudyBuddy.user_id == current_user.id)
    
    if status_filter:
        query = query.filter(StudyBuddy.status == status_filter)
    
    results = query.all()
    return [
        {
            "id": sb.id,
            "buddy_id": sb.buddy_id,
            "buddy_username": user.username,
            "status": sb.status
        }
        for sb, user in results
    ]


@router.put("/buddies/{buddy_id}/accept")
async def accept_buddy_request(
    buddy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept a study buddy request"""
    request = db.query(StudyBuddy).filter(
        and_(
            StudyBuddy.user_id == buddy_id,
            StudyBuddy.buddy_id == current_user.id,
            StudyBuddy.status == "pending"
        )
    ).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request.status = "accepted"
    db.commit()
    
    return {"message": "Buddy request accepted"}


# Collaborative Sessions Endpoints
@router.post("/collaborative-sessions", response_model=CollaborativeSessionResponse)
async def create_collaborative_session(
    session_data: CollaborativeSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new collaborative study session"""
    session = CollaborativeSession(
        host_id=current_user.id,
        name=session_data.name,
        description=session_data.description,
        topic_id=session_data.topic_id,
        max_participants=session_data.max_participants
    )
    db.add(session)
    
    # Add host as participant
    participant = CollaborativeSessionParticipant(
        session_id=session.id,
        user_id=current_user.id
    )
    db.add(participant)
    db.commit()
    db.refresh(session)
    
    return {
        "id": session.id,
        "name": session.name,
        "description": session.description,
        "host_username": current_user.username,
        "participant_count": 1,
        "max_participants": session.max_participants,
        "is_active": session.is_active
    }


@router.get("/collaborative-sessions", response_model=List[CollaborativeSessionResponse])
async def get_collaborative_sessions(
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get available collaborative sessions"""
    query = db.query(CollaborativeSession, User).join(
        User, CollaborativeSession.host_id == User.id
    )
    
    if active_only:
        query = query.filter(CollaborativeSession.is_active == True)
    
    results = query.all()
    sessions = []
    for session, host in results:
        participant_count = db.query(func.count(CollaborativeSessionParticipant.id)).filter(
            and_(
                CollaborativeSessionParticipant.session_id == session.id,
                CollaborativeSessionParticipant.left_at.is_(None)
            )
        ).scalar()
        
        sessions.append({
            "id": session.id,
            "name": session.name,
            "description": session.description,
            "host_username": host.username,
            "participant_count": participant_count or 0,
            "max_participants": session.max_participants,
            "is_active": session.is_active
        })
    
    return sessions


@router.post("/collaborative-sessions/{session_id}/join")
async def join_collaborative_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join a collaborative study session"""
    session = db.query(CollaborativeSession).filter(
        CollaborativeSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.is_active:
        raise HTTPException(status_code=400, detail="Session is not active")
    
    # Check if already joined
    existing = db.query(CollaborativeSessionParticipant).filter(
        and_(
            CollaborativeSessionParticipant.session_id == session_id,
            CollaborativeSessionParticipant.user_id == current_user.id,
            CollaborativeSessionParticipant.left_at.is_(None)
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Already joined this session")
    
    # Check participant limit
    current_count = db.query(func.count(CollaborativeSessionParticipant.id)).filter(
        and_(
            CollaborativeSessionParticipant.session_id == session_id,
            CollaborativeSessionParticipant.left_at.is_(None)
        )
    ).scalar()
    
    if current_count >= session.max_participants:
        raise HTTPException(status_code=400, detail="Session is full")
    
    participant = CollaborativeSessionParticipant(
        session_id=session_id,
        user_id=current_user.id
    )
    db.add(participant)
    db.commit()
    
    return {"message": "Joined session successfully"}


@router.get("/collaborative-sessions/{session_id}/participants")
async def get_session_participants(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get participants of a collaborative session"""
    session = db.query(CollaborativeSession).filter(
        CollaborativeSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get active participants
    participants = db.query(CollaborativeSessionParticipant, User).join(
        User, CollaborativeSessionParticipant.user_id == User.id
    ).filter(
        and_(
            CollaborativeSessionParticipant.session_id == session_id,
            CollaborativeSessionParticipant.left_at.is_(None)
        )
    ).all()
    
    participant_list = [
        {
            "user_id": p.user_id,
            "username": u.username,
            "joined_at": p.joined_at.isoformat()
        }
        for p, u in participants
    ]
    
    return participant_list


# Comments Endpoints
@router.post("/flashcards/{flashcard_id}/comments", response_model=CommentResponse)
async def create_comment(
    flashcard_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a comment to a flashcard"""
    flashcard = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    comment = FlashcardComment(
        flashcard_id=flashcard_id,
        user_id=current_user.id,
        comment_text=comment_data.comment_text,
        parent_comment_id=comment_data.parent_comment_id
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    return {
        "id": comment.id,
        "comment_text": comment.comment_text,
        "username": current_user.username,
        "parent_comment_id": comment.parent_comment_id,
        "is_edited": comment.is_edited,
        "created_at": comment.created_at,
        "replies": []
    }


@router.get("/flashcards/{flashcard_id}/comments", response_model=List[CommentResponse])
async def get_comments(
    flashcard_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comments for a flashcard"""
    comments = db.query(FlashcardComment, User).join(
        User, FlashcardComment.user_id == User.id
    ).filter(
        and_(
            FlashcardComment.flashcard_id == flashcard_id,
            FlashcardComment.parent_comment_id.is_(None)  # Top-level comments only
        )
    ).order_by(FlashcardComment.created_at.desc()).all()
    
    result = []
    for comment, user in comments:
        # Get replies
        replies = db.query(FlashcardComment, User).join(
            User, FlashcardComment.user_id == User.id
        ).filter(
            FlashcardComment.parent_comment_id == comment.id
        ).order_by(FlashcardComment.created_at).all()
        
        result.append({
            "id": comment.id,
            "comment_text": comment.comment_text,
            "username": user.username,
            "parent_comment_id": comment.parent_comment_id,
            "is_edited": comment.is_edited,
            "created_at": comment.created_at,
            "replies": [
                {
                    "id": r.id,
                    "comment_text": r.comment_text,
                    "username": u.username,
                    "parent_comment_id": r.parent_comment_id,
                    "is_edited": r.is_edited,
                    "created_at": r.created_at,
                    "replies": []
                }
                for r, u in replies
            ]
        })
    
    return result


# Rating Endpoints
@router.post("/decks/{deck_id}/ratings", response_model=RatingResponse)
async def rate_deck(
    deck_id: int,
    rating_data: RatingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rate a flashcard deck"""
    if not (1 <= rating_data.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    # Check if user already rated
    existing = db.query(DeckRating).filter(
        and_(
            DeckRating.deck_id == deck_id,
            DeckRating.user_id == current_user.id
        )
    ).first()
    
    if existing:
        existing.rating = rating_data.rating
        existing.review_text = rating_data.review_text
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        
        return {
            "id": existing.id,
            "rating": existing.rating,
            "review_text": existing.review_text,
            "username": current_user.username,
            "created_at": existing.created_at
        }
    
    rating = DeckRating(
        deck_id=deck_id,
        user_id=current_user.id,
        rating=rating_data.rating,
        review_text=rating_data.review_text
    )
    db.add(rating)
    db.commit()
    db.refresh(rating)
    
    return {
        "id": rating.id,
        "rating": rating.rating,
        "review_text": rating.review_text,
        "username": current_user.username,
        "created_at": rating.created_at
    }


@router.get("/decks/{deck_id}/ratings", response_model=List[RatingResponse])
async def get_deck_ratings(
    deck_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get ratings for a deck"""
    ratings = db.query(DeckRating, User).join(
        User, DeckRating.user_id == User.id
    ).filter(
        DeckRating.deck_id == deck_id
    ).order_by(DeckRating.created_at.desc()).all()
    
    return [
        {
            "id": r.id,
            "rating": r.rating,
            "review_text": r.review_text,
            "username": u.username,
            "created_at": r.created_at
        }
        for r, u in ratings
    ]


@router.get("/decks/{deck_id}/rating-summary")
async def get_rating_summary(
    deck_id: int,
    db: Session = Depends(get_db)
):
    """Get rating summary (average, count) for a deck"""
    ratings = db.query(DeckRating).filter(DeckRating.deck_id == deck_id).all()
    
    if not ratings:
        return {"average_rating": 0, "total_ratings": 0, "rating_breakdown": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}}
    
    total = len(ratings)
    average = sum(r.rating for r in ratings) / total
    
    breakdown = {i: 0 for i in range(1, 6)}
    for r in ratings:
        breakdown[r.rating] += 1
    
    return {
        "average_rating": round(average, 2),
        "total_ratings": total,
        "rating_breakdown": breakdown
    }


# Study Groups Endpoints
class StudyGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    topic_id: Optional[int] = None
    is_public: bool = True
    max_members: int = 50


class StudyGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    creator_username: str
    topic_name: Optional[str]
    is_public: bool
    member_count: int
    max_members: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class StudyGroupDetailResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    creator_username: str
    topic_name: Optional[str]
    is_public: bool
    members: List[Dict[str, Any]]
    member_count: int
    max_members: int
    created_at: datetime


@router.post("/study-groups", response_model=StudyGroupResponse)
async def create_study_group(
    group_data: StudyGroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new study group"""
    group = StudyGroup(
        creator_id=current_user.id,
        name=group_data.name,
        description=group_data.description,
        topic_id=group_data.topic_id,
        is_public=group_data.is_public,
        max_members=group_data.max_members
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    
    # Add creator as admin member
    member = StudyGroupMember(
        group_id=group.id,
        user_id=current_user.id,
        role="admin"
    )
    db.add(member)
    db.commit()
    
    # Get topic name if exists
    topic_name = None
    if group.topic_id:
        topic = db.query(Topic).filter(Topic.id == group.topic_id).first()
        topic_name = topic.name if topic else None
    
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "creator_username": current_user.username,
        "topic_name": topic_name,
        "is_public": group.is_public,
        "member_count": 1,
        "max_members": group.max_members,
        "created_at": group.created_at
    }


@router.get("/study-groups", response_model=List[StudyGroupResponse])
async def get_study_groups(
    public_only: bool = True,
    topic_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get study groups"""
    query = db.query(StudyGroup, User).join(
        User, StudyGroup.creator_id == User.id
    )
    
    if public_only:
        query = query.filter(StudyGroup.is_public == True)
    
    if topic_id:
        query = query.filter(StudyGroup.topic_id == topic_id)
    
    results = query.order_by(desc(StudyGroup.created_at)).all()
    
    groups = []
    for group, creator in results:
        member_count = db.query(func.count(StudyGroupMember.id)).filter(
            StudyGroupMember.group_id == group.id
        ).scalar()
        
        topic_name = None
        if group.topic_id:
            topic = db.query(Topic).filter(Topic.id == group.topic_id).first()
            topic_name = topic.name if topic else None
        
        groups.append({
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "creator_username": creator.username,
            "topic_name": topic_name,
            "is_public": group.is_public,
            "member_count": member_count or 0,
            "max_members": group.max_members,
            "created_at": group.created_at
        })
    
    return groups


@router.get("/study-groups/{group_id}", response_model=StudyGroupDetailResponse)
async def get_study_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get study group details"""
    group = db.query(StudyGroup, User).join(
        User, StudyGroup.creator_id == User.id
    ).filter(StudyGroup.id == group_id).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Study group not found")
    
    group_obj, creator = group
    
    # Get members
    members = db.query(StudyGroupMember, User).join(
        User, StudyGroupMember.user_id == User.id
    ).filter(StudyGroupMember.group_id == group_id).all()
    
    member_list = [
        {
            "user_id": m.user_id,
            "username": u.username,
            "role": m.role,
            "joined_at": m.joined_at.isoformat()
        }
        for m, u in members
    ]
    
    topic_name = None
    if group_obj.topic_id:
        topic = db.query(Topic).filter(Topic.id == group_obj.topic_id).first()
        topic_name = topic.name if topic else None
    
    return {
        "id": group_obj.id,
        "name": group_obj.name,
        "description": group_obj.description,
        "creator_username": creator.username,
        "topic_name": topic_name,
        "is_public": group_obj.is_public,
        "members": member_list,
        "member_count": len(member_list),
        "max_members": group_obj.max_members,
        "created_at": group_obj.created_at
    }


@router.post("/study-groups/{group_id}/join")
async def join_study_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join a study group"""
    group = db.query(StudyGroup).filter(StudyGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Study group not found")
    
    # Check if already a member
    existing = db.query(StudyGroupMember).filter(
        and_(
            StudyGroupMember.group_id == group_id,
            StudyGroupMember.user_id == current_user.id
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Already a member of this group")
    
    # Check member limit
    member_count = db.query(func.count(StudyGroupMember.id)).filter(
        StudyGroupMember.group_id == group_id
    ).scalar()
    
    if member_count >= group.max_members:
        raise HTTPException(status_code=400, detail="Study group is full")
    
    member = StudyGroupMember(
        group_id=group_id,
        user_id=current_user.id,
        role="member"
    )
    db.add(member)
    db.commit()
    
    return {"message": "Successfully joined study group"}


# Shared Decks Endpoints
class SharedDeckResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    creator_username: str
    topic_name: Optional[str]
    flashcard_count: int
    import_count: int
    average_rating: float
    total_ratings: int
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/shared-decks", response_model=List[SharedDeckResponse])
async def get_shared_decks(
    topic_id: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get public shared decks"""
    query = db.query(SharedDeck, User).join(
        User, SharedDeck.user_id == User.id
    ).filter(SharedDeck.is_public == True)
    
    if topic_id:
        query = query.filter(SharedDeck.topic_id == topic_id)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                SharedDeck.name.like(search_pattern),
                SharedDeck.description.like(search_pattern)
            )
        )
    
    results = query.order_by(desc(SharedDeck.import_count), desc(SharedDeck.created_at)).limit(limit).all()
    
    decks = []
    for deck, creator in results:
        # Get rating summary
        ratings = db.query(DeckRating).filter(DeckRating.deck_id == deck.id).all()
        avg_rating = sum(r.rating for r in ratings) / len(ratings) if ratings else 0
        
        topic_name = None
        if deck.topic_id:
            topic = db.query(Topic).filter(Topic.id == deck.topic_id).first()
            topic_name = topic.name if topic else None
        
        decks.append({
            "id": deck.id,
            "name": deck.name,
            "description": deck.description,
            "creator_username": creator.username,
            "topic_name": topic_name,
            "flashcard_count": deck.flashcard_count,
            "import_count": deck.import_count,
            "average_rating": round(avg_rating, 2),
            "total_ratings": len(ratings),
            "created_at": deck.created_at
        })
    
    return decks


@router.post("/shared-decks/{deck_id}/import")
async def import_shared_deck(
    deck_id: int,
    topic_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import a shared deck"""
    shared_deck = db.query(SharedDeck).filter(SharedDeck.id == deck_id).first()
    if not shared_deck:
        raise HTTPException(status_code=404, detail="Shared deck not found")
    
    if not shared_deck.is_public:
        raise HTTPException(status_code=403, detail="Deck is not public")
    
    # Get flashcards from the original topic
    original_flashcards = db.query(Flashcard).filter(
        Flashcard.topic_id == shared_deck.topic_id
    ).all()
    
    if not original_flashcards:
        raise HTTPException(status_code=404, detail="No flashcards found in shared deck")
    
    # Create new flashcards for the user
    imported_count = 0
    for original_card in original_flashcards:
        new_card = Flashcard(
            user_id=current_user.id,
            topic_id=topic_id,
            question=original_card.question,
            answer=original_card.answer,
            flashcard_type=original_card.flashcard_type,
            difficulty_level=original_card.difficulty_level,
            tags=original_card.tags,
            importance_score=original_card.importance_score,
            mnemonic_device=original_card.mnemonic_device
        )
        db.add(new_card)
        imported_count += 1
    
    # Update import count
    shared_deck.import_count += 1
    db.commit()
    
    return {
        "message": f"Successfully imported {imported_count} flashcards",
        "imported_count": imported_count
    }


# Leaderboard Endpoints
class LeaderboardEntry(BaseModel):
    user_id: int
    username: str
    xp_points: int
    level: int
    rank: int
    avatar_url: Optional[str] = None


@router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(
    period: str = "all_time",  # daily, weekly, monthly, all_time
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get leaderboard"""
    # Calculate date range based on period
    end_date = date.today()
    if period == "daily":
        start_date = end_date
    elif period == "weekly":
        start_date = end_date - timedelta(days=7)
    elif period == "monthly":
        start_date = end_date - timedelta(days=30)
    else:  # all_time
        start_date = None
    
    # Get user profiles
    query = db.query(UserProfile, User).join(
        User, UserProfile.user_id == User.id
    )
    
    if start_date:
        # Filter by activity in period
        active_users = db.query(DailyActivity.user_id).filter(
            DailyActivity.activity_date >= start_date
        ).distinct().subquery()
        query = query.filter(UserProfile.user_id.in_(db.query(active_users.c.user_id)))
    
    # Order by XP
    results = query.order_by(desc(UserProfile.xp_points)).limit(limit).all()
    
    leaderboard = []
    for rank, (profile, user) in enumerate(results, start=1):
        leaderboard.append({
            "user_id": user.id,
            "username": user.username,
            "xp_points": profile.xp_points,
            "level": profile.level,
            "rank": rank,
            "avatar_url": user.avatar_url
        })
    
    return leaderboard
