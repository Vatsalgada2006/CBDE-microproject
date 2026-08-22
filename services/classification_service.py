import logging
import re
from typing import List, Tuple, Optional
from models.document import Document

logger = logging.getLogger(__name__)

class ClassificationService:
    def __init__(self):
        # Initialize stop words lazily
        self._stop_words = None
        # Define categories and their associated keywords
        self.categories = {
            'Contract': ['contract', 'agreement', 'party', 'parties', 'obligation', 'liability', 'breach', 'termination', 'effective date', 'governing law'],
            'Invoice': ['invoice', 'bill', 'amount due', 'due date', 'invoice number', 'billing', 'invoice date', 'payment terms', 'line item', 'quantity', 'price', 'tax'],
            'Receipt': ['receipt', 'payment received', 'amount paid', 'transaction', 'method of payment', 'date of payment', 'receipt number', 'paid', 'change', 'tax'],
            'Report': ['report', 'summary', 'findings', 'conclusion', 'analysis', 'overview', 'introduction', 'methodology', 'results', 'discussion', 'references'],
            'Research Paper': ['abstract', 'introduction', 'literature review', 'methodology', 'results', 'discussion', 'conclusion', 'references', 'hypothesis', 'experiment', 'study', 'survey'],
            'Assignment': ['assignment', 'homework', 'due date', 'course', 'instructor', 'student', 'question', 'problem set', 'worksheet', 'exercise'],
            'Presentation': ['presentation', 'slide', 'slideshow', 'powerpoint', 'keynote', 'presentation title', 'agenda', 'objective', 'outline', 'conclusion', 'questions'],
            'Resume': ['resume', 'curriculum vitae', 'work experience', 'education', 'skills', 'objective', 'summary', 'references', 'certifications', 'awards'],
            'Certificate': ['certificate', 'certification', 'awarded', 'completion', 'achievement', 'license', 'accredited', 'authority', 'date of issue', 'expiry date'],
            'Policy': ['policy', 'procedure', 'guideline', 'rule', 'regulation', 'compliance', 'standards', 'protocol', 'policy number', 'effective date', 'review date'],
            'Form': ['form', 'application', 'please fill out', 'fields', 'signature', 'date of birth', 'name', 'address', 'phone number', 'email', 'checkbox', 'radio button'],
        }
        # Default category
        self.default_category = 'Other'

    @property
    def stop_words(self):
        """Lazy load NLTK stop words."""
        if self._stop_words is None:
            try:
                from nltk.corpus import stopwords
                self._stop_words = set(stopwords.words('english'))
            except LookupError:
                # Download necessary NLTK data if not present
                import nltk
                nltk.download('stopwords')
                from nltk.corpus import stopwords
                self._stop_words = set(stopwords.words('english'))
        return self._stop_words

    def _preprocess_text(self, text: str) -> List[str]:
        """
        Tokenize and remove stop words.
        """
        if not text:
            return []
        
        # Lazy load NLTK tokenizer
        try:
            from nltk.tokenize import word_tokenize
        except LookupError:
            # Download necessary NLTK data if not present
            import nltk
            nltk.download('punkt')
            nltk.download('punkt_tab')
            from nltk.tokenize import word_tokenize
        
        tokens = word_tokenize(text.lower())
        # Remove non-alphabetic tokens and stop words
        tokens = [token for token in tokens if token.isalpha() and token not in self.stop_words]
        return tokens

    def classify(self, document: Document, extracted_text: Optional[str] = None) -> Tuple[str, float]:
        """
        Classify the document into one of the predefined categories.
        Returns a tuple (category, confidence).
        Confidence is the normalized score for the winning category.
        """
        # Use extracted text if provided, otherwise fall back to filename
        text_to_classify = extracted_text if extracted_text is not None else document.filename
        if not text_to_classify:
            return self.default_category, 0.0

        tokens = self._preprocess_text(text_to_classify)
        if not tokens:
            return self.default_category, 0.0

        # Score each category
        scores = {}
        for category, keywords in self.categories.items():
            score = 0
            for keyword in keywords:
                # Count how many times the keyword appears in the tokens
                # We'll do a simple substring match for multi-word keywords
                # For simplicity, we'll split the keyword and check if all words are present
                keyword_words = keyword.lower().split()
                # Check if all words in the keyword appear in the tokens (not necessarily consecutive)
                # This is a simple approximation
                all_present = all(word in tokens for word in keyword_words)
                if all_present:
                    score += 1
            # Normalize by the number of keywords in the category
            if len(keywords) > 0:
                scores[category] = score / len(keywords)
            else:
                scores[category] = 0.0

        # Find the category with the highest score
        if not scores:
            return self.default_category, 0.0

        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]

        # If the best score is below a threshold, classify as Other
        threshold = 0.2  # at least 20% of keywords matched
        if best_score < threshold:
            return self.default_category, best_score
        else:
            return best_category, best_score
