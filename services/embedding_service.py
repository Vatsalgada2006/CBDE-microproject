from sentence_transformers import SentenceTransformer
from typing import List

class EmbeddingService:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.model = None  # Will be loaded on first use

    def _load_model(self):
        """Load the SentenceTransformer model lazily."""
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)

    def generate_embedding(self, text: str) -> List[float]:
        self._load_model()  # Ensure model is loaded
        embedding = self.model.encode(text, convert_to_tensor=False)
        return embedding.tolist()