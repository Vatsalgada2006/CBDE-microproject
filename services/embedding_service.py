import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self, model_name: str = 'BAAI/bge-small-en-v1.5'):
        self.model_name = model_name
        self.model = None  # Will be loaded on first use

    def _load_model(self):
        """Load the fastembed model lazily to save memory until needed."""
        if self.model is None:
            try:
                from fastembed import TextEmbedding
                logger.info(f"Loading fastembed model: {self.model_name}")
                self.model = TextEmbedding(self.model_name)
            except ImportError:
                logger.error("fastembed not installed. Embeddings will be disabled.")
                self.model = False # Set to False so we don't keep retrying

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        self._load_model()  # Ensure model is loaded
        
        if self.model is False or not text or not text.strip():
            return None
            
        try:
            # text embedding returns a generator of numpy arrays
            embeddings_generator = self.model.embed([text])
            embedding_array = next(embeddings_generator)
            return embedding_array.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None