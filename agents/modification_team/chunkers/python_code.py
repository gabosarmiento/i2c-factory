# --- chunkers/python_code.py ---
from pathlib import Path
import hashlib
from agno.document.base import Document
from .base import ChunkingStrategy

class PythonCodeChunkingStrategy:
    def chunk(self, doc: Document) -> list[Document]:
        chunks = self._split_by_function_or_class(doc)

        if not chunks:
            # Fallback: return the full file as one chunk
            return [Document(
                content=doc.content,
                meta_data={
                    'chunk_type': 'fallback',
                    'chunk_name': 'full_file',
                    'language': 'python',
                }
            )]

        return chunks

    def _split_by_function_or_class(self, doc: Document) -> list[Document]:
        """
        Your actual logic to split Python code into functions and classes.
        Placeholder version below.
        """
        lines = doc.content.splitlines()
        chunks = []
        current_chunk = []
        for line in lines:
            if line.strip().startswith(("def ", "class ")):
                if current_chunk:
                    chunks.append(Document(
                        content="\n".join(current_chunk),
                        meta_data={'chunk_type': 'function_or_class'}
                    ))
                    current_chunk = []
            current_chunk.append(line)
        if current_chunk:
            chunks.append(Document(
                content="\n".join(current_chunk),
                meta_data={'chunk_type': 'function_or_class'}
            ))
        return chunks