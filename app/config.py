"""
Application configuration settings
"""

from pydantic_settings import BaseSettings
from typing import List
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Database
    # Support both standard DATABASE_URL and Vercel Neon integration variables
    # Priority: Check Neon integration variables FIRST (they're more reliable)
    # Vercel Neon native integration uses DATABASE_DB_URL__DATABASE_URL
    DATABASE_URL: str = (
        os.getenv("DATABASE_DB_URL__DATABASE_URL") or  # Vercel Neon integration (highest priority)
        os.getenv("POSTGRES_URL") or  # Vercel Postgres
        os.getenv("DATABASE_URL") or  # Standard variable (fallback)
        ""  # Empty default - must be set via environment variable
    )
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")  # or "gpt-4o"
    
    # Anthropic Claude (for long documents)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Google Gemini (for fast/cost-efficient tasks)
    GOOGLE_GEMINI_API_KEY: str = os.getenv("GOOGLE_GEMINI_API_KEY", "")
    
    # Google Cloud Vision
    GOOGLE_CLOUD_VISION_API_KEY: str = os.getenv("GOOGLE_CLOUD_VISION_API_KEY", "")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    # Google Document AI (requires processor setup in GCP Console)
    GOOGLE_DOCUMENT_AI_PROCESSOR_NAME: str = os.getenv("GOOGLE_DOCUMENT_AI_PROCESSOR_NAME", "")
    
    # Azure Computer Vision (for handwritten OCR)
    AZURE_VISION_KEY: str = os.getenv("AZURE_VISION_KEY", "")
    AZURE_VISION_ENDPOINT: str = os.getenv("AZURE_VISION_ENDPOINT", "")
    
    # File Storage
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "local")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_S3_BUCKET_NAME: str = os.getenv("AWS_S3_BUCKET_NAME", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")
    
    # Server
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    
    # CORS
    CORS_ORIGINS: List[str] = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:8080,http://localhost:8000"
    ).split(",")
    
    # Upload settings
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    
    class Config:
        env_file = ".env"


settings = Settings()

# Validate DATABASE_URL and warn if it looks invalid
if settings.DATABASE_URL:
    # Check for common invalid patterns
    invalid_patterns = ["@@@", "example", "localhost", "placeholder", "your-"]
    if any(pattern in settings.DATABASE_URL.lower() for pattern in invalid_patterns):
        logger.warning(
            f"DATABASE_URL appears to contain invalid/placeholder values. "
            f"Please check your Vercel environment variables. "
            f"Using Neon integration? Ensure DATABASE_DB_URL__DATABASE_URL is set correctly."
        )


