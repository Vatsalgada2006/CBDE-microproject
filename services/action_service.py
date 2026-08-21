import logging
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import nltk
from nltk.tokenize import sent_tokenize

logger = logging.getLogger(__name__)

# Download necessary NLTK data if not present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class ActionService:
    def __init__(self):
        # Patterns for deadlines and dates
        self.date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY or DD/MM/YYYY
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',    # YYYY/MM/DD
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',  # Month DD, YYYY
            r'\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b',   # DD Month YYYY
        ]
        # Compile the patterns
        self.date_regex = re.compile('|'.join(self.date_patterns), re.IGNORECASE)

        # Patterns for task indicators
        self.task_patterns = [
            r'\b(?:need to|must|should|shall|required to|have to|ought to)\b',
            r'\b(?:task|action|item|todo|to-do)\b',
            r'\b(?:submit|provide|deliver|complete|finish)\b',
        ]
        self.task_regex = re.compile('|'.join(self.task_patterns), re.IGNORECASE)

    def extract_actions(self, text: str) -> List[Dict]:
        """
        Extract actions (tasks, deadlines) from text.
        Returns a list of dictionaries with keys:
        - action: description of the action
        - deadline: extracted deadline (if any) as a string
        - confidence: float between 0 and 1
        - type: 'task' or 'deadline'
        """
        if not text:
            return []

        actions = []
        sentences = sent_tokenize(text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check for task indicators
            task_match = self.task_regex.search(sentence)
            if task_match:
                # Extract a plausible action phrase around the match
                # We'll take the whole sentence as the action for simplicity
                action_text = sentence
                # Look for a date in the sentence
                date_match = self.date_regex.search(sentence)
                deadline = date_match.group(0) if date_match else None
                confidence = 0.8 if deadline else 0.6
                actions.append({
                    'action': action_text,
                    'deadline': deadline,
                    'confidence': confidence,
                    'type': 'task'
                })
                continue  # Avoid double counting if both task and date patterns are present

            # Check for dates (deadlines)
            date_match = self.date_regex.search(sentence)
            if date_match:
                # Look for task indicators in the sentence to increase confidence
                task_indicator = self.task_regex.search(sentence)
                deadline = date_match.group(0)
                # Try to extract an action phrase: we'll take the sentence and maybe trim
                action_text = sentence
                confidence = 0.7 if task_indicator else 0.5
                actions.append({
                    'action': action_text,
                    'deadline': deadline,
                    'confidence': confidence,
                    'type': 'deadline'
                })

        # If we found multiple actions, we might want to merge or deduplicate
        # For simplicity, we'll return all found actions
        return actions

    def extract_deadlines(self, text: str) -> List[str]:
        """
        Extract all date-like strings from text.
        """
        if not text:
            return []
        return self.date_regex.findall(text)

    def extract_tasks(self, text: str) -> List[str]:
        """
        Extract task-related sentences.
        """
        if not text:
            return []
        sentences = sent_tokenize(text)
        tasks = []
        for sentence in sentences:
            if self.task_regex.search(sentence):
                tasks.append(sentence.strip())
        return tasks