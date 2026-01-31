"""
AI Service for content analysis and flashcard generation
"""

import openai
from typing import List, Dict, Any
from app.config import settings

# Initialize OpenAI client
openai.api_key = settings.OPENAI_API_KEY


class AIService:
    """Service for AI-powered content analysis and generation"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def extract_key_concepts(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract key concepts, definitions, and important facts from text
        """
        prompt = f"""
        Analyze the following study material and extract key concepts, definitions, formulas, and important facts.
        Focus on exam-relevant content. Return a JSON array with objects containing:
        - concept: the key concept name
        - definition: brief definition or explanation
        - importance: score from 1-10
        - type: one of ['definition', 'formula', 'concept', 'fact', 'process']
        
        Text:
        {text[:4000]}  # Limit to avoid token limits
        
        Return only valid JSON array, no additional text.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing study materials and extracting key concepts for exam preparation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error extracting concepts: {e}")
            return []
    
    async def generate_flashcards(self, text: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        Generate flashcards from study material text
        """
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
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at creating educational flashcards that help students learn effectively."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=3000
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error generating flashcards: {e}")
            return []
    
    async def generate_practice_questions(self, text: str, question_type: str = "mcq", count: int = 5) -> List[Dict[str, Any]]:
        """
        Generate practice exam questions from study material
        """
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
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at creating exam-style practice questions that predict what will be tested."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=3000
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error generating practice questions: {e}")
            return []
    
    async def generate_visual_description(self, concept: str, flashcard_type: str) -> str:
        """
        Generate description for visual memory aid
        """
        prompt = f"""
        Create a visual description for a memory aid for this concept:
        Concept: {concept}
        Type: {flashcard_type}
        
        Suggest what visual elements (diagrams, charts, mind maps, icons) would help remember this concept.
        Return a brief description suitable for image generation.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
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
        """
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
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at organizing study materials into optimal learning chunks."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=4000
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error chunking content: {e}")
            return [{"title": "Content", "content": text, "related_concepts": []}]
    
    async def analyze_difficulty(self, user_responses: List[Dict[str, Any]], flashcard_id: int) -> Dict[str, Any]:
        """
        Analyze user performance to determine optimal difficulty level
        """
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
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing learning patterns and adapting difficulty levels."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result if isinstance(result, dict) else {}
        except Exception as e:
            print(f"Error analyzing difficulty: {e}")
            return {}
    
    async def generate_concept_map(self, concepts: List[str], topic: str) -> Dict[str, Any]:
        """
        Generate a concept map showing relationships between concepts
        """
        prompt = f"""
        Create a concept map for the topic: {topic}
        
        Concepts to include:
        {', '.join(concepts)}
        
        Return JSON with:
        - nodes: array of {{id, label, type, description}}
        - edges: array of {{source, target, relationship, strength}}
        - central_concept: the main concept
        
        Show relationships, hierarchies, and connections between concepts.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at creating concept maps and knowledge graphs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=2000
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result if isinstance(result, dict) else {"nodes": [], "edges": []}
        except Exception as e:
            print(f"Error generating concept map: {e}")
            return {"nodes": [], "edges": []}
    
    async def suggest_adaptive_path(self, user_id: int, topic_id: int, performance_data: Dict[str, Any]) -> List[int]:
        """
        Suggest optimal learning path based on user performance
        """
        prompt = f"""
        Based on the following user performance data, suggest an optimal learning sequence.
        Consider:
        - Weak areas that need more practice
        - Prerequisites that should be learned first
        - Strong areas that can be reviewed less
        - Logical learning progression
        
        Performance Data:
        {str(performance_data)[:2000]}
        
        Return JSON array of concept/flashcard IDs in recommended order.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at creating personalized learning paths."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=1000
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error suggesting adaptive path: {e}")
            return []
    
    async def generate_questions_from_notes(self, notes_text: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        Generate questions directly from handwritten notes or text
        """
        prompt = f"""
        Generate {count} high-quality study questions from the following notes.
        Create questions that test understanding of the key concepts mentioned.
        
        Notes:
        {notes_text[:4000]}
        
        Return JSON array with questions, each containing:
        - question_text: The question
        - correct_answer: The answer
        - question_type: mcq/short_answer/essay
        - difficulty: easy/medium/hard
        - explanation: Why this question is important
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at creating study questions from notes and text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=3000
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error generating questions from notes: {e}")
            return []
    
    async def predict_exam_score(self, performance_history: List[Dict[str, Any]], exam_topic: str) -> Dict[str, Any]:
        """
        Predict exam score based on performance history
        """
        prompt = f"""
        Predict the user's likely exam score based on their performance history.
        
        Performance History:
        {str(performance_history)[:2000]}
        
        Exam Topic: {exam_topic}
        
        Return JSON with:
        - predicted_score: 0-100 percentage
        - confidence: 0-1 confidence level
        - weak_areas: array of topics to focus on
        - recommended_study_time: hours needed
        - readiness_level: not_ready/almost_ready/ready/excellent
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at predicting exam performance based on study data."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result if isinstance(result, dict) else {}
        except Exception as e:
            print(f"Error predicting exam score: {e}")
            return {}


