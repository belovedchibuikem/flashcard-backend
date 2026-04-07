"""
Study Materials router - File upload and processing
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
import mimetypes
from datetime import datetime
from app.database import get_db
from app.models import User, StudyMaterial, ProcessingStatus, FileType
from app.schemas import StudyMaterialResponse, StudyMaterialCreate
from app.routers.auth import get_current_user
from app.services.simple_ocr_service import SimpleOCRService
from app.services.enhanced_ai_service import EnhancedAIService
from app.config import settings

router = APIRouter()
ocr_service = SimpleOCRService()
ai_service = EnhancedAIService()

# Mobile/web clients often send application/octet-stream or omit MIME; validate with sniff + filename.
ALLOWED_MATERIAL_TYPES = frozenset({
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
})


def _normalize_mime(mime: Optional[str]) -> Optional[str]:
    if not mime:
        return None
    m = mime.split(";")[0].strip().lower()
    if m == "image/jpg":
        return "image/jpeg"
    return m


def _sniff_bytes_mime(content: bytes) -> Optional[str]:
    if len(content) >= 4 and content[:4] == b"%PDF":
        return "application/pdf"
    if len(content) >= 3 and content[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(content) >= 8 and content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(content) >= 6 and content[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def _guess_mime_from_filename(filename: str) -> Optional[str]:
    if not filename:
        return None
    guessed, _ = mimetypes.guess_type(filename)
    return _normalize_mime(guessed)


def resolve_study_material_mime(
    declared: Optional[str],
    content: bytes,
    filename: str,
) -> Optional[str]:
    """Pick a trusted MIME type for study materials (PDF + images)."""
    declared_n = _normalize_mime(declared)
    if declared_n in ALLOWED_MATERIAL_TYPES:
        return declared_n

    sniffed = _sniff_bytes_mime(content)
    if sniffed in ALLOWED_MATERIAL_TYPES:
        return sniffed

    guessed = _guess_mime_from_filename(filename)
    if guessed in ALLOWED_MATERIAL_TYPES:
        return guessed

    if declared_n in (None, "", "application/octet-stream", "binary/octet-stream"):
        if sniffed and sniffed in ALLOWED_MATERIAL_TYPES:
            return sniffed
        if guessed and guessed in ALLOWED_MATERIAL_TYPES:
            return guessed

    return None


def save_uploaded_file(file: UploadFile, user_id: int) -> tuple[str, str]:
    """Save uploaded file and return file path and URL"""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{user_id}_{timestamp}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    file_url = f"/uploads/{filename}"
    return file_path, file_url


@router.post("/upload", response_model=StudyMaterialResponse, status_code=status.HTTP_201_CREATED)
async def upload_material(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload study material (PDF, image, document)"""
    # Validate file exists
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validate file size
    file_content = await file.read()
    file_size = len(file_content)
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE / (1024*1024):.1f}MB"
        )
    
    # Reset file pointer
    await file.seek(0)

    effective_mime = resolve_study_material_mime(
        file.content_type,
        file_content,
        file.filename or "",
    )
    if not effective_mime:
        raise HTTPException(
            status_code=400,
            detail="File type not supported. Allowed types: PDF, JPEG, PNG, GIF, WEBP",
        )

    file_type = None
    if effective_mime == "application/pdf":
        file_type = FileType.PDF
    elif effective_mime.startswith("image/"):
        file_type = FileType.IMAGE
    else:
        file_type = FileType.DOCUMENT
    
    if not title:
        title = file.filename or "Untitled Material"
    
    # Check if auto-extract is requested (for PDFs)
    auto_extract = False  # Can be added as a form parameter
    
    try:
        # Save file
        file_path, file_url = save_uploaded_file(file, current_user.id)
        file_size = os.path.getsize(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    try:
        # Create study material record
        material = StudyMaterial(
            user_id=current_user.id,
            title=title,
            file_type=file_type,
            file_url=file_url,
            file_size=file_size,
            original_filename=file.filename,
            processing_status=ProcessingStatus.PENDING
        )
        db.add(material)
        db.commit()
        db.refresh(material)
        
        # Process file asynchronously using background task
        # In production, use Celery or similar task queue
        # For now, process in background using asyncio
        from fastapi import BackgroundTasks
        # Note: In production, use proper background task queue
        # For development, we'll process synchronously but could use BackgroundTasks
        import asyncio
        try:
            # Schedule background processing
            loop = asyncio.get_event_loop()
            loop.create_task(process_material(material.id, db))
        except RuntimeError:
            # If no event loop, process synchronously
            await process_material(material.id, db)
        
        return material
    except Exception as e:
        # Cleanup file if database operation fails
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error creating material record: {str(e)}")


async def process_material(material_id: int, db: Session):
    """Process uploaded material: extract text and generate flashcards"""
    material = db.query(StudyMaterial).filter(StudyMaterial.id == material_id).first()
    if not material:
        return
    
    material.processing_status = ProcessingStatus.PROCESSING
    db.commit()
    
    try:
        # Extract text based on file type
        extracted_text = ""
        file_path = os.path.join(settings.UPLOAD_DIR, os.path.basename(material.file_url))
        if material.file_type == FileType.PDF:
            extracted_text = await ocr_service.extract_text_from_pdf(file_path)
        elif material.file_type == FileType.IMAGE:
            # Enhanced OCR service automatically tries best APIs with fallback
            extracted_text = await ocr_service.extract_text_from_image(
                file_path, 
                is_handwritten=False  # Can be enhanced with ML-based detection
            )
            material.ocr_processed = True
        
        if extracted_text:
            material.extracted_text = extracted_text
            material.processing_status = ProcessingStatus.COMPLETED
        else:
            material.processing_status = ProcessingStatus.FAILED
        
        db.commit()
    except Exception as e:
        print(f"Error processing material: {e}")
        material.processing_status = ProcessingStatus.FAILED
        db.commit()


@router.get("/", response_model=List[StudyMaterialResponse])
async def get_materials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all study materials for current user"""
    materials = db.query(StudyMaterial).filter(StudyMaterial.user_id == current_user.id).all()
    return materials


@router.get("/{material_id}", response_model=StudyMaterialResponse)
async def get_material(
    material_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific study material"""
    material = db.query(StudyMaterial).filter(
        StudyMaterial.id == material_id,
        StudyMaterial.user_id == current_user.id
    ).first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    return material


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(
    material_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete study material"""
    material = db.query(StudyMaterial).filter(
        StudyMaterial.id == material_id,
        StudyMaterial.user_id == current_user.id
    ).first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    # Delete file
    file_path = os.path.join(settings.UPLOAD_DIR, os.path.basename(material.file_url))
    if os.path.exists(file_path):
        os.remove(file_path)
    
    db.delete(material)
    db.commit()
    return None


@router.post("/{material_id}/auto-extract-flashcards", status_code=status.HTTP_200_OK)
async def auto_extract_flashcards_from_pdf(
    material_id: int,
    count: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Automatically extract and create flashcards from PDF using AI"""
    material = db.query(StudyMaterial).filter(
        StudyMaterial.id == material_id,
        StudyMaterial.user_id == current_user.id
    ).first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    if material.file_type != FileType.PDF:
        raise HTTPException(status_code=400, detail="Auto-extract only available for PDF files")
    
    if not material.extracted_text:
        raise HTTPException(status_code=400, detail="Material not processed yet. Please wait for processing to complete.")
    
    # Generate flashcards using AI
    from app.routers.flashcards import router as flashcards_router
    ai_flashcards = await ai_service.generate_flashcards(material.extracted_text, count)
    
    created_count = 0
    for ai_card in ai_flashcards:
        from app.models import Flashcard
        flashcard = Flashcard(
            user_id=current_user.id,
            topic_id=None,
            study_material_id=material_id,
            question=ai_card.get('question', ''),
            answer=ai_card.get('answer', ''),
            flashcard_type=ai_card.get('type', 'concept'),
            difficulty_level=ai_card.get('difficulty', 'medium'),
            tags=ai_card.get('tags', []),
            importance_score=ai_card.get('importance_score', 5),
            mnemonic_device=ai_card.get('mnemonic')
        )
        db.add(flashcard)
        created_count += 1
    
    db.commit()
    
    return {
        "message": f"Successfully extracted and created {created_count} flashcards",
        "count": created_count
    }

