"""
Rich Media Models for flashcards
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base, IS_MYSQL


class MediaAttachment(Base):
    """Generic media attachment model"""
    __tablename__ = "media_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    flashcard_id = Column(Integer, ForeignKey("flashcards.id"), nullable=False)
    media_type = Column(String(50), nullable=False)  # video, audio, image, diagram, model_3d
    file_url = Column(String(500), nullable=False)
    file_size = Column(Integer)  # Size in bytes
    mime_type = Column(String(100))
    metadata = Column(JSON)  # Additional metadata (duration, dimensions, etc.)
    created_at = Column(DateTime, server_default=func.now())
    
    # MySQL-specific table args (ignored by PostgreSQL)
    __table_args__ = ({"mysql_engine": "InnoDB"},) if IS_MYSQL else ()


class ImageAnnotation(Base):
    """Image annotations/drawings"""
    __tablename__ = "image_annotations"
    
    id = Column(Integer, primary_key=True, index=True)
    flashcard_id = Column(Integer, ForeignKey("flashcards.id"), nullable=False)
    image_url = Column(String(500), nullable=False)
    annotation_data = Column(JSON)  # Drawing paths, highlights, shapes
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # MySQL-specific table args (ignored by PostgreSQL)
    __table_args__ = ({"mysql_engine": "InnoDB"},) if IS_MYSQL else ()


class InteractiveDiagram(Base):
    """Interactive diagram data"""
    __tablename__ = "interactive_diagrams"
    
    id = Column(Integer, primary_key=True, index=True)
    flashcard_id = Column(Integer, ForeignKey("flashcards.id"), nullable=False)
    diagram_type = Column(String(50))  # flowchart, mindmap, network, etc.
    diagram_data = Column(JSON)  # Nodes, edges, shapes, connections
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # MySQL-specific table args (ignored by PostgreSQL)
    __table_args__ = ({"mysql_engine": "InnoDB"},) if IS_MYSQL else ()
