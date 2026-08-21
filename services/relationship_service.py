import logging
import re
from typing import List, Tuple, Optional, Set
from datetime import datetime
from models.document import Document
import numpy as np
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

logger = logging.getLogger(__name__)

# Download necessary NLTK data if not present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class RelationshipService:
    def __init__(self,
                 semantic_weight: float = 0.4,
                 filename_weight: float = 0.2,
                 entity_weight: float = 0.2,
                 keyword_weight: float = 0.1,
                 folder_weight: float = 0.05,
                 temporal_weight: float = 0.05):
        """
        Initialize the relationship service with weights for different signals.
        """
        self.semantic_weight = semantic_weight
        self.filename_weight = filename_weight
        self.entity_weight = entity_weight
        self.keyword_weight = keyword_weight
        self.folder_weight = folder_weight
        self.temporal_weight = temporal_weight
        self.stop_words = set(stopwords.words('english'))

    def _compute_semantic_similarity(self, doc1: Document, doc2: Document) -> float:
        """
        Compute semantic similarity based on embeddings.
        """
        if doc1.embedding is None or doc2.embedding is None:
            return 0.0
        emb1 = np.array(doc1.embedding)
        emb2 = np.array(doc2.embedding)
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

    def _compute_filename_similarity(self, doc1: Document, doc2: Document) -> float:
        """
        Compute similarity between filenames (without extension).
        Simple approach: Jaccard similarity of character 3-grams.
        """
        def get_grams(s):
            s = s.lower()
            # Remove file extension
            if '.' in s:
                s = s.rsplit('.', 1)[0]
            # Generate 3-grams
            grams = set()
            for i in range(len(s) - 2):
                grams.add(s[i:i+3])
            return grams

        set1 = get_grams(doc1.filename or "")
        set2 = get_grams(doc2.filename or "")
        if not set1 and not set2:
            return 0.0
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        if union == 0:
            return 0.0
        return intersection / union

    def _extract_entities(self, text: str) -> Set[str]:
        """
        Extract simple entities: capitalized words and nouns (simplified).
        We'll tokenize and keep words that are capitalized and not stop words.
        This is a very basic entity extraction.
        """
        if not text:
            return set()
        tokens = word_tokenize(text)
        entities = set()
        for token in tokens:
            # Keep words that are capitalized and not stop words and are alphabetic
            if token.istitle() and token.isalpha() and token.lower() not in self.stop_words:
                entities.add(token.lower())
        return entities

    def _compute_entity_similarity(self, doc1: Document, doc2: Document) -> float:
        """
        Compute similarity based on shared entities.
        We'll need to extract entities from the text. For now, we'll use a placeholder
        and later we can integrate with extraction service to get the text.
        Since we don't have the text stored, we'll skip for now and return 0.
        In a full implementation, we would store the extracted text or entities.
        """
        # Placeholder: we don't have the text stored in the document model
        # We'll return 0 for now, but in a real system we would compute from extracted text
        return 0.0

    def _compute_keyword_similarity(self, doc1: Document, doc2: Document) -> float:
        """
        Compute similarity based on keyword overlap (TF-IDF like, but simple word overlap).
        Again, we need the text. We'll skip for now and return 0.
        """
        return 0.0

    def _compute_folder_similarity(self, doc1: Document, doc2: Document) -> float:
        """
        Compute similarity based on folder context.
        If both documents are in the same folder, return 1.0, else 0.0.
        """
        if doc1.folder_id and doc2.folder_id and doc1.folder_id == doc2.folder_id:
            return 1.0
        return 0.0

    def _compute_temporal_similarity(self, doc1: Document, doc2: Document) -> float:
        """
        Compute similarity based on temporal closeness.
        We'll use a decaying function: similarity = exp(-diff_in_days / tau)
        where tau is a time constant (e.g., 30 days).
        """
        if doc1.CreatedAt is None or doc2.CreatedAt is None:
            return 0.0
        diff_seconds = abs((doc1.CreatedAt - doc2.CreatedAt).total_seconds())
        diff_days = diff_seconds / (24 * 3600)
        tau = 30.0  # time constant of 30 days
        similarity = np.exp(-diff_days / tau)
        return similarity

    def compute_relationship(self, doc1: Document, doc2: Document) -> Tuple[float, str]:
        """
        Compute the relationship score between two documents and provide a reason.
        Returns a tuple (score, reason) where score is between 0 and 1.
        """
        # Compute individual similarities
        semantic_sim = self._compute_semantic_similarity(doc1, doc2)
        filename_sim = self._compute_filename_similarity(doc1, doc2)
        entity_sim = self._compute_entity_similarity(doc1, doc2)
        keyword_sim = self._compute_keyword_similarity(doc1, doc2)
        folder_sim = self._compute_folder_similarity(doc1, doc2)
        temporal_sim = self._compute_temporal_similarity(doc1, doc2)

        # Weighted sum
        score = (self.semantic_weight * semantic_sim +
                 self.filename_weight * filename_sim +
                 self.entity_weight * entity_sim +
                 self.keyword_weight * keyword_sim +
                 self.folder_weight * folder_sim +
                 self.temporal_weight * temporal_sim)

        # Generate reason
        reasons = []
        if semantic_sim > 0.7:
            reasons.append("high semantic similarity")
        elif semantic_sim > 0.4:
            reasons.append("moderate semantic similarity")
        if filename_sim > 0.5:
            reasons.append("similar filename")
        if folder_sim > 0.5:
            reasons.append("same folder")
        if temporal_sim > 0.7:
            reasons.append("close in time")
        # Note: entity and keyword similarities are not implemented yet

        if not reasons:
            reason = "low similarity across all signals"
        else:
            reason = ", ".join(reasons)

        return score, reason

    def find_related_documents(self, document: Document, existing_documents: List[Document], threshold: float = 0.6) -> List[Tuple[Document, float, str]]:
        """
        Find documents related to the given document above a threshold.
        Returns a list of tuples (related_document, score, reason).
        """
        related = []
        for doc in existing_documents:
            if doc.doc_id == document.doc_id:
                continue
            score, reason = self.compute_relationship(document, doc)
            if score >= threshold:
                related.append((doc, score, reason))
                logger.info(f"Related document found: {document.doc_id} <-> {doc.doc_id} (score: {score}, reason: {reason})")
        return related