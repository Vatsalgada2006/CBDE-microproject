import logging
from typing import List, Tuple, Optional
from models.document import Document
import numpy as np

logger = logging.getLogger(__name__)

class DuplicateService:
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize the duplicate service.
        :param similarity_threshold: Threshold for considering near duplicates (cosine similarity)
        """
        self.similarity_threshold = similarity_threshold

    def find_exact_duplicates(self, document: Document, existing_documents: List[Document]) -> List[Tuple[Document, float]]:
        """
        Find exact duplicates based on file hash.
        Returns a list of tuples (duplicate_document, confidence) where confidence is 1.0 for exact hash match.
        """
        duplicates = []
        if document.hash is None:
            return duplicates
        for doc in existing_documents:
            if doc.doc_id == document.doc_id:
                continue  # Skip self
            if doc.hash == document.hash:
                duplicates.append((doc, 1.0))
                logger.info(f"Exact duplicate found: {document.doc_id} matches {doc.doc_id}")
        return duplicates

    def find_near_duplicates(self, document: Document, existing_documents: List[Document]) -> List[Tuple[Document, float]]:
        """
        Find near duplicates based on embedding similarity.
        Returns a list of tuples (duplicate_document, similarity_score) for documents above the threshold.
        """
        if document.embedding is None:
            return []
        duplicates = []
        doc_embedding = np.array(document.embedding)
        for doc in existing_documents:
            if doc.doc_id == document.doc_id:
                continue  # Skip self
            if doc.embedding is None:
                continue
            other_embedding = np.array(doc.embedding)
            similarity = np.dot(doc_embedding, other_embedding) / (
                np.linalg.norm(doc_embedding) * np.linalg.norm(other_embedding)
            )
            if similarity >= self.similarity_threshold:
                duplicates.append((doc, float(similarity)))
                logger.info(f"Near duplicate found: {document.doc_id} similar to {doc.doc_id} with score {similarity}")
        return duplicates

    def find_duplicates(self, document: Document, existing_documents: List[Document]) -> List[Tuple[Document, float, str]]:
        """
        Find both exact and near duplicates.
        Returns a list of tuples (document, confidence, type) where type is 'exact' or 'near'.
        """
        results = []
        exact_dups = self.find_exact_duplicates(document, existing_documents)
        for doc, conf in exact_dups:
            results.append((doc, conf, 'exact'))
        near_dups = self.find_near_duplicates(document, existing_documents)
        for doc, conf in near_dups:
            results.append((doc, conf, 'near'))
        return results