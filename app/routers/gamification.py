"""
Gamification router for achievements, XP, streaks, and study sessions
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date, timedelta
from typing import List, Optional

from app.database import get_db
from app.models import (
    User, UserProfile, Achievement, UserAchievement, 
    StudySession, DailyActivity, ReviewSession, Flashcard
)
from app.schemas import (
    UserProfileResponse, AchievementResponse, StudySessionCreate,
    StudySessionResponse, StudySessionComplete, DailyActivityResponse,
    HeatMapDataResponse
)
from app.routers.auth import get_current_user

router = APIRouter()


def get_or_create_user_profile(user_id: int, db: Session) -> UserProfile:
    """Get or create user profile"""
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def calculate_level(xp: int) -> tuple[int, int, float]:
    """Calculate level from XP. Returns (level, xp_to_next_level, progress_percentage)"""
    # XP formula: level * 100 * (level + 1) / 2
    # Level 1: 0-199 XP, Level 2: 200-499 XP, Level 3: 500-999 XP, etc.
    level = 1
    xp_for_current_level = 0
    xp_for_next_level = 200
    
    while xp >= xp_for_next_level:
        xp_for_current_level = xp_for_next_level
        level += 1
        xp_for_next_level = level * 100 * (level + 1) // 2
    
    xp_to_next_level = xp_for_next_level - xp
    progress = ((xp - xp_for_current_level) / (xp_for_next_level - xp_for_current_level) * 100) if xp_for_current_level > 0 else (xp / xp_for_next_level * 100)
    
    return level, xp_to_next_level, min(progress, 100.0)


def award_xp(user_id: int, xp_amount: int, db: Session) -> UserProfile:
    """Award XP to user and update level"""
    profile = get_or_create_user_profile(user_id, db)
    profile.xp_points += xp_amount
    
    # Recalculate level
    new_level, _, _ = calculate_level(profile.xp_points)
    if new_level > profile.level:
        profile.level = new_level
    
    db.commit()
    db.refresh(profile)
    return profile


def update_streak(user_id: int, db: Session) -> UserProfile:
    """Update study streak"""
    profile = get_or_create_user_profile(user_id, db)
    today = date.today()
    
    if profile.last_study_date:
        days_diff = (today - profile.last_study_date).days
        
        if days_diff == 0:
            # Already studied today, no change
            pass
        elif days_diff == 1:
            # Consecutive day, increment streak
            profile.current_streak += 1
        else:
            # Streak broken, reset to 1
            profile.current_streak = 1
    else:
        # First study session
        profile.current_streak = 1
    
    profile.last_study_date = today
    
    if profile.current_streak > profile.longest_streak:
        profile.longest_streak = profile.current_streak
    
    db.commit()
    db.refresh(profile)
    return profile


def check_achievements(user_id: int, db: Session):
    """Check and unlock achievements"""
    profile = get_or_create_user_profile(user_id, db)
    achievements = db.query(Achievement).filter(Achievement.is_active == True).all()
    
    unlocked_achievements = []
    
    for achievement in achievements:
        user_achievement = db.query(UserAchievement).filter(
            and_(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement.id
            )
        ).first()
        
        if user_achievement and user_achievement.progress >= achievement.requirement_value:
            # Already unlocked
            continue
        
        # Check achievement requirements
        progress = 0
        unlocked = False
        
        if achievement.code == "first_flashcard":
            progress = profile.total_flashcards_reviewed
            unlocked = progress >= 1
        elif achievement.code == "flashcard_master_10":
            progress = profile.total_flashcards_reviewed
            unlocked = progress >= 10
        elif achievement.code == "flashcard_master_100":
            progress = profile.total_flashcards_reviewed
            unlocked = progress >= 100
        elif achievement.code == "streak_7":
            progress = profile.current_streak
            unlocked = progress >= 7
        elif achievement.code == "streak_30":
            progress = profile.current_streak
            unlocked = progress >= 30
        elif achievement.code == "level_5":
            progress = profile.level
            unlocked = progress >= 5
        elif achievement.code == "level_10":
            progress = profile.level
            unlocked = progress >= 10
        elif achievement.code == "study_time_10h":
            progress = profile.total_study_time_minutes
            unlocked = progress >= 600  # 10 hours
        elif achievement.code == "perfect_session":
            # Check last session for 100% accuracy
            last_session = db.query(StudySession).filter(
                StudySession.user_id == user_id
            ).order_by(StudySession.completed_at.desc()).first()
            if last_session and last_session.flashcards_reviewed > 0:
                accuracy = last_session.correct_count / last_session.flashcards_reviewed
                unlocked = accuracy == 1.0
                progress = int(accuracy * 100)
        
        if unlocked and not user_achievement:
            # Unlock achievement
            user_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=achievement.id,
                progress=achievement.requirement_value
            )
            db.add(user_achievement)
            
            # Award XP
            if achievement.xp_reward > 0:
                award_xp(user_id, achievement.xp_reward, db)
            
            unlocked_achievements.append(achievement)
        elif user_achievement:
            # Update progress
            user_achievement.progress = progress
            db.commit()
    
    if unlocked_achievements:
        db.commit()
    
    return unlocked_achievements


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user gamification profile"""
    profile = get_or_create_user_profile(current_user.id, db)
    _, xp_to_next_level, progress = calculate_level(profile.xp_points)
    
    return {
        "user_id": profile.user_id,
        "xp_points": profile.xp_points,
        "level": profile.level,
        "current_streak": profile.current_streak,
        "longest_streak": profile.longest_streak,
        "total_study_time_minutes": profile.total_study_time_minutes,
        "total_flashcards_reviewed": profile.total_flashcards_reviewed,
        "total_practice_questions": profile.total_practice_questions,
        "xp_to_next_level": xp_to_next_level,
        "level_progress_percentage": progress
    }


@router.get("/achievements", response_model=List[AchievementResponse])
async def get_achievements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all achievements with user's progress"""
    achievements = db.query(Achievement).filter(Achievement.is_active == True).all()
    user_achievements = {
        ua.achievement_id: ua
        for ua in db.query(UserAchievement).filter(
            UserAchievement.user_id == current_user.id
        ).all()
    }
    
    result = []
    for achievement in achievements:
        user_achievement = user_achievements.get(achievement.id)
        result.append({
            "id": achievement.id,
            "code": achievement.code,
            "name": achievement.name,
            "description": achievement.description,
            "icon_name": achievement.icon_name,
            "xp_reward": achievement.xp_reward,
            "category": achievement.category,
            "requirement_value": achievement.requirement_value,
            "unlocked_at": user_achievement.unlocked_at if user_achievement else None,
            "progress": user_achievement.progress if user_achievement else 0,
            "is_unlocked": user_achievement is not None
        })
    
    return result


@router.post("/session/start", response_model=StudySessionResponse)
async def start_study_session(
    session_data: StudySessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a new study session"""
    session = StudySession(
        user_id=current_user.id,
        session_type=session_data.session_type,
        topic_id=session_data.topic_id,
        is_focus_mode=session_data.is_focus_mode,
        pomodoro_duration_minutes=session_data.pomodoro_duration_minutes
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.put("/session/{session_id}/complete", response_model=StudySessionResponse)
async def complete_study_session(
    session_id: int,
    session_data: StudySessionComplete,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Complete a study session and award XP"""
    session = db.query(StudySession).filter(
        and_(
            StudySession.id == session_id,
            StudySession.user_id == current_user.id
        )
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.completed_at:
        raise HTTPException(status_code=400, detail="Session already completed")
    
    # Update session
    session.flashcards_reviewed = session_data.flashcards_reviewed
    session.correct_count = session_data.correct_count
    session.incorrect_count = session_data.incorrect_count
    session.time_spent_seconds = session_data.time_spent_seconds
    session.completed_at = datetime.utcnow()
    
    # Calculate XP (10 XP per flashcard, bonus for accuracy)
    base_xp = session_data.flashcards_reviewed * 10
    accuracy = session_data.correct_count / session_data.flashcards_reviewed if session_data.flashcards_reviewed > 0 else 0
    accuracy_bonus = int(base_xp * accuracy * 0.5)  # Up to 50% bonus
    time_bonus = min(session_data.time_spent_seconds // 60, 50)  # 1 XP per minute, max 50
    
    total_xp = base_xp + accuracy_bonus + time_bonus
    session.xp_earned = total_xp
    
    # Update user profile
    profile = get_or_create_user_profile(current_user.id, db)
    profile.total_flashcards_reviewed += session_data.flashcards_reviewed
    profile.total_study_time_minutes += session_data.time_spent_seconds // 60
    
    # Award XP and update streak
    award_xp(current_user.id, total_xp, db)
    update_streak(current_user.id, db)
    
    # Update daily activity
    today = date.today()
    daily_activity = db.query(DailyActivity).filter(
        and_(
            DailyActivity.user_id == current_user.id,
            DailyActivity.activity_date == today
        )
    ).first()
    
    if not daily_activity:
        daily_activity = DailyActivity(
            user_id=current_user.id,
            activity_date=today
        )
        db.add(daily_activity)
    
    daily_activity.flashcards_studied += session_data.flashcards_reviewed
    daily_activity.study_time_minutes += session_data.time_spent_seconds // 60
    daily_activity.xp_earned += total_xp
    daily_activity.streak_maintained = True
    
    db.commit()
    db.refresh(session)
    
    # Check for achievements
    check_achievements(current_user.id, db)
    
    return session


@router.get("/daily-activity", response_model=List[DailyActivityResponse])
async def get_daily_activity(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get daily activity for heat map"""
    start_date = date.today() - timedelta(days=days)
    activities = db.query(DailyActivity).filter(
        and_(
            DailyActivity.user_id == current_user.id,
            DailyActivity.activity_date >= start_date
        )
    ).order_by(DailyActivity.activity_date).all()
    
    return activities


@router.get("/heatmap", response_model=List[HeatMapDataResponse])
async def get_heatmap_data(
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get heat map data for calendar visualization"""
    if year is None:
        year = date.today().year
    
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    activities = db.query(DailyActivity).filter(
        and_(
            DailyActivity.user_id == current_user.id,
            DailyActivity.activity_date >= start_date,
            DailyActivity.activity_date <= end_date
        )
    ).all()
    
    # Create a map for quick lookup
    activity_map = {a.activity_date: a for a in activities}
    
    # Generate all dates in the year
    result = []
    current_date = start_date
    while current_date <= end_date:
        activity = activity_map.get(current_date)
        
        # Calculate intensity (0-4) based on study time
        if activity:
            intensity = min(4, activity.study_time_minutes // 30)  # 0-4 based on 30min intervals
            result.append({
                "date": current_date,
                "intensity": intensity,
                "study_time_minutes": activity.study_time_minutes,
                "flashcards_studied": activity.flashcards_studied
            })
        else:
            result.append({
                "date": current_date,
                "intensity": 0,
                "study_time_minutes": 0,
                "flashcards_studied": 0
            })
        
        current_date += timedelta(days=1)
    
    return result


@router.post("/initialize-achievements")
async def initialize_achievements(db: Session = Depends(get_db)):
    """Initialize default achievements (admin only - for setup)"""
    achievements = [
        Achievement(code="first_flashcard", name="First Steps", description="Review your first flashcard", icon_name="star", xp_reward=50, category="study", requirement_value=1),
        Achievement(code="flashcard_master_10", name="Getting Started", description="Review 10 flashcards", icon_name="trophy", xp_reward=100, category="study", requirement_value=10),
        Achievement(code="flashcard_master_100", name="Century Club", description="Review 100 flashcards", icon_name="medal", xp_reward=500, category="study", requirement_value=100),
        Achievement(code="streak_7", name="Week Warrior", description="Maintain a 7-day streak", icon_name="flame", xp_reward=200, category="streak", requirement_value=7),
        Achievement(code="streak_30", name="Monthly Master", description="Maintain a 30-day streak", icon_name="fire", xp_reward=1000, category="streak", requirement_value=30),
        Achievement(code="level_5", name="Rising Star", description="Reach level 5", icon_name="star", xp_reward=300, category="level", requirement_value=5),
        Achievement(code="level_10", name="Expert Learner", description="Reach level 10", icon_name="crown", xp_reward=1000, category="level", requirement_value=10),
        Achievement(code="study_time_10h", name="Dedicated Scholar", description="Study for 10 hours total", icon_name="clock", xp_reward=500, category="time", requirement_value=600),
        Achievement(code="perfect_session", name="Perfect Score", description="Get 100% accuracy in a session", icon_name="check_circle", xp_reward=150, category="accuracy", requirement_value=100),
    ]
    
    for achievement_data in achievements:
        existing = db.query(Achievement).filter(Achievement.code == achievement_data.code).first()
        if not existing:
            db.add(achievement_data)
    
    db.commit()
    return {"message": "Achievements initialized", "count": len(achievements)}
