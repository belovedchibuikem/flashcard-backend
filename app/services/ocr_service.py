"""
OCR Service for extracting text from images and handwritten notes
"""

import os
from typing import Optional
from PIL import Image
import pytesseract
from app.config import settings

try:
    from google.cloud import vision
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False


class OCRService:
    """Service for Optical Character Recognition"""
    
    def __init__(self):
        self.use_google_vision = (
            GOOGLE_VISION_AVAILABLE and 
            settings.GOOGLE_CLOUD_VISION_API_KEY
        )
        
        if self.use_google_vision:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_APPLICATION_CREDENTIALS
            self.vision_client = vision.ImageAnnotatorClient()
    
    async def extract_text_from_image(self, image_path: str) -> Optional[str]:
        """
        Extract text from image using OCR
        Prefers Google Cloud Vision API, falls back to Tesseract
        """
        try:
            if self.use_google_vision:
                return await self._extract_with_google_vision(image_path)
            else:
                return await self._extract_with_tesseract(image_path)
        except Exception as e:
            print(f"OCR Error: {e}")
            return None
    
    async def _extract_with_google_vision(self, image_path: str) -> str:
        """Extract text using Google Cloud Vision API"""
        with open(image_path, 'rb') as image_file:
            content = image_file.read()
        
        image = vision.Image(content=content)
        response = self.vision_client.text_detection(image=image)
        
        if response.error.message:
            raise Exception(f"Google Vision API Error: {response.error.message}")
        
        texts = response.text_annotations
        if texts:
            return texts[0].description
        return ""
    
    async def _extract_with_tesseract(self, image_path: str) -> str:
        """Extract text using Tesseract OCR"""
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            print(f"Tesseract Error: {e}")
            return ""
    
    async def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """
        Extract text from PDF file
        """
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(pdf_path)
            text = ""
            
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            return text
        except Exception as e:
            print(f"PDF Extraction Error: {e}")
            return None
    
    async def preprocess_image(self, image_path: str) -> str:
        """
        Preprocess image for better OCR results
        """
        try:
            from PIL import ImageEnhance, ImageFilter
            import cv2
            import numpy as np
            
            # Read image
            img = cv2.imread(image_path)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply thresholding
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(thresh)
            
            # Save processed image
            processed_path = image_path.replace('.', '_processed.')
            cv2.imwrite(processed_path, denoised)
            
            return processed_path
        except Exception as e:
            print(f"Image preprocessing error: {e}")
            return image_path


