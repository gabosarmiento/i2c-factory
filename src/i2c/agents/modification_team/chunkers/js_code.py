# src/i2c/agents/modification_team/chunkers/js_code.py

import os
import re
import hashlib
from typing import List

from agno.document.base import Document
from agno.document.chunking.strategy import ChunkingStrategy

# Try to import the JS parser
try:
    import esprima
except ImportError:
    esprima = None

# Your other chunkers
from .generic import GenericTextChunkingStrategy
from .jsx_code import JSXCodeChunkingStrategy

# Logger fallback
try:
    from i2c.cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def info(self, msg):    print(f"[INFO_JS] {msg}")
        def warning(self, msg): print(f"[WARN_JS] {msg}")
        def error(self, msg):   print(f"[ERROR_JS] {msg}")
    canvas = FallbackCanvas()


class JSCodeChunkingStrategy(ChunkingStrategy):
    """
    Chunk JavaScript via Esprima.  If parsing fails or yields no top-level chunks,
    fall back to the JSX regex-based chunker.
    """

    def __init__(
        self,
        chunk_size: int = None,
        overlap: int = None,
        max_content_length: int = int(os.getenv('MAX_JS_CHUNK_CONTENT', '100000'))
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.max_content_length = max_content_length

        if chunk_size or overlap:
            canvas.warning(f"Ignoring chunk_size={chunk_size}, overlap={overlap} for JS chunker")

    def chunk(self, document: Document) -> List[Document]:
        content = document.content or ""
        path = document.meta_data.get('file_path', '')

        # 1) Too large → no chunking
        if len(content) > self.max_content_length:
            canvas.warning(f"Skipping JS chunk for {path}: content length {len(content)} exceeds {self.max_content_length}")
            return [document]

        # 2) No Esprima → no parsing
        if esprima is None:
            canvas.error("esprima parser not installed; falling back to generic text chunking")
            return GenericTextChunkingStrategy().chunk(document)

        # 3) Try to parse
        try:
            tree = esprima.parseScript(content, tolerant=True, loc=True)
        except Exception as e:
            canvas.error(f"Failed to parse JS file with esprima: {e}")
            return JSXCodeChunkingStrategy().chunk(document)

        lines = content.splitlines(keepends=True)
        chunks: List[Document] = []

        # 4) Extract every top-level node as a snippet
        for node in getattr(tree, 'body', []):
            # determine start/end lines
            if not hasattr(node, 'loc'):
                continue
            start_line = node.loc.start.line - 1
            end_line   = node.loc.end.line
            snippet = "".join(lines[start_line:end_line]).rstrip() + "\n"

            # pick a name and type
            ntype = node.type
            if ntype == 'FunctionDeclaration':
                name = node.id.name if node.id else 'anonymous'
                ctype = 'function'
            elif ntype == 'VariableDeclaration':
                names = [d.id.name for d in node.declarations if hasattr(d, 'id')]
                name = ",".join(names) or 'var'
                ctype = 'variable'
            elif ntype in ('ImportDeclaration', 'ImportSpecifier', 'ImportDefaultSpecifier'):
                names = []
                for imp in node.specifiers:
                    names.append(getattr(imp, 'local', imp).name)
                name = ",".join(names) or 'import'
                ctype = 'import'
            else:
                name = ntype
                ctype = 'other'

            h = hashlib.sha256(snippet.encode()).hexdigest()
            meta = {
                'chunk_name': name,
                'chunk_type': ctype,
                'content_hash': h,
                'language': 'javascript',
                'file_path': path,
                'start_pos': sum(len(l) for l in lines[:start_line]),
                'end_pos':   sum(len(l) for l in lines[:end_line]),
            }
            chunks.append(Document(content=snippet, meta_data=meta))

        # 5) If Esprima found nothing, fallback into JSX regex chunker
        if not chunks:
            canvas.warning(f"No JS chunks extracted from {path}; falling back to JSX chunker")
            return JSXCodeChunkingStrategy().chunk(document)

        canvas.info(f"Extracted {len(chunks)} JS chunks via esprima")
        return chunks

    def __repr__(self):
        return f"JSCodeChunkingStrategy(max_content_length={self.max_content_length})"
