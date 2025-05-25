# src/agents/modification_team/chunkers/ts_code.py

import os
import re
import hashlib
from typing import List, Optional

from agno.document.base import Document
from agno.document.chunking.strategy import ChunkingStrategy

# Logger fallback
try:
    from i2c.cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def info(self, msg):    print(f"[INFO_TS] {msg}")
        def warning(self, msg): print(f"[WARN_TS] {msg}")
        def error(self, msg):   print(f"[ERROR_TS] {msg}")
    canvas = FallbackCanvas()

class TSCodeChunkingStrategy(ChunkingStrategy):
    """
    Chunk TypeScript code into top-level declarations: classes, interfaces,
    enums, functions, types, and variables.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None
    ):
        # chunk_size/overlap ignored for TS; use env var
        self.chunk_size = chunk_size
        self.overlap = overlap

        # loaded by your config.yaml → os.environ
        self.max_content_length = int(os.getenv('MAX_TS_CHUNK_CONTENT', '100000'))

        if chunk_size or overlap:
            canvas.warning(
                f"Ignoring chunk_size={chunk_size}, overlap={overlap} for TS chunker"
            )

        # Patterns for top-level declarations
        self.patterns = [
            (r'^(?:export\s+)?(class|interface|enum|function|type)\s+(\w+)', 'declaration'),
            (r'^(?:export\s+)?(?:const|let|var)\s+(\w+)',           'variable'),
        ]

    def chunk(self, document: Document) -> List[Document]:
        content = document.content or ""
        if len(content) > self.max_content_length:
            canvas.warning(
                f"Skipping TS chunk for {document.meta_data.get('file_path', '')}: "
                f"content length {len(content)} exceeds {self.max_content_length}"
            )
            return [document]

        lines = content.splitlines(keepends=True)
        chunks: List[Document] = []
        current: List[str]     = []
        current_name: str      = ''
        current_type: str      = ''
        current_start_pos: int = 0
        open_braces: int       = 0
        pos: int               = 0
        limit = self.max_content_length

        def flush_chunk():
            nonlocal current_name, current_type, current_start_pos
            if not current:
                return
            snippet = ''.join(current)
            end_pos = current_start_pos + len(snippet)
            h = hashlib.sha256(snippet.encode()).hexdigest()
            meta = {
                'chunk_name': current_name,
                'chunk_type': current_type,
                'content_hash': h,
                'language': 'typescript',
                'file_path': document.meta_data.get('file_path', ''),
                'start_pos': current_start_pos,
                'end_pos': end_pos,
            }
            chunks.append(Document(content=snippet, meta_data=meta))
            current.clear()
            current_name = ''
            current_type = ''
            current_start_pos = pos

        for line in lines:
            # detect new top-level decl only when balanced
            for pattern, decl_type in self.patterns:
                m = re.match(pattern, line)
                if m and open_braces == 0:
                    if current:
                        flush_chunk()
                    current_name = m.group(m.lastindex)
                    current_type = decl_type
                    current_start_pos = pos
                    break

            open_braces += line.count('{') - line.count('}')
            current.append(line)
            pos += len(line)

            if len(''.join(current)) > limit:
                flush_chunk()

        flush_chunk()

        # fallback if nothing emitted
        if not chunks:
            h = hashlib.sha256(content.encode()).hexdigest()
            meta = {
                'chunk_name': 'ts_content',
                'chunk_type': 'ts_file',
                'content_hash': h,
                'language': 'typescript',
                'file_path': document.meta_data.get('file_path', ''),
                'start_pos': 0,
                'end_pos': len(content),
            }
            chunks.append(Document(content=content, meta_data=meta))

        canvas.info(
            f"Chunked {len(chunks)} TS blocks "
            f"({self.max_content_length=} max length)"
        )
        return chunks

    def __repr__(self):
        return (
            f"TSCodeChunkingStrategy(chunk_size={self.chunk_size}, "
            f"overlap={self.overlap}, max_content_length={self.max_content_length})"
        )
