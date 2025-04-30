from functools import lru_cache
from sentence_transformers import SentenceTransformer

from .config import load_config

# Load configuration values
cfg = load_config()

# Initialize the embedding model
EMBED_MODEL = SentenceTransformer(cfg['EMBEDDING_MODEL'])

@lru_cache(maxsize=1024)
def embed_text(text: str) -> list[float]:
    """
    Generate and cache embeddings for text using the configured model.
    """
    vector = EMBED_MODEL.encode(text, convert_to_numpy=True)
    return vector.tolist()