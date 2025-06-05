# agents/modification_team/context_reader/context_reader_agent.py

import os
from pathlib import Path
from typing import Any, Callable, Optional
import logging

try:
    from ..context_utils import _embedding_model as loaded_embedding_model
except ImportError:
    loaded_embedding_model = None

# If that fails, use the official project-wide embed model getter
if loaded_embedding_model is None:
    try:
        from i2c.workflow.modification.rag_config import get_embed_model
        loaded_embedding_model = get_embed_model()
        logging.info("Using embedding model from rag_config.get_embed_model()")
    except Exception as e:
        logging.error(f"Failed to load embedding model from rag_config: {e}")
        # No further fallbacks - we'll just have None and handle the case properly
        
from .context_indexer import ContextIndexer
from .incremental_indexer import IncrementalContextIndexer

# Logger setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Updated ContextReaderAgent class
class ContextReaderAgent:
    """
    Agent responsible of launching context indexing on a project.
    """

    def __init__(
        self,
        project_path: Path,
        progress_callback: Optional[Callable[[str, Any], None]] = None,
        use_incremental: bool = True,
    ):
        self.project_path = project_path
        self.progress_callback = progress_callback
        self.use_incremental = use_incremental

        # Load embedding model
        self.embedding_model: Any | None = loaded_embedding_model
        if not self.embedding_model:
            logger.warning("No embedding model loaded; RAG will fail later.")

        # Initialize the appropriate indexer
        try:
            if self.use_incremental:
                logger.info("Using IncrementalContextIndexer for intelligent change detection")
                self.indexer = IncrementalContextIndexer(self.project_path)
            else:
                logger.info("Using legacy ContextIndexer for full reindexing")
                self.indexer = ContextIndexer(self.project_path)
        except Exception as e:
            logger.error(f"Error creating indexer: {e}", exc_info=True)
            self.indexer = None

    def index_project_context(
    self,
    project_path: Optional[Path] = None,
) -> dict:
        """
        Validates project_path and starts indexing.
        Returns a dict with files_indexed, files_skipped, chunks_indexed and errors.
        """
        path = project_path or self.project_path
        if path is None or not path.exists() or not path.is_dir():
            err = f"Invalid project_path: {path}"
            logger.error(err)
            return {
                "files_indexed": 0,
                "files_skipped": 0,
                "chunks_indexed": 0,
                "errors": [err],
            }

        if not self.indexer:
            # Try to create indexer again if it was None
            try:
                if self.use_incremental:
                    self.indexer = IncrementalContextIndexer(path)
                else:
                    self.indexer = ContextIndexer(path)
            except Exception as e:
                err = f"Indexer unavailable: {e}"
                logger.error(err)
                return {
                    "files_indexed": 0,
                    "files_skipped": 0,
                    "chunks_indexed": 0,
                    "errors": [err],
                }

        # Start callback
        if self.progress_callback:
            try:
                self.progress_callback("start", {"project_path": str(path)})
            except Exception as e:
                logger.warning(f"start-callback failed: {e}")

        # Call the appropriate indexer method
        try:
            logger.info(f"Starting indexing of {path}")
            if self.use_incremental:
                status = self.indexer.index_project_incrementally()
                logger.info(f"Incremental indexing completed with status: {status}")
            else:
                status = self.indexer.index_project()
                logger.info(f"Full indexing completed with status: {status}")
        except Exception as e:
            # Log the detailed error trace
            import traceback
            logger.error(f"Error during context indexing: {e}")
            logger.error(traceback.format_exc())
            
            status = {
                "files_indexed": 0,
                "files_skipped": 0,
                "chunks_indexed": 0,
                "errors": [str(e)],
            }

        # Finish callback
        if self.progress_callback:
            try:
                self.progress_callback("finish", status)
            except Exception as e:
                logger.warning(f"finish-callback failed: {e}")

        return status

# Singleton para imports
default_root = Path(os.getenv("DEFAULT_PROJECT_ROOT", "."))
context_reader_agent = ContextReaderAgent(default_root, use_incremental=True)
