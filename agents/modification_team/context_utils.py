import os
from typing import TYPE_CHECKING, List, Optional
from functools import lru_cache

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer
else:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        SentenceTransformer = None
        print("❌ Error: sentence-transformers library not found. Please install it.")

try:
    from cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_UTIL] {msg}")
        def error(self, msg): print(f"[ERROR_UTIL] {msg}")
        def info(self, msg): print(f"[INFO_UTIL] {msg}")
    canvas = FallbackCanvas()

# Allow configuration via environment variable
EMBEDDING_MODEL_NAME = os.getenv('EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2')
_embedding_model: Optional['SentenceTransformer'] = None

try:
    _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    # Patch missing 'dimensions' attribute if needed
    if not hasattr(_embedding_model, "dimensions"):
        _embedding_model.dimensions = _embedding_model.get_sentence_embedding_dimension()
    
    if not hasattr(_embedding_model, "get_embedding"):
        def get_embedding(text):
            return _embedding_model.encode(text, convert_to_numpy=True)
        _embedding_model.get_embedding = get_embedding
        
    canvas.info(f"[ContextUtils] Loaded embedding model '{EMBEDDING_MODEL_NAME}' with dimensions {_embedding_model.dimensions}.")
except (ValueError, RuntimeError, ImportError) as e:
    _embedding_model = None
    canvas.warning(f"[ContextUtils] Failed to load embedding model '{EMBEDDING_MODEL_NAME}': {e}")
except Exception as e:
    _embedding_model = None
    canvas.warning(f"[ContextUtils] Unexpected error loading model: {e}")

@lru_cache(maxsize=1024)
def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate an embedding for the given text.

    Uses an LRU cache to speed up repeated calls with the same input.
    Returns a list of floats, or None if an error occurs.
    """
    if not text:
        canvas.error("[ContextUtils] Cannot generate embedding: Input text is empty.")
        return None
    if not _embedding_model:
        canvas.error("[ContextUtils] Cannot generate embedding: Model not loaded.")
        return None

    try:
        # Force numpy output for consistency
        vector = _embedding_model.encode(text, convert_to_numpy=True)
        # Ensure it's a list of floats
        return [float(x) for x in vector.tolist()]
    except (ValueError, RuntimeError, TypeError) as e:
        canvas.error(f"[ContextUtils] Error generating embedding for text '{text[:30]}...': {type(e).__name__}: {e}")
        return None
    except Exception as e:
        canvas.error(f"[ContextUtils] Unexpected error: {type(e).__name__}: {e}")
        return None
