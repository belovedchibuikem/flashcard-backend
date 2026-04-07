"""
Application configuration settings
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend/ and project root (for Vercel api/index.py which chdirs to backend)
_backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(_backend_dir / ".env")
load_dotenv(_backend_dir.parent / ".env")  # project root

logger = logging.getLogger(__name__)


def _is_serverless_ephemeral_filesystem() -> bool:
    """Vercel/AWS Lambda deploy the app under /var/task, which is read-only; only /tmp is writable."""
    return (
        os.getenv("VERCEL") == "1"
        or bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
        or str(os.getenv("AWS_EXECUTION_ENV", "")).startswith("AWS_Lambda")
    )


def _default_upload_dir() -> str:
    if _is_serverless_ephemeral_filesystem():
        base = os.getenv("TMPDIR") or "/tmp"
        return os.path.join(base, "flashcard_uploads")
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")


def _get_jwt_secret() -> str:
    """Read JWT secret from env - check multiple var names for Vercel compatibility."""
    return (
        os.getenv("JWT_SECRET_KEY")
        or os.getenv("JWT_SECRET")
        or "your-secret-key-change-in-production"
    )


def _sync_ai_keys_from_process_environ(s: "Settings") -> None:
    """
    Vercel injects secrets into the process environment at runtime.
    Reinforce AI keys from os.environ so they are never shadowed by .env placeholders.
    """
    oa = (os.getenv("OPENAI_API_KEY") or "").strip()
    if oa:
        s.OPENAI_API_KEY = oa
    gm = (
        os.getenv("GOOGLE_GEMINI_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or ""
    ).strip()
    if gm:
        s.GOOGLE_GEMINI_API_KEY = gm
    an = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if an:
        s.ANTHROPIC_API_KEY = an


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_backend_dir / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )
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
    
    # OpenAI (filled from env / .env via BaseSettings; _sync_ai_keys_from_process_environ reinforces on Vercel)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # Anthropic Claude (for long documents)
    ANTHROPIC_API_KEY: str = ""
    
    # Google Gemini (for fast/cost-efficient tasks)
    GOOGLE_GEMINI_API_KEY: str = ""
    GOOGLE_GEMINI_MODEL: str = "gemini-2.0-flash"
    
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
    
    # JWT - long-lived tokens so users stay logged in for days/months
    JWT_SECRET_KEY: str = _get_jwt_secret()
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    # 90 days default; set JWT_EXPIRATION_DAYS or JWT_EXPIRATION_HOURS (legacy) to override
    JWT_EXPIRATION_DAYS: int = int(os.getenv("JWT_EXPIRATION_DAYS", "90"))
    
    # CORS (exact origins; Flutter web dev uses random ports — see allow_origin_regex in main.py)
    CORS_ORIGINS: List[str] = [
        x.strip()
        for x in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:8080,http://localhost:8000",
        ).split(",")
        if x.strip()
    ]
    
    # Upload settings
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    # On Vercel/Lambda, default to /tmp; override with UPLOAD_DIR for VPS/Docker. Docs: filesystem is ephemeral.
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR") or _default_upload_dir()


settings = Settings()
_sync_ai_keys_from_process_environ(settings)

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

# Validate JWT_SECRET_KEY on Vercel - must be set explicitly
_IS_VERCEL = os.getenv("VERCEL") == "1"
_DEFAULT_JWT = "your-secret-key-change-in-production"
if _IS_VERCEL and (not settings.JWT_SECRET_KEY or settings.JWT_SECRET_KEY == _DEFAULT_JWT):
    logger.critical(
        "JWT_SECRET_KEY is not set or is default on Vercel. "
        "Auth will fail: set JWT_SECRET_KEY in Vercel Dashboard → Settings → Environment Variables, "
        "then redeploy. Example: openssl rand -hex 32"
    )


