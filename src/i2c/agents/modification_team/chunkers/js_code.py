import os
import hashlib
from typing import List, Optional

try:
    import esprima
except ImportError:
    esprima = None

from agno.document.base import Document
from .base import ChunkingStrategy

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
    Uses esprima to chunk JavaScript/TypeScript code into top-level constructs.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
        max_content_length: int = int(os.getenv('MAX_JS_CHUNK_CONTENT', '100000'))
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.max_content_length = max_content_length

        if chunk_size or overlap:
            canvas.warning(f"Ignoring chunk_size={chunk_size}, overlap={overlap} for JS chunker")

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
            tree = esprima.parseScript(content, tolerant=True, loc=True)
            chunks = []
            lines = content.splitlines()

            for node in tree.body:
                try:
                    if hasattr(node, 'loc') and node.loc:
                        start = node.loc.start.line
                        end = node.loc.end.line

                        snippet = "\n".join(lines[start - 1:end])
                        node_type = getattr(node, 'type', 'unknown')

                        # Attempt to get a name
                        name = 'anonymous'
                        if hasattr(node, 'id') and node.id:
                            name = getattr(node.id, 'name', 'anonymous')
                        elif hasattr(node, 'key') and node.key:
                            name = getattr(node.key, 'name', 'anonymous')

                        chunks.append(Document(
                            content=snippet,
                            meta_data={
                                'chunk_name': name,
                                'chunk_type': node_type,
                                'language': 'javascript',
                                'start_line': start,
                                'end_line': end,
                                'file_path': document.meta_data.get('file_path', ''),
                                'content_hash': hashlib.sha256(snippet.encode()).hexdigest(),
                            }
                        ))

                except Exception as e:
                    canvas.warning(f"Failed to extract chunk for node: {e}")

            if not chunks:
                canvas.warning("No valid JS chunks extracted; returning full document.")
                return [document]

            canvas.info(f"Extracted {len(chunks)} JS chunks via esprima")
            return chunks

        except Exception as e:
            canvas.error(f"Failed to parse JS file with esprima: {e}")
            return [document]
