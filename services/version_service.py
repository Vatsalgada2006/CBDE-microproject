import logging
import re
from typing import List, Tuple, Optional
from datetime import datetime
from models.document import Document
import numpy as np

logger = logging.getLogger(__name__)

class VersionService:
    def __init__(self, similarity_threshold: float = 0.75):
        """
        Initialize the version service.
        :param similarity_threshold: Threshold for considering version similarity
        """
        self.similarity_threshold = similarity_threshold
        # Common version indicators in filenames
        self.version_patterns = [
            r'_v\d+',          # _v1, _v2, etc.
            r'_rev\d+',        # _rev1, _rev2
            r'_final',         # _final
            r'_edit',          # _edit
            r'_\d{4}',         # _2023, _2024 (year)
            r'\((\d+)\)',      # (1), (2)
            r'-v\d+',          # -v1, -v2
        ]

    def _extract_version_indicator(self, filename: str) -> Optional[str]:
        """
        Extract a version indicator from the filename.
        Returns a normalized version string or None.
        """
        if not filename:
            return None
        # Remove file extension
        name = filename.lower()
        if '.' in name:
            name = name.rsplit('.', 1)[0]

        # Look for patterns
        for pattern in self.version_patterns:
            match = re.search(pattern, name)
            if match:
                return match.group(0)
        return None

    def _version_indicator_similarity(self, ind1: Optional[str], ind2: Optional[str]) -> float:
        """
        Compute similarity between two version indicators.
        Simple approach: if both are None, return 0. If one is None, return 0.
        If both are present, compare strings (could be improved).
        """
        if ind1 is None or ind2 is None:
            return 0.0
        if ind1 == ind2:
            return 1.0
        # Simple string similarity (could use Levenshtein distance)
        # For now, we'll just return 0.5 if both are present but different
        return 0.5

    def find_possible_versions(self, document: Document, existing_documents: List[Document]) -> List[Tuple[Document, float, str]]:
        """
        Find possible version relationships.
        Returns a list of tuples (related_document, confidence, version_type) where version_type is 'possible_previous' or 'possible_newer'.
        We determine which is older based on CreatedAt timestamp.
        """
        if document.embedding is None:
            return []
        results = []
        doc_embedding = np.array(document.embedding)
        doc_time = document.CreatedAt
        doc_version_ind = self._extract_version_indicator(document.filename)

        for doc in existing_documents:
            if doc.doc_id == document.doc_id:
                continue  # Skip self
            if doc.embedding is None:
                continue

            # Compute content similarity
            other_embedding = np.array(doc.embedding)
            content_similarity = np.dot(doc_embedding, other_embedding) / (
                np.linalg.norm(doc_embedding) * np.linalg.norm(other_embedding)
            )

            # Compute version indicator similarity
            other_version_ind = self._extract_version_indicator(doc.filename)
            version_sim = self._version_indicator_similarity(doc_version_ind, other_version_ind)

            # Compute time difference (normalized)
            time_diff = abs((doc_time - doc.CreatedAt).total_seconds())
            # Normalize time difference: assume that versions are likely within a year (31536000 seconds)
            time_sim = max(0, 1 - (time_diff / 31536000))  # 1 if same time, 0 if a year apart

            # Combine signals: weighted average
            # Weights: content 0.5, version indicator 0.3, time 0.2
            combined_score = 0.5 * content_similarity + 0.3 * version_sim + 0.2 * time_sim

            if combined_score >= self.similarity_threshold:
                # Determine which is older
                if doc_time < doc.CreatedAt:
                    # doc is older than the existing document
                    version_type = 'possible_previous'
                else:
                    version_type = 'possible_newer'
                results.append((doc, combined_score, version_type))
                logger.info(f"Possible version found: {document.doc_id} -> {doc.doc_id} (type: {version_type}, score: {combined_score})")

        return results