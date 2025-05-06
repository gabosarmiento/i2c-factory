# agno/document/chunking/python_code_chunker.py

import ast
import os
import hashlib
from pathlib import Path
from typing import List, Type, Optional

# 1) Pull in Agno’s base classes
from agno.document.base import Document
from agno.document.chunking.strategy import ChunkingStrategy

# 2) (Optional) Try to use xxhash for speed
try:
    import xxhash
    _has_xxhash = True
except ImportError:
    _has_xxhash = False

# 3) Your canvas/logger
try:
    from i2c.cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def info(self, msg):    print(f"[INFO_CODE] {msg}")
        def warning(self, msg): print(f"[WARN_CODE] {msg}")
        def error(self, msg):   print(f"[ERROR_CODE] {msg}")
    canvas = FallbackCanvas()


class PythonCodeChunkingStrategy(ChunkingStrategy):
    """
    A ChunkingStrategy that extracts top-level and nested
    functions, async functions, and classes from a Python file.
    """

    def __init__(
        self,
        node_types: Optional[List[Type[ast.AST]]] = None,
        max_content_length: int = int(os.getenv("MAX_CHUNK_CONTENT", "100000")),
    ):
        # Default to FunctionDef, AsyncFunctionDef, ClassDef
        self.node_types = node_types or [ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]
        self.max_content_length = max_content_length

    def chunk(self, document: Document) -> List[Document]:
        """
        Takes an Agno Document whose .content is Python source,
        and returns a list of smaller Documents for each function/class.
        """
        src_text = document.content
        path_meta = document.meta_data.get("file_path", None)

        # 1) Skip huge blobs
        if len(src_text) > self.max_content_length:
            canvas.warning(f"Skipping chunk on {path_meta or 'in-memory'}: content too large")
            return [document]

        # 2) Parse once, with error handling
        try:
            tree = ast.parse(src_text)
        except SyntaxError as e:
            canvas.error(f"SyntaxError in {path_meta or '<string>'}: {e}")
            return [document]
        except Exception as e:
            canvas.error(f"Unexpected parse error in {path_meta or '<string>'}: {type(e).__name__}: {e}")
            return [document]

        chunks: List[Document] = []
        for node in ast.walk(tree):
            if not isinstance(node, tuple(self.node_types)):
                continue
            seg = ast.get_source_segment(src_text, node)
            if not seg:
                continue

            code = seg.strip()
            start = getattr(node, "lineno", None)
            end   = getattr(node, "end_lineno", None)
            if start is None:
                continue
            if end is None:
                end = start + code.count("\n")
            if end < start:
                end = start

            # 3) Compute a fast hash
            if _has_xxhash:
                h = xxhash.xxh64(code.encode()).hexdigest()
            else:
                h = hashlib.sha256(code.encode()).hexdigest()

            meta = dict(document.meta_data)
            meta.update({
                "chunk":       getattr(node, "name", "<lambda>"),
                "type":        "async_function"
                               if isinstance(node, ast.AsyncFunctionDef) else
                               "function"       if isinstance(node, ast.FunctionDef)      else
                               "class",
                "start_line":  start,
                "end_line":    end,
                "content_hash": h,
            })

            chunks.append(Document(
                content=code,
                id=f"{document.id}_{node.lineno}" if document.id else None,
                name=document.name,
                meta_data=meta,
            ))

        canvas.info(f"PythonCodeChunkingStrategy → {len(chunks)} chunks from {path_meta or '<in-memory>'}")
        return chunks
