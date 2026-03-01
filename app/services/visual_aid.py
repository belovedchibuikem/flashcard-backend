"""
Visual Aid Generation Service
"""

from typing import Optional
import openai
from app.config import settings


class VisualAidService:
    """Service for generating visual memory aids"""
    
    def __init__(self):
        api_key = getattr(settings, 'OPENAI_API_KEY', '') or ''
        self.client = openai.OpenAI(api_key=api_key) if api_key else None
    
    async def generate_visual_aid(
        self,
        concept: str,
        description: str
    ) -> Optional[str]:
        """
        Generate visual aid image using DALL-E or return placeholder URL
        In production, this would generate actual images
        """
        try:
            if not self.client:
                return None
            # Generate image using DALL-E
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=f"Educational diagram or infographic for: {concept}. {description}. Clean, colorful, memory-friendly design.",
                size="1024x1024",
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            return image_url
        except Exception as e:
            print(f"Error generating visual aid: {e}")
            # Return placeholder or use alternative method
            return None
    
    async def generate_mind_map(self, concepts: list[str]) -> Optional[str]:
        """Generate mind map visualization"""
        # Placeholder - would use specialized mind map generation
        return None
    
    async def generate_memory_palace(self, sequential_info: list[str]) -> Optional[str]:
        """Generate memory palace visualization"""
        # Placeholder - would create memory palace layout
        return None


