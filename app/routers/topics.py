"""
Topics router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, Topic
from app.schemas import TopicCreate, TopicResponse
from app.routers.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
async def create_topic(
    topic_data: TopicCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new topic/subject"""
    topic = Topic(
        user_id=current_user.id,
        name=topic_data.name,
        description=topic_data.description,
        color_code=topic_data.color_code
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


@router.get("/", response_model=List[TopicResponse])
async def get_topics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all topics for current user"""
    topics = db.query(Topic).filter(Topic.user_id == current_user.id).all()
    return topics


@router.get("/{topic_id}", response_model=TopicResponse)
async def get_topic(
    topic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific topic"""
    topic = db.query(Topic).filter(
        Topic.id == topic_id,
        Topic.user_id == current_user.id
    ).first()
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    return topic


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(
    topic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete topic"""
    topic = db.query(Topic).filter(
        Topic.id == topic_id,
        Topic.user_id == current_user.id
    ).first()
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    db.delete(topic)
    db.commit()
    return None


