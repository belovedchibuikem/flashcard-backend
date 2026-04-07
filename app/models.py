"""
SQLAlchemy database models
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum, DECIMAL, JSON, Date, BIGINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base, IS_MYSQL
import enum

# Note: Media models (MediaAttachment, ImageAnnotation, InteractiveDiagram) are defined in app/models/media.py
# They are imported directly where needed (e.g., in routers/media.py) to avoid import conflicts
# between app/models.py (file) and app/models/ (directory)


class FileType(str, enum.Enum):
    PDF = "pdf"
    IMAGE = "image"
    DOCUMENT = "document"
    HANDWRITTEN = "handwritten"


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FlashcardType(str, enum.Enum):
    DEFINITION = "definition"
    CONCEPT = "concept"
    PROBLEM_SOLVING = "problem_solving"
    TRUE_FALSE = "true_false"
    MCQ = "mcq"


class DifficultyLevel(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class MasteryLevel(str, enum.Enum):
    LEARNING = "learning"
    REVIEWING = "reviewing"
    MASTERED = "mastered"


def _enum_type(enum_class):
    """PostgreSQL ENUM columns expect string values (e.g. 'pdf'); SQLAlchemy otherwise may send names ('PDF')."""
    return Enum(enum_class, values_callable=lambda obj: [m.value for m in obj])


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    avatar_url = Column(String(500))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Topic(Base):
    __tablename__ = "topics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    color_code = Column(String(7))
    created_at = Column(DateTime, server_default=func.now())


class StudyMaterial(Base):
    __tablename__ = "study_materials"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    file_type = Column(_enum_type(FileType), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_size = Column(BIGINT)
    original_filename = Column(String(255))
    extracted_text = Column(Text)
    ocr_processed = Column(Boolean, default=False)
    processing_status = Column(_enum_type(ProcessingStatus), default=ProcessingStatus.PENDING)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Flashcard(Base):
    __tablename__ = "flashcards"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    study_material_id = Column(Integer, ForeignKey("study_materials.id"), nullable=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    flashcard_type = Column(_enum_type(FlashcardType), default=FlashcardType.CONCEPT)
    difficulty_level = Column(_enum_type(DifficultyLevel), default=DifficultyLevel.MEDIUM)
    visual_aid_url = Column(String(500))
    mnemonic_device = Column(Text)
    tags = Column(JSON)
    importance_score = Column(Integer, default=5)
    # Rich Media Support
    video_url = Column(String(500))  # YouTube or other video URLs
    audio_url = Column(String(500))  # Audio file URL
    latex_content = Column(Text)  # LaTeX/math formulas
    code_content = Column(Text)  # Code snippets
    code_language = Column(String(50))  # Programming language for syntax highlighting
    diagram_data = Column(JSON)  # Interactive diagram data
    annotated_image_url = Column(String(500))  # Image with annotations
    model_3d_url = Column(String(500))  # 3D model file URL
    model_3d_format = Column(String(20))  # glb, gltf, obj, etc.
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SpacedRepetition(Base):
    __tablename__ = "spaced_repetition"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    flashcard_id = Column(Integer, ForeignKey("flashcards.id"), nullable=False)
    ease_factor = Column(DECIMAL(5, 2), default=2.5)
    interval_days = Column(Integer, default=1)
    repetitions = Column(Integer, default=0)
    last_reviewed_at = Column(DateTime, nullable=True)
    next_review_at = Column(DateTime, nullable=True)
    mastery_level = Column(_enum_type(MasteryLevel), default=MasteryLevel.LEARNING)
    consecutive_correct = Column(Integer, default=0)
    consecutive_incorrect = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ReviewSession(Base):
    __tablename__ = "review_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_type = Column(String(50), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    flashcards_reviewed = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    incorrect_count = Column(Integer, default=0)
    time_spent_seconds = Column(Integer, default=0)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)


class ReviewResponse(Base):
    __tablename__ = "review_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    review_session_id = Column(Integer, ForeignKey("review_sessions.id"), nullable=False)
    flashcard_id = Column(Integer, ForeignKey("flashcards.id"), nullable=False)
    user_response = Column(Text)
    is_correct = Column(Boolean, nullable=False)
    response_time_seconds = Column(Integer)
    confidence_level = Column(String(20))
    reviewed_at = Column(DateTime, server_default=func.now())


class PracticeQuestion(Base):
    __tablename__ = "practice_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    study_material_id = Column(Integer, ForeignKey("study_materials.id"), nullable=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)
    correct_answer = Column(Text, nullable=False)
    options = Column(JSON)
    explanation = Column(Text)
    difficulty_level = Column(_enum_type(DifficultyLevel), default=DifficultyLevel.MEDIUM)
    predicted_exam_relevance = Column(DECIMAL(3, 2), default=0.5)
    created_at = Column(DateTime, server_default=func.now())


class PracticeExamAttempt(Base):
    __tablename__ = "practice_exam_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    exam_type = Column(String(20), default="untimed")
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, default=0)
    time_limit_minutes = Column(Integer)
    time_spent_seconds = Column(Integer)
    score_percentage = Column(DECIMAL(5, 2))
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)


class PracticeExamResponse(Base):
    __tablename__ = "practice_exam_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    exam_attempt_id = Column(Integer, ForeignKey("practice_exam_attempts.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("practice_questions.id"), nullable=False)
    user_answer = Column(Text)
    is_correct = Column(Boolean, nullable=False)
    points_earned = Column(DECIMAL(5, 2), default=0)
    answered_at = Column(DateTime, server_default=func.now())


class ProgressAnalytics(Base):
    __tablename__ = "progress_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    date = Column(Date, nullable=False)
    flashcards_studied = Column(Integer, default=0)
    flashcards_mastered = Column(Integer, default=0)
    practice_questions_answered = Column(Integer, default=0)
    practice_questions_correct = Column(Integer, default=0)
    study_time_minutes = Column(Integer, default=0)
    mastery_percentage = Column(DECIMAL(5, 2), default=0)
    exam_readiness_score = Column(DECIMAL(5, 2), default=0)
    created_at = Column(DateTime, server_default=func.now())


# Gamification Models
class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    xp_points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_study_date = Column(Date, nullable=True)
    total_study_time_minutes = Column(Integer, default=0)
    total_flashcards_reviewed = Column(Integer, default=0)
    total_practice_questions = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Achievement(Base):
    __tablename__ = "achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    icon_name = Column(String(100))
    xp_reward = Column(Integer, default=0)
    category = Column(String(50))  # study, streak, mastery, social, etc.
    requirement_value = Column(Integer)  # e.g., 100 flashcards reviewed
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    unlocked_at = Column(DateTime, server_default=func.now())
    progress = Column(Integer, default=0)  # Progress towards achievement
    
    achievement = relationship("Achievement")


class StudySession(Base):
    __tablename__ = "study_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_type = Column(String(50), nullable=False)  # normal, speed_review, focus_mode, etc.
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    flashcards_reviewed = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    incorrect_count = Column(Integer, default=0)
    time_spent_seconds = Column(Integer, default=0)
    xp_earned = Column(Integer, default=0)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    is_focus_mode = Column(Boolean, default=False)
    pomodoro_duration_minutes = Column(Integer, nullable=True)


class DailyActivity(Base):
    __tablename__ = "daily_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_date = Column(Date, nullable=False, index=True)
    flashcards_studied = Column(Integer, default=0)
    study_time_minutes = Column(Integer, default=0)
    xp_earned = Column(Integer, default=0)
    achievements_unlocked = Column(Integer, default=0)
    streak_maintained = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # MySQL-specific table args (ignored by PostgreSQL)
    __table_args__ = ({"mysql_engine": "InnoDB"},) if IS_MYSQL else ()


# Social Features Models
class StudyBuddy(Base):
    __tablename__ = "study_buddies"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    buddy_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")  # pending, accepted, blocked
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        {"mysql_engine": "InnoDB"},
    )


class CollaborativeSession(Base):
    __tablename__ = "collaborative_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    max_participants = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)
    started_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class CollaborativeSessionParticipant(Base):
    __tablename__ = "collaborative_session_participants"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("collaborative_sessions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, server_default=func.now())
    left_at = Column(DateTime, nullable=True)
    flashcards_reviewed = Column(Integer, default=0)
    
    session = relationship("CollaborativeSession")


class FlashcardComment(Base):
    __tablename__ = "flashcard_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    flashcard_id = Column(Integer, ForeignKey("flashcards.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    comment_text = Column(Text, nullable=False)
    parent_comment_id = Column(Integer, ForeignKey("flashcard_comments.id"), nullable=True)  # For replies
    is_edited = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    flashcard = relationship("Flashcard")
    user = relationship("User")
    parent_comment = relationship("FlashcardComment", remote_side=[id])


class DeckRating(Base):
    __tablename__ = "deck_ratings"
    
    id = Column(Integer, primary_key=True, index=True)
    deck_id = Column(Integer, nullable=False)  # Reference to shared deck or topic
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    review_text = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class StudyGroup(Base):
    __tablename__ = "study_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    is_public = Column(Boolean, default=True)
    max_members = Column(Integer, default=50)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        {"mysql_engine": "InnoDB"},
    )


class StudyGroupMember(Base):
    __tablename__ = "study_group_members"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("study_groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), default="member")  # member, admin
    joined_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        {"mysql_engine": "InnoDB"},
    )


class SharedDeck(Base):
    __tablename__ = "shared_decks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_public = Column(Boolean, default=True)
    flashcard_count = Column(Integer, default=0)
    import_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        {"mysql_engine": "InnoDB"},
    )


# Exam Features Models
class Exam(Base):
    __tablename__ = "exams"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    exam_date = Column(DateTime, nullable=False)
    subject = Column(String(255))
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        {"mysql_engine": "InnoDB"},
    )


class ExamHistory(Base):
    __tablename__ = "exam_history"
    
    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, nullable=False)  # Reference to exam
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    attempt_number = Column(Integer, default=1)
    score_percentage = Column(DECIMAL(5, 2))
    total_questions = Column(Integer)
    correct_answers = Column(Integer)
    time_spent_minutes = Column(Integer)
    weak_topics = Column(JSON)  # List of topics that need improvement
    completed_at = Column(DateTime, server_default=func.now())


class QuestionBank(Base):
    __tablename__ = "question_banks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exam_id = Column(Integer, nullable=True)  # Optional link to specific exam
    name = Column(String(255), nullable=False)
    description = Column(Text)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    question_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class QuestionBankItem(Base):
    __tablename__ = "question_bank_items"
    
    id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(Integer, ForeignKey("question_banks.id"), nullable=False)
    practice_question_id = Column(Integer, ForeignKey("practice_questions.id"), nullable=False)
    added_at = Column(DateTime, server_default=func.now())
    
    bank = relationship("QuestionBank")
    practice_question = relationship("PracticeQuestion")


# AI Features Models
class UserKnowledgeProfile(Base):
    __tablename__ = "user_knowledge_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    difficulty_level = Column(String(20), default="medium")  # easy, medium, hard
    mastery_score = Column(DECIMAL(5, 2), default=0)  # 0-100
    weak_areas = Column(JSON)  # List of concepts user struggles with
    strong_areas = Column(JSON)  # List of concepts user excels at
    mistake_patterns = Column(JSON)  # Common mistakes identified
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        {"mysql_engine": "InnoDB"},
    )


class ConceptMap(Base):
    __tablename__ = "concept_maps"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    title = Column(String(255), nullable=False)
    map_data = Column(JSON)  # Graph structure with nodes and edges
    generated_at = Column(DateTime, server_default=func.now())


class AdaptiveLearningPath(Base):
    __tablename__ = "adaptive_learning_paths"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    path_sequence = Column(JSON)  # Ordered list of flashcard IDs or concepts
    current_position = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# Import/Export Models
class ImportExportHistory(Base):
    __tablename__ = "import_export_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operation_type = Column(String(20), nullable=False)  # import, export
    source_format = Column(String(20))  # anki, quizlet, csv, pdf
    target_format = Column(String(20))  # anki, quizlet, csv, pdf
    item_count = Column(Integer, default=0)
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    file_url = Column(String(500))
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)

