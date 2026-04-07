"""
Enhanced AI Service with Latest Models for Better Accuracy
Supports GPT-4 Turbo, Claude 3.5 Sonnet, and Gemini 2.5 Flash-Lite
"""

import json
import logging
import os
import openai
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)


def _strip_json_fences(raw: str) -> str:
    t = (raw or "").strip()
    if not t.startswith("```"):
        return t
    lines = t.split("\n")
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _find_json_object_in_text(text: str) -> Optional[str]:
    """If the model adds prose around JSON, pull the first {...} span."""
    t = _strip_json_fences(text)
    start = t.find("{")
    depth = 0
    for i, ch in enumerate(t[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return t[start : i + 1]
    return None


def _normalize_flashcard_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Map common LLM key variants to question/answer expected by the API."""
    q = d.get("question") or d.get("Question") or d.get("q") or d.get("Q")
    a = d.get("answer") or d.get("Answer") or d.get("a") or d.get("A")
    out = dict(d)
    out["question"] = (str(q).strip() if q is not None else "")
    out["answer"] = (str(a).strip() if a is not None else "")
    return out


def _normalize_flashcard_list(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_normalize_flashcard_dict(x) for x in items if isinstance(x, dict)]


def _flashcard_list_from_parsed(result: Any) -> List[Dict[str, Any]]:
    """Normalize LLM output to a list of flashcard dicts (tolerant of key names and nesting)."""
    if isinstance(result, list):
        return [x for x in result if isinstance(x, dict)]
    if isinstance(result, dict):
        for key in (
            "flashcards",
            "flash_cards",
            "cards",
            "data",
            "items",
            "results",
        ):
            v = result.get(key)
            if isinstance(v, list):
                found = [x for x in v if isinstance(x, dict)]
                if found:
                    return found
        if len(result) == 1:
            v = next(iter(result.values()))
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
            if isinstance(v, dict):
                inner = _flashcard_list_from_parsed(v)
                if inner:
                    return inner
        for v in result.values():
            if isinstance(v, dict):
                inner = _flashcard_list_from_parsed(v)
                if inner:
                    return inner
    return []


def _parse_llm_json(content: str) -> Any:
    """Parse JSON from chat response; tolerate markdown and extra wrapping text."""
    t = _strip_json_fences(content)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        blob = _find_json_object_in_text(t)
        if blob:
            return json.loads(blob)
        raise


def _gemini_aggregate_text(response: Any) -> str:
    try:
        return (response.text or "").strip()
    except Exception:
        pass
    try:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return ""
        parts = getattr(candidates[0].content, "parts", None) or []
        return "".join(getattr(p, "text", "") or "" for p in parts).strip()
    except Exception:
        return ""


def _effective_api_key(val: str) -> str:
    """Strip and reject template placeholder values from .env samples."""
    v = (val or "").strip()
    if not v:
        return ""
    lower = v.lower()
    if lower in ("your_openai_api_key_here", "changeme", "none", "sk-your-key-here"):
        return ""
    if lower.startswith("your_") and "here" in lower:
        return ""
    return v

# Claude (Anthropic)
try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

# Gemini (Google)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class EnhancedAIService:
    """
    Enhanced AI Service with multiple providers
    Uses GPT-4 Turbo/GPT-4o for general tasks
    Uses Claude 3.5 Sonnet for long documents
    Uses Gemini 2.5 Flash-Lite for fast/cost-efficient tasks
    """
    
    def __init__(self):
        # Prefer process env (Vercel) then settings — avoids Pydantic/env_file edge cases
        openai_key = _effective_api_key(
            os.getenv("OPENAI_API_KEY") or getattr(settings, "OPENAI_API_KEY", "") or ""
        )
        self.openai_client = openai.OpenAI(api_key=openai_key) if openai_key else None
        self.openai_model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

        anthropic_key = _effective_api_key(
            os.getenv("ANTHROPIC_API_KEY") or getattr(settings, "ANTHROPIC_API_KEY", "") or ""
        )
        if CLAUDE_AVAILABLE and anthropic_key:
            self.claude_client = anthropic.Anthropic(api_key=anthropic_key)
        else:
            self.claude_client = None

        gemini_key = _effective_api_key(
            os.getenv("GOOGLE_GEMINI_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or getattr(settings, "GOOGLE_GEMINI_API_KEY", "")
            or ""
        )
        gemini_model = getattr(settings, "GOOGLE_GEMINI_MODEL", "gemini-2.0-flash")
        if GEMINI_AVAILABLE and gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini_model = genai.GenerativeModel(gemini_model)
        else:
            self.gemini_model = None

        self._last_flashcard_error: Optional[str] = None

    def has_any_llm(self) -> bool:
        return bool(self.openai_client or self.gemini_model)
    
    async def extract_key_concepts(
        self, 
        text: str, 
        use_claude_for_long: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Extract key concepts with automatic model selection
        Uses Claude for long documents (>8000 tokens), GPT-4 Turbo otherwise
        """
        # Use Claude for long documents (200K context vs GPT-4's 8K)
        if use_claude_for_long and len(text) > 8000 and self.claude_client:
            return await self._extract_concepts_with_claude(text)
        
        # Use GPT-4 Turbo for shorter documents
        return await self._extract_concepts_with_openai(text)
    
    async def _extract_concepts_with_openai(self, text: str) -> List[Dict[str, Any]]:
        """Extract concepts using GPT-4 Turbo"""
        if not self.openai_client:
            return []
        prompt = f"""
        Analyze the following study material and extract key concepts, definitions, formulas, and important facts.
        Focus on exam-relevant content. Return a JSON array with objects containing:
        - concept: the key concept name
        - definition: brief definition or explanation
        - importance: score from 1-10
        - type: one of ['definition', 'formula', 'concept', 'fact', 'process']
        
        Text:
        {text[:4000]}
        
        Return only valid JSON array, no additional text.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing study materials and extracting key concepts for exam preparation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}  # Better JSON parsing
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result.get('concepts', []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        except Exception as e:
            print(f"Error extracting concepts with OpenAI: {e}")
            return []
    
    async def _extract_concepts_with_claude(self, text: str) -> List[Dict[str, Any]]:
        """Extract concepts using Claude 3.5 Sonnet (better for long documents)"""
        prompt = f"""
        Analyze the following study material and extract key concepts, definitions, formulas, and important facts.
        Focus on exam-relevant content. Return a JSON array with objects containing:
        - concept: the key concept name
        - definition: brief definition or explanation
        - importance: score from 1-10
        - type: one of ['definition', 'formula', 'concept', 'fact', 'process']
        
        Text:
        {text[:100000]}  # Claude can handle much longer text
        
        Return only valid JSON array, no additional text.
        """
        
        try:
            message = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            import json
            result = json.loads(message.content[0].text)
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error extracting concepts with Claude: {e}")
            return []
    
    async def generate_flashcards(
        self, 
        text: str, 
        count: int = 10,
        use_fast_model: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Generate flashcards with model selection.
        Tries primary provider then falls back so a bad OpenAI parse/model does not block Gemini (and vice versa).
        """
        self._last_flashcard_error = None
        if not (text or "").strip():
            self._last_flashcard_error = "No text extracted from material to generate from."
            return []

        async def try_gemini() -> List[Dict[str, Any]]:
            if not self.gemini_model:
                return []
            return await self._generate_flashcards_with_gemini(text, count)

        async def try_openai() -> List[Dict[str, Any]]:
            if not self.openai_client:
                return []
            return await self._generate_flashcards_with_openai(text, count)

        if use_fast_model:
            order = (try_gemini, try_openai)
        else:
            order = (try_openai, try_gemini)

        errors: List[str] = []
        for attempt in order:
            out = await attempt()
            if out:
                norm = _normalize_flashcard_list(out)
                # Drop entries with no text at all (prevents "success" with blank cards)
                norm = [c for c in norm if c.get("question") or c.get("answer")]
                if norm:
                    return norm
                self._last_flashcard_error = (
                    (self._last_flashcard_error or "")
                    + " | All flashcard objects missing question/answer text"
                ).strip(" |")
            if self._last_flashcard_error:
                errors.append(self._last_flashcard_error)
        if errors:
            self._last_flashcard_error = " | ".join(errors)[:500]
        return []
    
    async def _generate_flashcards_with_openai(self, text: str, count: int) -> List[Dict[str, Any]]:
        """Generate flashcards using OpenAI chat completions (json_object)."""
        if not self.openai_client:
            return []
        prompt = f"""
        Generate {count} high-quality flashcards from the following study material.
        Create diverse flashcard types: definitions, concept explanations, problem-solving, and true/false.
        
        For each flashcard object in the "flashcards" array, include:
        - question: Clear, concise question
        - answer: Detailed, accurate answer
        - type: One of ['definition', 'concept', 'problem_solving', 'true_false']
        - difficulty: One of ['easy', 'medium', 'hard']
        - importance_score: 1-10 rating
        - mnemonic: Optional memory aid suggestion
        
        Text:
        {text[:4000]}
        
        You MUST return a single JSON object with exactly one top-level key, "flashcards",
        whose value is the array of flashcard objects. No other top-level keys. No markdown.
        """

        configured = self.openai_model
        fallbacks = []
        for m in ("gpt-4o-mini", "gpt-4o", "gpt-4-turbo"):
            if m != configured and m not in fallbacks:
                fallbacks.append(m)
        models_to_try = [configured] + fallbacks

        last_err: Optional[Exception] = None
        messages = [
            {
                "role": "system",
                "content": "You are an expert at creating educational flashcards that help students learn effectively.",
            },
            {"role": "user", "content": prompt},
        ]
        for model in models_to_try:
            for use_json_object in (True, False):
                try:
                    kwargs = dict(
                        model=model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=4096,
                    )
                    if use_json_object:
                        kwargs["response_format"] = {"type": "json_object"}
                    response = self.openai_client.chat.completions.create(**kwargs)
                    content = response.choices[0].message.content
                    if not content:
                        raise ValueError("empty completion content")
                    result = _parse_llm_json(content)
                    cards = _flashcard_list_from_parsed(result)
                    if cards:
                        return cards
                    last_err = ValueError(
                        f"OpenAI model {model} (json_object={use_json_object}) returned no flashcard objects"
                    )
                except Exception as e:
                    last_err = e
                    logger.warning(
                        "OpenAI flashcards failed model=%s json_object=%s: %s",
                        model,
                        use_json_object,
                        e,
                        exc_info=False,
                    )

        self._last_flashcard_error = f"OpenAI: {last_err}"[:400] if last_err else "OpenAI: unknown error"
        return []
    
    async def _generate_flashcards_with_gemini(self, text: str, count: int) -> List[Dict[str, Any]]:
        """Generate flashcards using Google Gemini (fast, cost-efficient)"""
        prompt = f"""
        Generate {count} high-quality flashcards from the following study material.
        Create diverse flashcard types: definitions, concept explanations, problem-solving, and true/false.
        
        For each flashcard object in the "flashcards" array, include:
        - question: Clear, concise question
        - answer: Detailed, accurate answer
        - type: One of ['definition', 'concept', 'problem_solving', 'true_false']
        - difficulty: One of ['easy', 'medium', 'hard']
        - importance_score: 1-10 rating
        - mnemonic: Optional memory aid suggestion
        
        Text:
        {text[:4000]}
        
        Return valid JSON only: a single object {{"flashcards": [ ... ]}} with no markdown fences.
        """
        
        try:
            gen_cfg = None
            try:
                gen_cfg = genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                )
            except Exception:
                pass
            response = (
                self.gemini_model.generate_content(prompt, generation_config=gen_cfg)
                if gen_cfg
                else self.gemini_model.generate_content(prompt)
            )
            raw = _gemini_aggregate_text(response)
            if not raw:
                block = getattr(getattr(response, "prompt_feedback", None), "block_reason", None)
                self._last_flashcard_error = f"Gemini: empty response (block_reason={block})"[:400]
                return []
            result = _parse_llm_json(raw)
            cards = _flashcard_list_from_parsed(result)
            if cards:
                return cards
            self._last_flashcard_error = "Gemini: parsed JSON but no flashcard list found"
            return []
        except Exception as e:
            logger.warning("Gemini flashcards failed: %s", e, exc_info=True)
            self._last_flashcard_error = f"Gemini: {e}"[:400]
            return []
    
    async def generate_practice_questions(
        self, 
        text: str, 
        question_type: str = "mcq", 
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """Generate practice questions using GPT-4 Turbo"""
        if not self.openai_client:
            return []
        prompt = f"""
        Generate {count} {question_type} practice exam questions from the following study material.
        Focus on topics likely to appear on exams. Predict exam-relevant questions.
        
        For each question provide:
        - question_text: The question
        - correct_answer: The correct answer
        - options: For MCQ, provide 4 options as array
        - explanation: Brief explanation of the answer
        - difficulty: One of ['easy', 'medium', 'hard']
        - predicted_exam_relevance: 0.0-1.0 score
        
        Text:
        {text[:4000]}
        
        Return JSON array with questions, no additional text.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at creating exam-style practice questions that predict what will be tested."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result.get('questions', []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        except Exception as e:
            print(f"Error generating practice questions: {e}")
            return []
    
    async def generate_visual_description(
        self, 
        concept: str, 
        flashcard_type: str
    ) -> str:
        """Generate visual description using GPT-4 Turbo"""
        if not self.openai_client:
            return ""
        prompt = f"""
        Create a visual description for a memory aid for this concept:
        Concept: {concept}
        Type: {flashcard_type}
        
        Suggest what visual elements (diagrams, charts, mind maps, icons) would help remember this concept.
        Return a brief description suitable for image generation.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at creating visual memory aids for learning."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating visual description: {e}")
            return ""
    
    async def analyze_difficulty(self, user_responses: List[Dict[str, Any]], flashcard_id: int) -> Dict[str, Any]:
        """Analyze user performance to determine optimal difficulty level"""
        if not self.openai_client:
            return {
                "current_difficulty": "medium",
                "recommended_difficulty": "medium",
                "knowledge_gaps": [],
                "mistake_patterns": [],
                "mastery_score": 50.0
            }
        prompt = f"""
        Analyze the following user performance data and determine:
        1. Current difficulty level (easy, medium, hard)
        2. Recommended next difficulty
        3. Knowledge gaps identified
        4. Mistake patterns

        User Responses:
        {str(user_responses)[:2000]}

        Return JSON with:
        - current_difficulty: easy/medium/hard
        - recommended_difficulty: easy/medium/hard
        - knowledge_gaps: array of concepts
        - mistake_patterns: array of common mistakes
        - mastery_score: 0-100
        """
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing learning patterns and adapting difficulty levels."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            import json
            result = json.loads(response.choices[0].message.content)
            return result if isinstance(result, dict) else {}
        except Exception as e:
            print(f"Error analyzing difficulty: {e}")
            return {
                "current_difficulty": "medium",
                "recommended_difficulty": "medium",
                "knowledge_gaps": [],
                "mistake_patterns": [],
                "mastery_score": 50.0
            }

    async def chunk_content(self, text: str) -> List[Dict[str, str]]:
        """
        Break content into optimal learning chunks
        Uses Claude for very long documents due to better context handling
        """
        if len(text) > 8000 and self.claude_client:
            return await self._chunk_content_with_claude(text)
        
        return await self._chunk_content_with_openai(text)
    
    async def _chunk_content_with_openai(self, text: str) -> List[Dict[str, str]]:
        """Chunk content using GPT-4 Turbo"""
        if not self.openai_client:
            return []
        prompt = f"""
        Break the following study material into optimal learning chunks.
        Each chunk should be:
        - Focused on a single topic or concept
        - Not too large (max 500 words)
        - Logically grouped
        - Include related concepts together
        
        Text:
        {text[:6000]}
        
        Return JSON array with chunks, each containing:
        - title: Topic/title of chunk
        - content: The chunk text
        - related_concepts: Array of related concept names
        
        Return only valid JSON array.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at organizing study materials into optimal learning chunks."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result.get('chunks', []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        except Exception as e:
            print(f"Error chunking content: {e}")
            return [{"title": "Content", "content": text, "related_concepts": []}]
    
    async def _chunk_content_with_claude(self, text: str) -> List[Dict[str, str]]:
        """Chunk content using Claude (better for long documents)"""
        prompt = f"""
        Break the following study material into optimal learning chunks.
        Each chunk should be:
        - Focused on a single topic or concept
        - Not too large (max 500 words)
        - Logically grouped
        - Include related concepts together
        
        Text:
        {text[:100000]}  # Claude can handle much longer text
        
        Return JSON array with chunks, each containing:
        - title: Topic/title of chunk
        - content: The chunk text
        - related_concepts: Array of related concept names
        
        Return only valid JSON array.
        """
        
        try:
            message = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.5,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            import json
            result = json.loads(message.content[0].text)
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error chunking content with Claude: {e}")
            return [{"title": "Content", "content": text, "related_concepts": []}]

    async def generate_concept_map(self, concepts: List[str], topic: str) -> Dict[str, Any]:
        """Generate a concept map showing relationships between concepts"""
        if not self.openai_client:
            return {"nodes": [], "edges": [], "central_concept": topic}
        prompt = f"""
        Create a concept map for the topic: {topic}
        Concepts to include: {', '.join(concepts[:50])}
        Return JSON with: nodes (array of {{id, label, type, description}}),
        edges (array of {{source, target, relationship, strength}}),
        central_concept (main concept). Return only valid JSON.
        """
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at creating concept maps. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            import json
            result = json.loads(response.choices[0].message.content)
            return result if isinstance(result, dict) else {"nodes": [], "edges": [], "central_concept": topic}
        except Exception as e:
            print(f"Error generating concept map: {e}")
            return {"nodes": [], "edges": [], "central_concept": topic}

    async def suggest_adaptive_path(self, user_id: int, topic_id: int, performance_data: Dict[str, Any]) -> List[int]:
        """Suggest optimal learning path based on user performance"""
        if not self.openai_client:
            return performance_data.get("flashcard_ids", [])
        prompt = f"""
        Based on this performance data, suggest an optimal learning sequence of flashcard IDs.
        Performance Data: {str(performance_data)[:2000]}
        Return JSON array of flashcard IDs in recommended order. Only IDs, no other text.
        """
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at personalized learning paths. Return only a JSON array of IDs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            import json
            result = json.loads(response.choices[0].message.content)
            flashcard_ids = performance_data.get("flashcard_ids", [])
            ids = result if isinstance(result, list) else (result.get("path") or result.get("ids") or []) if isinstance(result, dict) else []
            try:
                valid = [int(x) for x in ids]
                return [i for i in valid if i in flashcard_ids] if valid else flashcard_ids
            except (ValueError, TypeError):
                return flashcard_ids
        except Exception as e:
            print(f"Error suggesting adaptive path: {e}")
            return performance_data.get("flashcard_ids", [])

    async def generate_questions_from_notes(self, notes_text: str, count: int = 10) -> List[Dict[str, Any]]:
        """Generate questions directly from notes/text"""
        if not self.openai_client:
            return []
        prompt = f"""
        Generate {count} study questions from these notes. Return JSON array with objects containing:
        question_text, correct_answer, question_type (mcq/short_answer), difficulty, options (for mcq), explanation.
        Notes: {notes_text[:4000]}
        Return only valid JSON array.
        """
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at creating study questions. Return only valid JSON array."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )
            import json
            result = json.loads(response.choices[0].message.content)
            questions = result.get("questions", result) if isinstance(result, dict) else result
            return questions if isinstance(questions, list) else []
        except Exception as e:
            print(f"Error generating questions from notes: {e}")
            return []

