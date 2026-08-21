<parameter=content>
import logging
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import hashlib
import os

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the embedding service with a sentence transformer model.
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
        # Simple cache: map text hash to embedding
        self.embedding_cache = {}

    def _load_model(self):
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.model = None

    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Get embedding for a text string.
        Returns None if the model is not available.
        """
        if self.model is None:
            logger.warning("Embedding model not available")
            return None

        # Check cache
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        if text_hash in self.embedding_cache:
            return self.embedding_cache[text_hash]

        try:
            # Encode the text
            embedding = self.model.encode(text, convert_to_numpy=True)
            # Cache the embedding
            self.embedding_cache[text_hash] = embedding
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def get_embeddings(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """
        Get embeddings for a list of text strings.
        """
        if self.model is None:
            logger.warning("Embedding model not available")
            return [None] * len(texts)

        embeddings = []
        for text in texts:
            emb = self.get_embedding(text)
            embeddings.append(emb)
        return embeddings

    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        """
        if emb1 is None or emb2 is None:
            return 0.0
        # Normalize the vectors
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return np.dot(emb1, emb2) / (norm1 * norm2)