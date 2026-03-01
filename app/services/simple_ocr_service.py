"""
Lightweight OCR Service - Uses Google Cloud Vision REST API (no heavy SDKs).
Works on Vercel and other serverless platforms. Only requires GOOGLE_CLOUD_VISION_API_KEY.
"""

import base64
import asyncio
from typing import Optional
from app.config import settings

# Use httpx for async HTTP - lightweight, no heavy SDKs
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class SimpleOCRService:
    """
    Lightweight OCR using Google Cloud Vision REST API.
    Single provider, minimal dependencies, works on Vercel.
    """

    VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"

    def __init__(self):
        self.api_key = getattr(settings, "GOOGLE_CLOUD_VISION_API_KEY", "") or ""
        self.api_key = (self.api_key or "").strip()

    def _is_available(self) -> bool:
        if not HTTPX_AVAILABLE:
            print("SimpleOCR: Install httpx (pip install httpx) for image OCR.")
            return False
        return bool(self.api_key)

    async def extract_text_from_image(
        self, image_path: str, is_handwritten: bool = False
    ) -> Optional[str]:
        """
        Extract text from image using Google Cloud Vision REST API.
        Requires GOOGLE_CLOUD_VISION_API_KEY in environment.
        """
        if not self._is_available():
            print(
                "SimpleOCR: Set GOOGLE_CLOUD_VISION_API_KEY for image OCR. "
                "Get a key at https://console.cloud.google.com/apis/credentials"
            )
            return None

        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            content_b64 = base64.b64encode(image_bytes).decode("utf-8")

            payload = {
                "requests": [
                    {
                        "image": {"content": content_b64},
                        "features": [{"type": "TEXT_DETECTION", "maxResults": 1}],
                    }
                ]
            }

            url = f"{self.VISION_API_URL}?key={self.api_key}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)

            if response.status_code != 200:
                err = response.text
                print(f"Google Vision API error {response.status_code}: {err[:200]}")
                return None

            data = response.json()
            responses = data.get("responses", [])
            if not responses:
                return None

            first = responses[0]
            if "error" in first:
                print(f"Vision API error: {first['error']}")
                return None

            # TEXT_DETECTION returns full text in fullTextAnnotation
            full_text = first.get("fullTextAnnotation", {})
            text = full_text.get("text", "").strip()
            if text:
                return text

            # Fallback: concatenate textAnnotations
            annotations = first.get("textAnnotations", [])
            if annotations:
                return annotations[0].get("description", "").strip()
            return None

        except Exception as e:
            print(f"SimpleOCR error: {e}")
            return None

    async def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """Extract text from PDF using PyPDF2 (no external APIs)."""
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip() or None
        except Exception as e:
            print(f"PDF extraction error: {e}")
            return None
