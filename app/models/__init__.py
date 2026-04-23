"""
Models package - exports all models including media models
This file bridges app/models.py (file) and app/models/ (directory)
"""
import sys
import os
import importlib.util

# Import all models from app/models.py (the file)
# We need to import from the file path to avoid circular import
_current_dir = os.path.dirname(__file__)
_parent_dir = os.path.dirname(_current_dir)
_models_file_path = os.path.join(_parent_dir, 'models.py')

if os.path.exists(_models_file_path):
    spec = importlib.util.spec_from_file_location("app.models_file", _models_file_path)
    models_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models_module)
    
    # Import all classes and enums from models.py
    User = models_module.User
    Topic = models_module.Topic
    StudyMaterial = models_module.StudyMaterial
    Flashcard = models_module.Flashcard
    SpacedRepetition = models_module.SpacedRepetition
    ReviewSession = models_module.ReviewSession
    ReviewResponse = models_module.ReviewResponse
    ReviewIdempotencyKey = models_module.ReviewIdempotencyKey
    PracticeQuestion = models_module.PracticeQuestion
    PracticeExamAttempt = models_module.PracticeExamAttempt
    PracticeExamResponse = models_module.PracticeExamResponse
    ProgressAnalytics = models_module.ProgressAnalytics
    UserProfile = models_module.UserProfile
    Achievement = models_module.Achievement
    UserAchievement = models_module.UserAchievement
    StudySession = models_module.StudySession
    DailyActivity = models_module.DailyActivity
    StudyBuddy = models_module.StudyBuddy
    CollaborativeSession = models_module.CollaborativeSession
    CollaborativeSessionParticipant = models_module.CollaborativeSessionParticipant
    FlashcardComment = models_module.FlashcardComment
    DeckRating = models_module.DeckRating
    StudyGroup = models_module.StudyGroup
    StudyGroupMember = models_module.StudyGroupMember
    SharedDeck = models_module.SharedDeck
    Exam = models_module.Exam
    ExamHistory = models_module.ExamHistory
    QuestionBank = models_module.QuestionBank
    QuestionBankItem = models_module.QuestionBankItem
    UserKnowledgeProfile = models_module.UserKnowledgeProfile
    ConceptMap = models_module.ConceptMap
    AdaptiveLearningPath = models_module.AdaptiveLearningPath
    ImportExportHistory = models_module.ImportExportHistory
    
    # Import enums
    FileType = models_module.FileType
    ProcessingStatus = models_module.ProcessingStatus
    FlashcardType = models_module.FlashcardType
    DifficultyLevel = models_module.DifficultyLevel
    MasteryLevel = models_module.MasteryLevel
else:
    raise ImportError(f"Could not find models.py at {_models_file_path}")

# Import media models from media.py
_media_path = os.path.join(_current_dir, 'media.py')
if os.path.exists(_media_path):
    spec = importlib.util.spec_from_file_location("app.models.media", _media_path)
    media_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(media_module)
    MediaAttachment = media_module.MediaAttachment
    ImageAnnotation = media_module.ImageAnnotation
    InteractiveDiagram = media_module.InteractiveDiagram
else:
    raise ImportError(f"Could not find media.py at {_media_path}")

# Re-export everything
__all__ = [
    # Enums
    'FileType', 'ProcessingStatus', 'FlashcardType', 'DifficultyLevel', 'MasteryLevel',
    # Core models
    'User', 'Topic', 'StudyMaterial', 'Flashcard',
    # Spaced repetition
    'SpacedRepetition', 'ReviewSession', 'ReviewResponse', 'ReviewIdempotencyKey',
    # Practice
    'PracticeQuestion', 'PracticeExamAttempt', 'PracticeExamResponse',
    # Analytics
    'ProgressAnalytics',
    # Gamification
    'UserProfile', 'Achievement', 'UserAchievement', 'StudySession', 'DailyActivity',
    # Social
    'StudyBuddy', 'CollaborativeSession', 'CollaborativeSessionParticipant',
    'FlashcardComment', 'DeckRating', 'StudyGroup', 'StudyGroupMember', 'SharedDeck',
    # Exams
    'Exam', 'ExamHistory', 'QuestionBank', 'QuestionBankItem',
    # AI Features
    'UserKnowledgeProfile', 'ConceptMap', 'AdaptiveLearningPath',
    # Import/Export
    'ImportExportHistory',
    # Media models
    'MediaAttachment', 'ImageAnnotation', 'InteractiveDiagram',
]
