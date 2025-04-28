# /agents/modification_team/context_reader/context_reader_agent.py
# Defines the ContextReaderAgent class which orchestrates context indexing.

from pathlib import Path
from typing import Any # For type hinting

# Import SentenceTransformer handling from context_utils
# This ensures model is loaded once when context_utils is imported
try:
    # Try relative import first (if context_utils is in the parent dir)
    from ..context_utils import _embedding_model as loaded_embedding_model
except ImportError: # Fallback if structure is different or run directly
     try:
        # Try absolute import from expected location
        from agents.modification_team.context_utils import _embedding_model as loaded_embedding_model
     except ImportError:
          print("❌ Critical Error: Cannot import pre-loaded embedding model from context_utils.")
          loaded_embedding_model = None

# Import the indexing function from the sibling module
from .context_indexer import index_project_context

# Import CLI for logging (optional, could be passed in)
try:
    from cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_AGENT] {msg}")
        def error(self, msg): print(f"[ERROR_AGENT] {msg}")
        def info(self, msg): print(f"[INFO_AGENT] {msg}")
    canvas = FallbackCanvas()


class ContextReaderAgent:
    """
    Agent responsible for managing the project context indexing process.
    It holds the embedding model reference (loaded in context_utils)
    and delegates indexing to context_indexer.
    Note: This is not an Agno Agent as it doesn't directly call an LLM for its primary task.
    """
    def __init__(self):
        print("📄 [ContextReaderAgent] Initialized.")
        # Store the pre-loaded embedding model instance reference
        self.embedding_model: Any | None = loaded_embedding_model # Reference pre-loaded model
        if self.embedding_model is None:
            # Warning already printed by context_utils if loading failed
            canvas.warning("   ContextReaderAgent initialized without a valid embedding model.")

    def index_project_context(self, project_path: Path) -> dict:
        """
        Orchestrates the indexing process by calling the indexer function.
        The indexer function now uses the pre-loaded embedding model internally.

        Args:
            project_path: Path to the project directory.

        Returns:
            A dictionary confirming indexing status.
        """
        # Call the indexer function WITHOUT passing the embedding model
        # as it's accessed via the context_utils module now.
        return index_project_context(project_path, self.embedding_model)

    # Add other methods later if needed, e.g., for querying context directly
    # def get_context_summary(self, project_path: Path) -> str: ...

# Instantiate the agent globally for easy import
context_reader_agent = ContextReaderAgent()
