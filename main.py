"""
AI-Powered Smart Flashcard Generator - Backend API
Main FastAPI application entry point
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import uvicorn
from dotenv import load_dotenv
import os
import logging

from app.routers import auth, flashcards, materials, practice, analytics, topics, gamification, social, exams, import_export, ai_features, media
from app.database import engine, Base
from app.config import settings
try:
    from app.middleware.error_handler import (
        validation_exception_handler,
        database_exception_handler,
        general_exception_handler,
    )
except ImportError:
    # Fallback if middleware not available
    async def validation_exception_handler(request, exc):
        from fastapi.responses import JSONResponse
        from fastapi import status
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)}
        )
    
    async def database_exception_handler(request, exc):
        from fastapi.responses import JSONResponse
        from fastapi import status
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Database error"}
        )
    
    async def general_exception_handler(request, exc):
        from fastapi.responses import JSONResponse
        from fastapi import status
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create database tables (only if database is available)
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
except Exception as e:
    logger.warning(f"Could not create database tables: {e}. This is OK if database is not available yet.")

# Initialize FastAPI app
app = FastAPI(
    title="AI-Powered Smart Flashcard Generator API",
    description="Backend API for intelligent flashcard generation and adaptive learning",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(materials.router, prefix="/api/materials", tags=["Study Materials"])
app.include_router(flashcards.router, prefix="/api/flashcards", tags=["Flashcards"])
app.include_router(practice.router, prefix="/api/practice", tags=["Practice"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(topics.router, prefix="/api/topics", tags=["Topics"])
app.include_router(gamification.router, prefix="/api/gamification", tags=["Gamification"])
app.include_router(social.router, prefix="/api/social", tags=["Social"])
app.include_router(exams.router, prefix="/api/exams", tags=["Exams"])
app.include_router(import_export.router, prefix="/api/import-export", tags=["Import/Export"])
app.include_router(ai_features.router, prefix="/api/ai", tags=["AI Features"])
app.include_router(media.router, prefix="/api/media", tags=["Rich Media"])

# Add exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.get("/")
async def root():
    return {
        "message": "AI-Powered Smart Flashcard Generator API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint - returns status even if database is unavailable"""
    health_status = {
        "status": "healthy",
        "api": "running",
        "version": "1.0.0"
    }
    
    # Check database connection (optional)
    try:
        from app.database import SessionLocal
        from sqlalchemy import text
        if settings.DATABASE_URL:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            health_status["database"] = "connected"
        else:
            health_status["database"] = "not_configured"
    except Exception as e:
        logger.warning(
            "Database check failed (Vercel Postgres): %s",
            str(e),
            exc_info=True,
        )
        health_status["database"] = "unavailable"
        health_status["database_error"] = str(e)
    
    # Return 200 even if DB is unavailable (API is still functional)
    return health_status


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )


