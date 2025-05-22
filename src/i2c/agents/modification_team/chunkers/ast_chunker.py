import ast
from typing import List
from agno.document.base import Document

class SimpleLineChunker:
    """
    Fallback chunker that splits on 'def ' or 'class ' lines.
    """
    def chunk(self, document: Document) -> List[Document]:
        lines = document.content.splitlines()
        chunks: List[Document] = []
        current: List[str] = []
        start_line = 0

        for i, line in enumerate(lines):
            if line.strip().startswith(("def ", "class ")):
                if current:
                    snippet = "\n".join(current)
                    chunks.append(Document(
                        content=snippet,
                        id=None,
                        name=document.name,
                        meta_data={
                            "chunk_type": "block",
                            "start_line": start_line + 1,
                            "end_line": i
                        }
                    ))
                current = [line]
                start_line = i
            else:
                current.append(line)

        # final chunk
        if current:
            chunks.append(Document(
                content="\n".join(current),
                id=None,
                name=document.name,
                meta_data={
                    "chunk_type": "block",
                    "start_line": start_line + 1,
                    "end_line": len(lines)
                }
            ))
        return chunks

class ASTChunker:
    """
    AST-based chunker: splits on top-level functions and classes,
    with fallback to SimpleLineChunker on syntax errors.
    """

    def __init__(self, chunk_size: int = None, overlap: int = None):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document: Document) -> List[Document]:
        try:
            tree = ast.parse(document.content)
        except SyntaxError:
            # Fallback to line-based chunking
            return SimpleLineChunker().chunk(document)

        chunks: List[Document] = []
        lines = document.content.splitlines()

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                name = node.name
                start_line = node.lineno
                end_line = self._find_end_line(node)
                docstring = ast.get_docstring(node) or ""
                snippet = docstring + ("\n\n" if docstring else "") + "\n".join(
                    lines[start_line - 1:end_line]
                )
                chunk_type = 'function' if isinstance(node, ast.FunctionDef) else 'class'

                chunks.append(Document(
                    content=snippet,
                    id=None,
                    name=document.name,
                    meta_data={
                        'chunk_name': name,
                        'chunk_type': chunk_type,
                        'start_line': start_line,
                        'end_line': end_line,
                        'language': 'python',
                        'docstring': docstring
                    }
                ))

        # If nothing found, fallback to full file
        if not chunks:
            return SimpleLineChunker().chunk(document)

        return chunks

    def _find_end_line(self, node: ast.AST) -> int:
        # Recursively find the maximum end_lineno
        max_line = getattr(node, 'end_lineno', getattr(node, 'lineno', -1))
        for child in ast.iter_child_nodes(node):
            child_line = self._find_end_line(child)
            if child_line > max_line:
                max_line = child_line
        return max_line
