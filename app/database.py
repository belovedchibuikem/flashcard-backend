"""
Database connection and session management
Supports both MySQL and PostgreSQL
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
import os

# Detect database type from DATABASE_URL
DATABASE_URL = settings.DATABASE_URL or ""

# Detect if we're using MySQL or PostgreSQL (safe defaults)
IS_MYSQL = bool(DATABASE_URL and (DATABASE_URL.startswith("mysql://") or DATABASE_URL.startswith("mysql+pymysql://")))
IS_POSTGRESQL = bool(DATABASE_URL and (DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")))

# Auto-detect database type and configure accordingly
if DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://"):
    # PostgreSQL configuration
    # Vercel Postgres format: postgres://user:pass@host:port/dbname
    # Convert postgres:// to postgresql:// for SQLAlchemy
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=10,
        echo=settings.DEBUG
    )
elif DATABASE_URL.startswith("mysql://") or DATABASE_URL.startswith("mysql+pymysql://"):
    # MySQL configuration (PlanetScale, Railway, etc.)
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=10,
        echo=settings.DEBUG
    )
else:
    # Default configuration (will use whatever DATABASE_URL specifies)
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.DEBUG
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


