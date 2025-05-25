# src/agents/modification_team/chunkers/ast_chunker.py

import ast
import hashlib
from typing import List, Optional

from agno.document.base import Document
from agno.document.chunking.strategy import ChunkingStrategy

# Logger fallback
try:
    from i2c.cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def info(self, msg):    print(f"[INFO_AST] {msg}")
        def warning(self, msg): print(f"[WARN_AST] {msg}")
        def error(self, msg):   print(f"[ERROR_AST] {msg}")
    canvas = FallbackCanvas()


class SimpleLineChunker:
    """
    Fallback chunker that splits on 'def ' or 'class ' lines.
    """
    def chunk(self, document: Document) -> List[Document]:
        lines = document.content.splitlines(keepends=True)
        chunks: List[Document] = []
        current: List[str] = []
        start_line = 0

        for i, line in enumerate(lines):
            if line.lstrip().startswith(("def ", "class ")):
                # flush previous block
                if current:
                    snippet = "".join(current)
                    chunks.append(Document(
                        content=snippet,
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

        # final block
        if current:
            snippet = "".join(current)
            chunks.append(Document(
                content=snippet,
                meta_data={
                    "chunk_type": "block",
                    "start_line": start_line + 1,
                    "end_line": len(lines)
                }
            ))

        return chunks


class ASTChunkingStrategy(ChunkingStrategy):
    """
    AST-based chunker: splits on top-level imports, assignments,
    function/async defs, classes, and expressions.
    Falls back to SimpleLineChunker on parse errors, and emits
    a module_init chunk for empty __init__.py files.
    """

    def __init__(self, chunk_size: Optional[int] = None, overlap: Optional[int] = None):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document: Document) -> List[Document]:
        content = document.content or ""
        # 1) Try plain AST parse
        try:
            tree = ast.parse(content)
        except (SyntaxError, ValueError) as e:
            canvas.warning(f"{e.__class__.__name__} in AST parse: {e}; falling back to lines")
            return SimpleLineChunker().chunk(document)

        lines = content.splitlines(keepends=True)
        chunks: List[Document] = []

        # 2) Extract top-level AST nodes
        for node in tree.body:
            if not isinstance(node, (
                ast.FunctionDef, ast.AsyncFunctionDef,
                ast.ClassDef, ast.Import, ast.ImportFrom,
                ast.Assign, ast.AnnAssign, ast.Expr
            )):
                continue

            start = node.lineno - 1
            end = getattr(node, 'end_lineno', start + 1)
            snippet = "".join(lines[start:end]).rstrip() + "\n"

            # Determine name and type
            if isinstance(node, ast.FunctionDef):
                name, ctype = node.name, 'function'
            elif isinstance(node, ast.AsyncFunctionDef):
                name, ctype = node.name, 'async_function'
            elif isinstance(node, ast.ClassDef):
                name, ctype = node.name, 'class'
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [alias.asname or alias.name for alias in node.names]
                name, ctype = ",".join(names), 'import'
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = getattr(node, 'targets', None) or [node.target]
                names = [t.id for t in targets if isinstance(t, ast.Name)]
                name, ctype = ",".join(names) or 'assignment', 'assignment'
            else:  # ast.Expr
                name, ctype = type(node).__name__, 'other'

            h = hashlib.sha256(snippet.encode()).hexdigest()
            meta = {
                'chunk_name':   name,
                'chunk_type':   ctype,
                'content_hash': h,
                'language':     'python',
                'file_path':    document.meta_data.get('file_path', ''),
                'start_pos':    sum(len(l) for l in lines[:start]),
                'end_pos':      sum(len(l) for l in lines[:end]),
            }
            chunks.append(Document(content=snippet, meta_data=meta))

        # 3) If no AST nodes and it's __init__.py → single module_init chunk
        fp = document.meta_data.get('file_path', '')
        if not chunks and fp.endswith('__init__.py'):
            empty_meta = {
                'chunk_name': '__init__',
                'chunk_type': 'module_init',
                'language':   'python',
                'file_path':  fp,
                'start_pos':  0,
                'end_pos':    0,
            }
            return [Document(content="", meta_data=empty_meta)]

        # 4) Final fallback to line-based chunker
        if not chunks:
            return SimpleLineChunker().chunk(document)

        canvas.info(f"AST chunked into {len(chunks)} blocks")
        return chunks


# Alias for factory compatibility
ASTChunker = ASTChunkingStrategy
