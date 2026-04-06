"""
Visual aid generation: DALL·E images when configured, with safe fallbacks for dev / quota issues.
"""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import quote

import openai

from app.config import settings

logger = logging.getLogger(__name__)

# Short label for placeholder images (placehold.co has URL length limits)
_MAX_LABEL_LEN = 48


def _fallback_image_url(title: str, subtitle: str = "") -> str:
    """PNG placeholder (no API key). Browser/client can display as flashcard visual."""
    label = (title or "Study").strip().replace("\n", " ")[:_MAX_LABEL_LEN]
    if subtitle:
        label = f"{label} — {(subtitle or '')[:24]}"
    encoded = quote(label, safe="")
    return f"https://placehold.co/600x400/1e3a5f/dbeafe/png?text={encoded}"


class VisualAidService:
    """Generate educational imagery for flashcards."""

    def __init__(self):
        api_key = getattr(settings, "OPENAI_API_KEY", "") or ""
        self.client = openai.OpenAI(api_key=api_key) if api_key else None

    async def generate_visual_aid(self, concept: str, description: str) -> Optional[str]:
        """
        Create a memory-friendly illustration URL for a flashcard concept.
        Uses DALL·E 3 when OPENAI_API_KEY is set; otherwise a labeled placeholder image.
        """
        concept = (concept or "").strip() or "Study concept"
        description = (description or "").strip()

        if self.client:
            try:
                prompt = (
                    f"Clean educational infographic or simple labeled diagram for students: {concept}. "
                    f"Context: {description}. "
                    "Bold colors, large readable labels, no photorealistic faces, suitable for flashcards."
                )
                response = self.client.images.generate(
                    model="dall-e-3",
                    prompt=prompt[:4000],
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )
                url = response.data[0].url
                if url:
                    return url
            except Exception as e:
                logger.warning("DALL·E visual aid failed, using placeholder: %s", e)

        return _fallback_image_url(concept, description)

    async def generate_mind_map(self, concepts: list[str]) -> Optional[str]:
        """Diagram suggesting relationships between key terms (DALL·E or placeholder)."""
        labels = [c.strip() for c in (concepts or []) if c and str(c).strip()]
        if not labels:
            return _fallback_image_url("Mind map", "Add concepts")

        headline = labels[0]
        rest = ", ".join(labels[1:8])
        blurb = f"terms: {rest}" if rest else ""

        if self.client:
            try:
                prompt = (
                    "Mind map diagram for students. Central concept with labeled branches, "
                    f"nodes: {', '.join(labels[:12])}. Flat vector style, high contrast, readable text."
                )
                response = self.client.images.generate(
                    model="dall-e-3",
                    prompt=prompt[:4000],
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )
                url = response.data[0].url
                if url:
                    return url
            except Exception as e:
                logger.warning("Mind map DALL·E failed: %s", e)

        return _fallback_image_url(f"Mind map: {headline}", blurb)

    async def generate_memory_palace(self, sequential_info: list[str]) -> Optional[str]:
        """Illustration for a memory palace journey through ordered facts."""
        steps = [s.strip() for s in (sequential_info or []) if s and str(s).strip()]
        if not steps:
            return _fallback_image_url("Memory palace", "Ordered steps")

        summary = " → ".join(steps[:6])
        if self.client:
            try:
                prompt = (
                    "Single isometric or cutaway illustration of a memorable building interior "
                    "(memory palace). Numbered stations along a path for memorization. "
                    f"Sequence to encode: {summary}. "
                    "Educational poster style, no gore, readable numbers."
                )
                response = self.client.images.generate(
                    model="dall-e-3",
                    prompt=prompt[:4000],
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )
                url = response.data[0].url
                if url:
                    return url
            except Exception as e:
                logger.warning("Memory palace DALL·E failed: %s", e)

        return _fallback_image_url("Memory palace", summary[:_MAX_LABEL_LEN])
