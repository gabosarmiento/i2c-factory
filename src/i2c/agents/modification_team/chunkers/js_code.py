# agents/modification_team/chunkers/js_code.py
import os
import hashlib
from typing import List, Optional

# Attempt to import the JS parser
try:
    import esprima
except ImportError:
    esprima = None

from agno.document.base import Document
from .base import ChunkingStrategy

# Canvas/logger fallback
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
    Chunk JavaScript/TypeScript code into functions, classes, and methods.
    """
    def __init__(
        self,
        max_content_length: int = int(os.getenv('MAX_JS_CHUNK_CONTENT', '100000'))
    ):
        self.max_content_length = max_content_length

    def chunk(self, document: Document) -> List[Document]:
        content = document.content or ""
        if len(content) > self.max_content_length:
            canvas.warning(
                f"Skipping JS chunk for {document.meta_data.get('file_path', '')}: "
                f"content length {len(content)} exceeds {self.max_content_length}"
            )
            return [document]

        if esprima is None:
            canvas.error("esprima parser not available; cannot chunk JS code.")
            return [document]

        try:
            tree = esprima.parseScript(
                content,
                tolerant=True,
                loc=True,
                range=True,
            )
        except Exception as e:
            canvas.error(f"Parsing error in JS document: {e}")
            return [document]

        chunks: List[Document] = []

        # Helper to record a node
        def record_node(node, node_type: str, name: Optional[str], start_idx: int, end_idx: int):
            code = content[start_idx:end_idx].strip()
            if not code:
                return
            start_line = getattr(node.loc.start, 'line', None)
            end_line = getattr(node.loc.end, 'line', None)
            # Fallback if loc missing
            if start_line is None or end_line is None:
                start_line = end_line = None

            h = hashlib.sha256(code.encode()).hexdigest()
            meta = {
                'chunk_name': name or '<anonymous>',
                'chunk_type': node_type,
                'start_line': start_line,
                'end_line': end_line,
                'content_hash': h,
                'language': 'javascript',
                **(document.meta_data or {}),
            }
            chunks.append(Document(content=code, meta_data=meta))

        # Top-level function and class declarations
        for node in getattr(tree, 'body', []):
            t = getattr(node, 'type', None)
            if t == 'FunctionDeclaration':
                name = node.id.name if getattr(node, 'id', None) else '<anonymous>'
                start, end = node.range
                record_node(node, 'function', name, start, end)

            elif t == 'ClassDeclaration':
                name = node.id.name if getattr(node, 'id', None) else '<anonymous>'
                start, end = node.range
                record_node(node, 'class', name, start, end)

                # Also chunk methods inside the class
                for elem in getattr(node, 'body', {}).get('body', []):
                    if getattr(elem, 'type', None) == 'MethodDefinition':
                        key = getattr(elem.key, 'name', '<anonymous>')
                        s, e = elem.range
                        record_node(elem, 'method', key, s, e)

        canvas.info(f"Chunked {len(chunks)} JS blocks")
        return chunks
