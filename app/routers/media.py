"""
Rich Media router - Video, Audio, LaTeX, Code, Diagrams, Annotations, 3D Models
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import shutil
from datetime import datetime

from app.database import get_db
from app.models import User, Flashcard
# Import media models from the models package (which handles the import conflict)
try:
    from app.models import MediaAttachment, ImageAnnotation, InteractiveDiagram
except ImportError:
    # Fallback: import directly from file
    import sys
    import os
    import importlib.util
    models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
    media_path = os.path.join(models_dir, 'media.py')
    if os.path.exists(media_path):
        spec = importlib.util.spec_from_file_location("app_models_media", media_path)
        media_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(media_module)
        MediaAttachment = media_module.MediaAttachment
        ImageAnnotation = media_module.ImageAnnotation
        InteractiveDiagram = media_module.InteractiveDiagram
    else:
        raise ImportError("Could not find app/models/media.py")
from app.routers.auth import get_current_user
from app.config import settings
from pydantic import BaseModel

router = APIRouter()


# Schemas
class VideoFlashcardUpdate(BaseModel):
    video_url: str
    video_type: Optional[str] = "youtube"  # youtube, vimeo, direct


class AudioFlashcardUpdate(BaseModel):
    audio_url: Optional[str] = None
    record_audio: Optional[bool] = False


class LaTeXFlashcardUpdate(BaseModel):
    latex_content: str
    render_inline: Optional[bool] = False


class CodeFlashcardUpdate(BaseModel):
    code_content: str
    code_language: str  # python, javascript, java, etc.


class DiagramFlashcardUpdate(BaseModel):
    diagram_type: str  # flowchart, mindmap, network
    diagram_data: dict


class AnnotationUpdate(BaseModel):
    annotation_data: dict  # Drawing paths, highlights


class Model3DFlashcardUpdate(BaseModel):
    model_url: str
    model_format: str  # glb, gltf, obj
    model_scale: Optional[float] = 1.0


def save_media_file(file: UploadFile, user_id: int, media_type: str) -> tuple[str, str]:
    """Save uploaded media file and return file path and URL"""
    # Ensure upload directory exists
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{user_id}_{media_type}_{timestamp}_{file.filename}"
    file_path = os.path.join(upload_dir, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # For cPanel, use relative URL path
    file_url = f"/uploads/{filename}"
    return file_path, file_url


# Video Flashcards
@router.put("/flashcards/{flashcard_id}/video")
async def add_video_to_flashcard(
    flashcard_id: int,
    video_data: VideoFlashcardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add video to flashcard (YouTube, Vimeo, or direct URL)"""
    flashcard = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id,
        Flashcard.user_id == current_user.id
    ).first()
    
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    flashcard.video_url = video_data.video_url
    db.commit()
    db.refresh(flashcard)
    
    return {"message": "Video added successfully", "video_url": flashcard.video_url}


@router.delete("/flashcards/{flashcard_id}/video")
async def remove_video_from_flashcard(
    flashcard_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove video from flashcard"""
    flashcard = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id,
        Flashcard.user_id == current_user.id
    ).first()
    
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    flashcard.video_url = None
    db.commit()
    
    return {"message": "Video removed successfully"}


# Audio Flashcards
@router.post("/flashcards/{flashcard_id}/audio")
async def upload_audio_to_flashcard(
    flashcard_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload audio file to flashcard"""
    flashcard = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id,
        Flashcard.user_id == current_user.id
    ).first()
    
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    # Validate file type
    allowed_types = ["audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg", "audio/m4a"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid audio file type")
    
    file_path, file_url = save_media_file(file, current_user.id, "audio")
    file_size = os.path.getsize(file_path)
    
    flashcard.audio_url = file_url
    
    # Create media attachment record
    attachment = MediaAttachment(
        flashcard_id=flashcard_id,
        media_type="audio",
        file_url=file_url,
        file_size=file_size,
        mime_type=file.content_type
    )
    db.add(attachment)
    db.commit()
    db.refresh(flashcard)
    
    return {"message": "Audio uploaded successfully", "audio_url": flashcard.audio_url}


@router.put("/flashcards/{flashcard_id}/audio")
async def update_audio_flashcard(
    flashcard_id: int,
    audio_data: AudioFlashcardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update audio URL for flashcard"""
    flashcard = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id,
        Flashcard.user_id == current_user.id
    ).first()
    
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    if audio_data.audio_url:
        flashcard.audio_url = audio_data.audio_url
    
    db.commit()
    
    return {"message": "Audio updated successfully"}


# LaTeX/Math Rendering
@router.put("/flashcards/{flashcard_id}/latex")
async def add_latex_to_flashcard(
    flashcard_id: int,
    latex_data: LaTeXFlashcardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add LaTeX/math content to flashcard"""
    flashcard = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id,
        Flashcard.user_id == current_user.id
    ).first()
    
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    flashcard.latex_content = latex_data.latex_content
    db.commit()
    db.refresh(flashcard)
    
    return {"message": "LaTeX content added successfully"}


# Code Syntax Highlighting
@router.put("/flashcards/{flashcard_id}/code")
async def add_code_to_flashcard(
    flashcard_id: int,
    code_data: CodeFlashcardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add code content with syntax highlighting to flashcard"""
    flashcard = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id,
        Flashcard.user_id == current_user.id
    ).first()
    
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    flashcard.code_content = code_data.code_content
    flashcard.code_language = code_data.code_language
    db.commit()
    db.refresh(flashcard)
    
    return {"message": "Code content added successfully"}


# Interactive Diagrams
@router.put("/flashcards/{flashcard_id}/diagram")
async def add_diagram_to_flashcard(
    flashcard_id: int,
    diagram_data: DiagramFlashcardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add interactive diagram to flashcard"""
    flashcard = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id,
        Flashcard.user_id == current_user.id
    ).first()
    
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    flashcard.diagram_data = diagram_data.diagram_data
    
    # Create or update diagram record
    diagram = db.query(InteractiveDiagram).filter(
        InteractiveDiagram.flashcard_id == flashcard_id
    ).first()
    
    if diagram:
        diagram.diagram_type = diagram_data.diagram_type
        diagram.diagram_data = diagram_data.diagram_data
    else:
        diagram = InteractiveDiagram(
            flashcard_id=flashcard_id,
            diagram_type=diagram_data.diagram_type,
            diagram_data=diagram_data.diagram_data
        )
        db.add(diagram)
    
    db.commit()
    
    return {"message": "Diagram added successfully"}


# Image Annotation
@router.post("/flashcards/{flashcard_id}/annotation")
async def upload_annotated_image(
    flashcard_id: int,
    file: UploadFile = File(...),
    annotation_data: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload image with annotations to flashcard"""
    flashcard = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id,
        Flashcard.user_id == current_user.id
    ).first()
    
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image file type")
    
    file_path, file_url = save_media_file(file, current_user.id, "image")
    
    flashcard.annotated_image_url = file_url
    
    # Parse annotation data if provided
    import json
    annotation_json = None
    if annotation_data:
        try:
            annotation_json = json.loads(annotation_data)
        except:
            pass
    
    # Create annotation record
    annotation = ImageAnnotation(
        flashcard_id=flashcard_id,
        image_url=file_url,
        annotation_data=annotation_json or {}
    )
    db.add(annotation)
    db.commit()
    db.refresh(flashcard)
    
    return {"message": "Annotated image uploaded successfully", "image_url": flashcard.annotated_image_url}


@router.put("/flashcards/{flashcard_id}/annotation")
async def update_image_annotation(
    flashcard_id: int,
    annotation_data: AnnotationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update image annotations"""
    annotation = db.query(ImageAnnotation).join(Flashcard).filter(
        ImageAnnotation.flashcard_id == flashcard_id,
        Flashcard.user_id == current_user.id
    ).first()
    
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    annotation.annotation_data = annotation_data.annotation_data
    db.commit()
    
    return {"message": "Annotation updated successfully"}


# 3D Models
@router.post("/flashcards/{flashcard_id}/model-3d")
async def upload_3d_model(
    flashcard_id: int,
    file: UploadFile = File(...),
    model_format: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload 3D model to flashcard"""
    flashcard = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id,
        Flashcard.user_id == current_user.id
    ).first()
    
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    # Validate format
    allowed_formats = ["glb", "gltf", "obj", "fbx"]
    if model_format.lower() not in allowed_formats:
        raise HTTPException(status_code=400, detail=f"Invalid 3D model format. Allowed: {', '.join(allowed_formats)}")
    
    file_path, file_url = save_media_file(file, current_user.id, "3d_model")
    file_size = os.path.getsize(file_path)
    
    flashcard.model_3d_url = file_url
    flashcard.model_3d_format = model_format.lower()
    
    # Create media attachment
    attachment = MediaAttachment(
        flashcard_id=flashcard_id,
        media_type="model_3d",
        file_url=file_url,
        file_size=file_size,
        mime_type=f"model/{model_format.lower()}",
        metadata={"format": model_format.lower()}
    )
    db.add(attachment)
    db.commit()
    db.refresh(flashcard)
    
    return {
        "message": "3D model uploaded successfully",
        "model_url": flashcard.model_3d_url,
        "model_format": flashcard.model_3d_format
    }


@router.put("/flashcards/{flashcard_id}/model-3d")
async def update_3d_model(
    flashcard_id: int,
    model_data: Model3DFlashcardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update 3D model URL for flashcard"""
    flashcard = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id,
        Flashcard.user_id == current_user.id
    ).first()
    
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    flashcard.model_3d_url = model_data.model_url
    flashcard.model_3d_format = model_data.model_format
    db.commit()
    
    return {"message": "3D model updated successfully"}


@router.get("/flashcards/{flashcard_id}/media")
async def get_flashcard_media(
    flashcard_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all media attachments for a flashcard"""
    flashcard = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id
    ).first()
    
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    # Check if user has access (owner or public)
    if flashcard.user_id != current_user.id:
        # Could add public deck check here
        raise HTTPException(status_code=403, detail="Access denied")
    
    attachments = db.query(MediaAttachment).filter(
        MediaAttachment.flashcard_id == flashcard_id
    ).all()
    
    return {
        "flashcard_id": flashcard_id,
        "video_url": flashcard.video_url,
        "audio_url": flashcard.audio_url,
        "latex_content": flashcard.latex_content,
        "code_content": flashcard.code_content,
        "code_language": flashcard.code_language,
        "diagram_data": flashcard.diagram_data,
        "annotated_image_url": flashcard.annotated_image_url,
        "model_3d_url": flashcard.model_3d_url,
        "model_3d_format": flashcard.model_3d_format,
        "attachments": [
            {
                "id": a.id,
                "media_type": a.media_type,
                "file_url": a.file_url,
                "file_size": a.file_size,
                "mime_type": a.mime_type,
                "metadata": a.metadata
            }
            for a in attachments
        ]
    }
