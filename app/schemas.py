"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    avatar_url: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Partial profile update. Password change requires current_password when new_password is set."""

    full_name: Optional[str] = None
    username: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Topic Schemas
class TopicBase(BaseModel):
    name: str
    description: Optional[str] = None
    color_code: Optional[str] = None


class TopicCreate(TopicBase):
    pass


class TopicResponse(TopicBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Study Material Schemas
class StudyMaterialBase(BaseModel):
    title: str
    file_type: str


class StudyMaterialCreate(StudyMaterialBase):
    pass


class StudyMaterialResponse(StudyMaterialBase):
    id: int
    user_id: int
    file_url: str
    file_size: Optional[int] = None
    original_filename: Optional[str] = None
    processing_status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Flashcard Schemas
class FlashcardBase(BaseModel):
    question: str
    answer: str
    flashcard_type: Optional[str] = "concept"
    difficulty_level: Optional[str] = "medium"
    tags: Optional[List[str]] = None
    importance_score: Optional[int] = 5


class FlashcardCreate(FlashcardBase):
    topic_id: Optional[int] = None
    study_material_id: Optional[int] = None


class FlashcardResponse(FlashcardBase):
    id: int
    user_id: int
    topic_id: Optional[int] = None
    study_material_id: Optional[int] = None
    visual_aid_url: Optional[str] = None
    mnemonic_device: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class FlashcardListItem(FlashcardResponse):
    """Flashcard row with source labels for deck/course browsing in the client."""

    study_material_title: Optional[str] = None
    topic_name: Optional[str] = None


class FlashcardMaterialDeckSummary(BaseModel):
    id: int
    title: str
    file_type: str
    flashcard_count: int


class FlashcardTopicDeckSummary(BaseModel):
    id: int
    name: str
    color_code: Optional[str] = None
    flashcard_count: int


class FlashcardDecksSummaryResponse(BaseModel):
    """Grouped counts so users can pick a course (material) or topic to study."""

    by_material: List[FlashcardMaterialDeckSummary]
    by_topic: List[FlashcardTopicDeckSummary]
    uncategorized_count: int


# Spaced Repetition Schemas
class SpacedRepetitionResponse(BaseModel):
    id: int
    flashcard_id: int
    ease_factor: Decimal
    interval_days: int
    repetitions: int
    next_review_at: Optional[datetime]
    mastery_level: str
    consecutive_correct: int
    consecutive_incorrect: int
    
    class Config:
        from_attributes = True


# Review Session Schemas
class ReviewResponseCreate(BaseModel):
    flashcard_id: int
    is_correct: bool
    confidence_level: Optional[str] = "medium"
    response_time_seconds: Optional[int] = None


class ReviewSessionCreate(BaseModel):
    session_type: str
    topic_id: Optional[int] = None
    responses: List[ReviewResponseCreate]


class ReviewSessionResponse(BaseModel):
    id: int
    session_type: str
    flashcards_reviewed: int
    correct_count: int
    incorrect_count: int
    time_spent_seconds: int
    started_at: datetime
    
    class Config:
        from_attributes = True


# Practice Question Schemas
class PracticeQuestionResponse(BaseModel):
    id: int
    question_text: str
    question_type: str
    options: Optional[List[Any]] = None  # MCQ options as list of strings
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    difficulty_level: str
    predicted_exam_relevance: Decimal
    study_material_id: Optional[int] = None
    study_material_title: Optional[str] = None
    
    class Config:
        from_attributes = True


class PracticeMaterialDeckSummary(BaseModel):
    id: int
    title: str
    file_type: str
    question_count: int


class PracticeTopicDeckSummary(BaseModel):
    id: int
    name: str
    color_code: Optional[str] = None
    question_count: int


class PracticeDecksSummaryResponse(BaseModel):
    """Course/deck picker for practice exams (counts per uploaded material)."""

    by_material: List[PracticeMaterialDeckSummary]
    by_topic: List[PracticeTopicDeckSummary]
    uncategorized_count: int


class PracticeExamResponse(BaseModel):
    question_id: int
    user_answer: str
    is_correct: bool


class PracticeExamCreate(BaseModel):
    topic_id: Optional[int] = None
    study_material_id: Optional[int] = None
    exam_label: Optional[str] = None
    exam_type: Optional[str] = "untimed"
    time_limit_minutes: Optional[int] = None
    responses: List[PracticeExamResponse]


# Analytics Schemas
class ProgressAnalyticsResponse(BaseModel):
    date: date
    flashcards_studied: int
    flashcards_mastered: int
    practice_questions_answered: int
    practice_questions_correct: int
    study_time_minutes: int
    mastery_percentage: Decimal
    exam_readiness_score: Decimal
    
    class Config:
        from_attributes = True


class ExamReadinessResponse(BaseModel):
    overall_readiness: Decimal
    topic_readiness: Dict[str, Decimal]
    weak_areas: List[str]
    recommended_study_time: int


# Gamification Schemas
class UserProfileResponse(BaseModel):
    user_id: int
    xp_points: int
    level: int
    current_streak: int
    longest_streak: int
    total_study_time_minutes: int
    total_flashcards_reviewed: int
    total_practice_questions: int
    xp_to_next_level: int
    level_progress_percentage: float
    
    class Config:
        from_attributes = True


class AchievementResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str]
    icon_name: Optional[str]
    xp_reward: int
    category: Optional[str]
    requirement_value: int
    unlocked_at: Optional[datetime] = None
    progress: int = 0
    is_unlocked: bool = False
    
    class Config:
        from_attributes = True


class StudySessionCreate(BaseModel):
    session_type: str  # normal, speed_review, focus_mode
    topic_id: Optional[int] = None
    is_focus_mode: bool = False
    pomodoro_duration_minutes: Optional[int] = None


class StudySessionResponse(BaseModel):
    id: int
    session_type: str
    flashcards_reviewed: int
    correct_count: int
    incorrect_count: int
    time_spent_seconds: int
    xp_earned: int
    started_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class StudySessionComplete(BaseModel):
    flashcards_reviewed: int
    correct_count: int
    incorrect_count: int
    time_spent_seconds: int


class DailyActivityResponse(BaseModel):
    activity_date: date
    flashcards_studied: int
    study_time_minutes: int
    xp_earned: int
    achievements_unlocked: int
    streak_maintained: bool
    
    class Config:
        from_attributes = True


class HeatMapDataResponse(BaseModel):
    date: date
    intensity: int  # 0-4 based on study activity
    study_time_minutes: int
    flashcards_studied: int

