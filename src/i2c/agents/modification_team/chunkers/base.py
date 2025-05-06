# --- chunkers/base.py ---
import ast
from abc import ABC, abstractmethod
from agno.document.base import Document

class ChunkingStrategy(ABC):
    @abstractmethod
    def chunk(self, document: Document) -> list[Document]:
        """Split document into a list of Documents (chunks)."""
        ...
