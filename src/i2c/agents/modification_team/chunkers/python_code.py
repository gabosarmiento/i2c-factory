from agno.document.base import Document
from .base import ChunkingStrategy
import ast
from typing import Optional

class PythonCodeChunkingStrategy(ChunkingStrategy):
    """
    Splits Python code into chunks based on AST nodes (functions, async functions, classes).
    Falls back to returning the full file if AST parsing fails or yields no chunks.
    """

    def __init__(self, chunk_size: Optional[int] = None, overlap: Optional[int] = None):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, doc: Document) -> list[Document]:
        try:
            tree = ast.parse(doc.content)
            lines = doc.content.splitlines()
            chunks = []
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    # Determine node type and lines
                    start_line = node.lineno
                    end_line = getattr(node, 'end_lineno', start_line)
                    chunk_lines = lines[start_line - 1:end_line]
                    chunk_text = "\n".join(chunk_lines)
                    chunk_type = (
                        'function' if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else 'class'
                    )
                    chunks.append(Document(
                        content=chunk_text,
                        id=None,
                        name=doc.name,
                        meta_data={
                            'chunk_name': getattr(node, 'name', ''),
                            'chunk_type': chunk_type,
                            'start_line': start_line,
                            'end_line': end_line,
                            'language': 'python'
                        }
                    ))
            # Return AST-based chunks if any
            if chunks:
                return chunks
        except Exception:
            # AST parsing failed, fallback below
            pass

        # Fallback: return full document as single chunk
        return [Document(
            content=doc.content,
            id=None,
            name=doc.name,
            meta_data={
                'chunk_type': 'fallback',
                'chunk_name': 'full_file',
                'language': 'python'
            }
        )]
