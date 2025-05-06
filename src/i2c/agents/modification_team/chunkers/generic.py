# --- chunkers/generic.py ---
from agno.document.chunking.recursive import RecursiveChunking as BaseRecursive

class GenericTextChunkingStrategy(BaseRecursive):
    """Wraps Agno's RecursiveChunking for any text."""
    pass
