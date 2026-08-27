import os
import logging
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import the Google Generative AI client
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    logger.warning("google-generativeai package not installed. LLM service will be unavailable.")
    GENAI_AVAILABLE = False

class LLMService:
    def __init__(self):
        """Initialize the LLM service with Google Gemini API."""
        self.api_key = os.environ.get('GEMINI_API_KEY')
        self.model_name = 'gemini-1.5-flash'  # Fast and efficient for our use case
        self.model = None

        if GENAI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
                logger.info(f"LLM service initialized with model {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize LLM service: {e}")
                self.model = None
        else:
            if not GENAI_AVAILABLE:
                logger.warning("LLM service not available due to missing google-generativeai package.")
            if not self.api_key:
                logger.warning("LLM service not available due to missing GEMINI_API_KEY environment variable.")

    def is_available(self) -> bool:
        """Check if the LLM service is available and configured."""
        return self.model is not None

    def generate_summary(self, text: str, max_length: int = 200) -> str:
        """
        Generate an abstractive summary of the provided text, constrained to be based only on the text.
        Returns the summary string.
        If LLM service is not available, returns an empty string or a fallback message.
        """
        if not self.is_available():
            logger.warning("LLM service not available for summarization.")
            return ""

        if not text or not text.strip():
            return ""

        # Truncate text if too long to avoid exceeding token limits (rough estimate)
        # Gemini 1.5 Flash has a large context window, but we'll be safe.
        max_chars = 10000  # Roughly 2500 tokens
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
            logger.info(f"Text truncated to {max_chars} characters for summarization.")

        prompt = f"""You are an expert summarizer. Your task is to generate a concise summary of the provided text.
        The summary must be based solely on the information in the text. Do not add external knowledge or facts not present in the text.
        If the text is empty or contains no meaningful information, return an empty string.
        Keep the summary under {max_length} characters.

        Text to summarize:
        {text}

        Summary:"""

        try:
            # Add a small delay to avoid rate limiting (though we have generous free tier)
            time.sleep(0.1)
            response = self.model.generate_content(prompt)
            summary = response.text.strip()
            # Ensure summary is not too long
            if len(summary) > max_length:
                summary = summary[:max_length].rsplit(' ', 1)[0] + "..."
            logger.info(f"Generated summary of length {len(summary)}")
            return summary
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            # Fallback to empty string or a simple truncation?
            return ""

    def answer_question(self, context: str, question: str) -> Dict[str, any]:
        """
        Answer a question based solely on the provided context.
        Returns a dictionary with keys:
        - 'answer': the answer string
        - 'confidence': a float between 0 and 1 (we'll use a fixed high confidence if answered)
        - 'context_used': the context chunks that were used (for citation)
        If the answer cannot be determined from the context, returns an answer indicating so.
        If LLM service is not available, returns a fallback response.
        """
        if not self.is_available():
            logger.warning("LLM service not available for question answering.")
            return {
                'answer': "LLM service is not available to answer questions.",
                'confidence': 0.0,
                'context_used': []
            }

        if not context or not context.strip():
            return {
                'answer': "No context provided to answer the question.",
                'confidence': 0.0,
                'context_used': []
            }

        if not question or not question.strip():
            return {
                'answer': "No question provided.",
                'confidence': 0.0,
                'context_used': []
            }

        # Truncate context if too long
        max_chars = 15000  # Roughly 3500 tokens
        if len(context) > max_chars:
            context = context[:max_chars] + "..."
            logger.info(f"Context truncated to {max_chars} characters for QA.")

        prompt = f"""You are an expert question-answering system. Your task is to answer the question based solely on the provided context.
        You must not use any external knowledge or facts not present in the context.
        If the question cannot be answered based on the context, you must say so clearly (e.g., "The answer cannot be determined from the provided context.").
        Do not speculate or add information beyond what is in the context.

        Context:
        {context}

        Question:
        {question}

        Answer:"""

        try:
            time.sleep(0.1)  # Small delay to avoid rate limiting
            response = self.model.generate_content(prompt)
            answer = response.text.strip()

            # Determine if the answer indicates inability to answer
            # We'll use a simple heuristic: if the answer contains certain phrases, we consider it as unable to answer.
            unable_to_answer_phrases = [
                "cannot be determined",
                "not enough information",
                "insufficient information",
                "cannot answer",
                "not specified",
                "does not contain",
                "not mentioned",
                "not in the context",
                "not provided"
            ]
            answer_lower = answer.lower()
            unable_to_answer = any(phrase in answer_lower for phrase in unable_to_answer_phrases)

            confidence = 0.9 if not unable_to_answer else 0.3  # Lower confidence if it says it can't answer

            # For simplicity, we'll return the whole context as used (since we didn't do chunking here)
            # In a more advanced version, we would return the specific chunks used.
            context_used = [context] if not unable_to_answer else []

            logger.info(f"Generated answer for question: {question[:50]}... (confidence: {confidence})")
            return {
                'answer': answer,
                'confidence': confidence,
                'context_used': context_used
            }
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return {
                'answer': "Error processing the question.",
                'confidence': 0.0,
                'context_used': []
            }

    def extract_key_points(self, text: str, num_points: int = 5) -> List[str]:
        """
        Extract key bullet points from the text using the LLM.
        Returns a list of strings (each string is a bullet point).
        """
        if not self.is_available():
            logger.warning("LLM service not available for key point extraction.")
            return []

        if not text or not text.strip():
            return []

        # Truncate text if too long
        max_chars = 10000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
            logger.info(f"Text truncated to {max_chars} characters for key point extraction.")

        prompt = f"""You are an expert at extracting key information from text.
        Extract the {num_points} most important points from the provided text as a concise bullet list.
        Each point should be a short sentence or phrase that captures a key fact, idea, or finding from the text.
        Base your points solely on the information in the text; do not add external knowledge.
        If the text contains fewer than {num_points} meaningful points, return as many as you can find.
        Format your response as a list where each line starts with a dash (-) followed by the point.

        Text:
        {text}

        Key points:"""

        try:
            time.sleep(0.1)
            response = self.model.generate_content(prompt)
            # Parse the response to extract bullet points
            points = []
            for line in response.text.split('\n'):
                line = line.strip()
                if line.startswith('-'):
                    point = line[1:].strip()
                    if point:
                        points.append(point)
                # Also handle lines that start with numbers or other bullet styles? We'll keep simple.
            # If we didn't get enough points, fallback to splitting by newline and cleaning
            if len(points) < 2:
                # Alternative: split by sentences and take first few?
                pass
            logger.info(f"Extracted {len(points)} key points")
            return points[:num_points]
        except Exception as e:
            logger.error(f"Error extracting key points: {e}")
            return []