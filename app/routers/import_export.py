"""
Import/Export router - Anki, Quizlet, CSV, PDF
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import json

from app.database import get_db
from app.models import User, Flashcard, Topic
from app.routers.auth import get_current_user
from app.services.import_export_service import ImportExportService
from app.services.enhanced_ai_service import EnhancedAIService
from fastapi.responses import StreamingResponse
import io

router = APIRouter()
import_export_service = ImportExportService()
ai_service = EnhancedAIService()


@router.post("/import/csv")
async def import_csv(
    file: UploadFile = File(...),
    topic_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import flashcards from CSV file"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    content = await file.read()
    csv_content = content.decode('utf-8')
    
    try:
        flashcards_data = await import_export_service.import_from_csv(csv_content)
        
        created_flashcards = []
        for card_data in flashcards_data:
            flashcard = Flashcard(
                user_id=current_user.id,
                topic_id=topic_id,
                question=card_data['question'],
                answer=card_data['answer'],
                flashcard_type=card_data.get('flashcard_type', 'concept'),
                difficulty_level=card_data.get('difficulty_level', 'medium'),
                tags=card_data.get('tags', []),
                importance_score=card_data.get('importance_score', 5)
            )
            db.add(flashcard)
            created_flashcards.append(flashcard)
        
        db.commit()
        
        return {
            "message": f"Successfully imported {len(created_flashcards)} flashcards",
            "count": len(created_flashcards)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error importing CSV: {str(e)}")


@router.get("/export/csv")
async def export_csv(
    topic_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export flashcards to CSV"""
    query = db.query(Flashcard).filter(Flashcard.user_id == current_user.id)
    
    if topic_id:
        query = query.filter(Flashcard.topic_id == topic_id)
    
    flashcards = query.all()
    
    flashcards_data = [
        {
            "question": f.question,
            "answer": f.answer,
            "flashcard_type": f.flashcard_type,
            "difficulty_level": f.difficulty_level,
            "tags": f.tags or [],
            "importance_score": f.importance_score
        }
        for f in flashcards
    ]
    
    csv_content = await import_export_service.export_to_csv(flashcards_data)
    
    return StreamingResponse(
        io.BytesIO(csv_content.encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=flashcards_export.csv"}
    )


@router.post("/import/anki")
async def import_anki(
    file: UploadFile = File(...),
    topic_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import flashcards from Anki .apkg file"""
    if not file.filename.endswith('.apkg'):
        raise HTTPException(status_code=400, detail="File must be an .apkg file")
    
    # Save file temporarily
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.apkg') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        flashcards_data = await import_export_service.import_from_anki(tmp_path)
        
        if not flashcards_data:
            raise HTTPException(
                status_code=400,
                detail="Anki import requires full SQLite parsing implementation"
            )
        
        created_flashcards = []
        for card_data in flashcards_data:
            flashcard = Flashcard(
                user_id=current_user.id,
                topic_id=topic_id,
                question=card_data['question'],
                answer=card_data['answer'],
                flashcard_type=card_data.get('flashcard_type', 'concept'),
                difficulty_level=card_data.get('difficulty_level', 'medium'),
                tags=card_data.get('tags', []),
                importance_score=card_data.get('importance_score', 5)
            )
            db.add(flashcard)
            created_flashcards.append(flashcard)
        
        db.commit()
        
        return {
            "message": f"Successfully imported {len(created_flashcards)} flashcards",
            "count": len(created_flashcards)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error importing Anki file: {str(e)}")
    finally:
        os.unlink(tmp_path)


@router.get("/export/anki")
async def export_anki(
    topic_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export flashcards to Anki .apkg format"""
    query = db.query(Flashcard).filter(Flashcard.user_id == current_user.id)
    
    if topic_id:
        query = query.filter(Flashcard.topic_id == topic_id)
    
    flashcards = query.all()
    
    flashcards_data = [
        {
            "question": f.question,
            "answer": f.answer,
            "flashcard_type": f.flashcard_type,
            "difficulty_level": f.difficulty_level,
            "tags": f.tags or [],
            "importance_score": f.importance_score
        }
        for f in flashcards
    ]
    
    apkg_data = await import_export_service.export_to_anki(flashcards_data)
    
    if not apkg_data:
        raise HTTPException(
            status_code=501,
            detail="Anki export requires full SQLite database creation implementation"
        )
    
    return StreamingResponse(
        io.BytesIO(apkg_data),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=flashcards_export.apkg"}
    )


@router.post("/import/quizlet")
async def import_quizlet(
    quizlet_data: dict,
    topic_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import flashcards from Quizlet JSON format"""
    try:
        flashcards_data = await import_export_service.import_from_quizlet(quizlet_data)
        
        created_flashcards = []
        for card_data in flashcards_data:
            flashcard = Flashcard(
                user_id=current_user.id,
                topic_id=topic_id,
                question=card_data['question'],
                answer=card_data['answer'],
                flashcard_type=card_data.get('flashcard_type', 'definition'),
                difficulty_level=card_data.get('difficulty_level', 'medium'),
                tags=card_data.get('tags', []),
                importance_score=card_data.get('importance_score', 5)
            )
            db.add(flashcard)
            created_flashcards.append(flashcard)
        
        db.commit()
        
        return {
            "message": f"Successfully imported {len(created_flashcards)} flashcards",
            "count": len(created_flashcards)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error importing Quizlet data: {str(e)}")


@router.get("/export/quizlet")
async def export_quizlet(
    topic_id: int = None,
    title: str = "Exported Deck",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export flashcards to Quizlet JSON format"""
    query = db.query(Flashcard).filter(Flashcard.user_id == current_user.id)
    
    if topic_id:
        query = query.filter(Flashcard.topic_id == topic_id)
    
    flashcards = query.all()
    
    flashcards_data = [
        {
            "question": f.question,
            "answer": f.answer,
            "flashcard_type": f.flashcard_type,
            "difficulty_level": f.difficulty_level,
            "tags": f.tags or [],
            "importance_score": f.importance_score
        }
        for f in flashcards
    ]
    
    quizlet_data = await import_export_service.export_to_quizlet(flashcards_data, title)
    
    return quizlet_data


@router.post("/import/pdf-auto")
async def import_pdf_auto_extract(
    file: UploadFile = File(...),
    topic_id: int = None,
    count: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import PDF and automatically extract flashcards using AI"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Save file temporarily
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # Extract text from PDF (would use PyPDF2 or similar)
        from app.services.simple_ocr_service import SimpleOCRService
        ocr_service = SimpleOCRService()
        extracted_text = await ocr_service.extract_text_from_pdf(tmp_path)
        
        if not extracted_text:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        # Generate flashcards using AI
        flashcards_data = await ai_service.generate_flashcards(extracted_text, count)
        
        created_flashcards = []
        for card_data in flashcards_data:
            flashcard = Flashcard(
                user_id=current_user.id,
                topic_id=topic_id,
                question=card_data.get('question', ''),
                answer=card_data.get('answer', ''),
                flashcard_type=card_data.get('type', 'concept'),
                difficulty_level=card_data.get('difficulty', 'medium'),
                tags=card_data.get('tags', []),
                importance_score=card_data.get('importance_score', 5),
                mnemonic_device=card_data.get('mnemonic')
            )
            db.add(flashcard)
            created_flashcards.append(flashcard)
        
        db.commit()
        
        return {
            "message": f"Successfully extracted and created {len(created_flashcards)} flashcards from PDF",
            "count": len(created_flashcards)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing PDF: {str(e)}")
    finally:
        os.unlink(tmp_path)
