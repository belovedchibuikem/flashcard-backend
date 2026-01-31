"""
Enhanced AI Service with Latest Models for Better Accuracy
Supports GPT-4 Turbo, Claude 3.5 Sonnet, and Gemini 2.5 Flash-Lite
"""

import openai
from typing import List, Dict, Any, Optional
from app.config import settings

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
        # OpenAI (GPT-4 Turbo/GPT-4o)
        self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.openai_model = getattr(settings, 'OPENAI_MODEL', 'gpt-4-turbo-preview')  # or 'gpt-4o'
        
        # Claude (for long documents)
        if CLAUDE_AVAILABLE and hasattr(settings, 'ANTHROPIC_API_KEY'):
            self.claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        else:
            self.claude_client = None
        
        # Gemini (for fast/cost-efficient tasks)
        if GEMINI_AVAILABLE and hasattr(settings, 'GOOGLE_GEMINI_API_KEY'):
            genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel('gemini-2.5-flash-lite')
        else:
            self.gemini_model = None
    
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
        Generate flashcards with model selection
        Uses Gemini Flash-Lite for fast generation, GPT-4 Turbo for quality
        """
        if use_fast_model and self.gemini_model:
            return await self._generate_flashcards_with_gemini(text, count)
        
        return await self._generate_flashcards_with_openai(text, count)
    
    async def _generate_flashcards_with_openai(self, text: str, count: int) -> List[Dict[str, Any]]:
        """Generate flashcards using GPT-4 Turbo"""
        prompt = f"""
        Generate {count} high-quality flashcards from the following study material.
        Create diverse flashcard types: definitions, concept explanations, problem-solving, and true/false.
        
        For each flashcard, provide:
        - question: Clear, concise question
        - answer: Detailed, accurate answer
        - type: One of ['definition', 'concept', 'problem_solving', 'true_false']
        - difficulty: One of ['easy', 'medium', 'hard']
        - importance_score: 1-10 rating
        - mnemonic: Optional memory aid suggestion
        
        Text:
        {text[:4000]}
        
        Return JSON array with flashcards, no additional text.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at creating educational flashcards that help students learn effectively."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result.get('flashcards', []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        except Exception as e:
            print(f"Error generating flashcards with OpenAI: {e}")
            return []
    
    async def _generate_flashcards_with_gemini(self, text: str, count: int) -> List[Dict[str, Any]]:
        """Generate flashcards using Gemini 2.5 Flash-Lite (faster, cost-efficient)"""
        prompt = f"""
        Generate {count} high-quality flashcards from the following study material.
        Create diverse flashcard types: definitions, concept explanations, problem-solving, and true/false.
        
        For each flashcard, provide:
        - question: Clear, concise question
        - answer: Detailed, accurate answer
        - type: One of ['definition', 'concept', 'problem_solving', 'true_false']
        - difficulty: One of ['easy', 'medium', 'hard']
        - importance_score: 1-10 rating
        - mnemonic: Optional memory aid suggestion
        
        Text:
        {text[:4000]}
        
        Return JSON array with flashcards, no additional text.
        """
        
        try:
            response = self.gemini_model.generate_content(prompt)
            import json
            result = json.loads(response.text)
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error generating flashcards with Gemini: {e}")
            return []
    
    async def generate_practice_questions(
        self, 
        text: str, 
        question_type: str = "mcq", 
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """Generate practice questions using GPT-4 Turbo"""
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

