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
        
try:
    from .context_indexer import ContextIndexer
except ImportError:
    ContextIndexer = None

# Logger setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class ContextReaderAgent:
    """
    Agent responsible of launching context indexing on a project.
    """

    def __init__(
        self,
        project_path: Path,
        progress_callback: Optional[Callable[[str, Any], None]] = None,
    ):
        self.project_path = project_path
        self.progress_callback = progress_callback

        # Carga del modelo de embeddings (puede ser None)
        self.embedding_model: Any | None = loaded_embedding_model
        if not self.embedding_model:
            logger.warning("No se cargó modelo de embedding; RAG fallará luego.")

        # Instancia el indexer si la clase está disponible
        if ContextIndexer:
            try:
                self.indexer = ContextIndexer(self.project_path)
            except Exception as e:
                logger.error(f"Error al crear ContextIndexer: {e}", exc_info=True)
                self.indexer = None
        else:
            logger.error("Clase ContextIndexer no encontrada.")
            self.indexer = None

    def index_project_context(
        self,
        project_path: Optional[Path] = None,
    ) -> dict:
        """
        Valida project_path y arranca la indexación.
        Devuelve un dict con files_indexed, files_skipped, chunks_indexed y errors.
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
            err = "ContextIndexer unavailable."
            logger.error(err)
            return {
                "files_indexed": 0,
                "files_skipped": 0,
                "chunks_indexed": 0,
                "errors": [err],
            }

        # Callback de inicio
        if self.progress_callback:
            try:
                self.progress_callback("start", {"project_path": str(path)})
            except Exception as e:
                logger.warning(f"start-callback failed: {e}")

        # Llama al indexer
        try:
            status = self.indexer.index_project()
        except Exception as e:
            logger.error(f"Indexing error for {path}: {e}", exc_info=True)
            status = {
                "files_indexed": 0,
                "files_skipped": 0,
                "chunks_indexed": 0,
                "errors": [str(e)],
            }

        # Callback de fin
        if self.progress_callback:
            try:
                self.progress_callback("finish", status)
            except Exception as e:
                logger.warning(f"finish-callback failed: {e}")

        return status

# Singleton para imports
default_root = Path(os.getenv("DEFAULT_PROJECT_ROOT", "."))
context_reader_agent = ContextReaderAgent(default_root)
