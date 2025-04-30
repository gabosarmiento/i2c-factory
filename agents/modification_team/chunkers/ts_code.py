# agents/modification_team/chunkers/ts_code.py
import os
import re
import hashlib
from typing import List, Optional

from agno.document.base import Document
from agno.document.chunking.strategy import ChunkingStrategy

# Logger fallback
try:
    from cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def info(self, msg):    print(f"[INFO_TS] {msg}")
        def warning(self, msg): print(f"[WARN_TS] {msg}")
        def error(self, msg):   print(f"[ERROR_TS] {msg}")
    canvas = FallbackCanvas()

class TSCodeChunkingStrategy(ChunkingStrategy):
    """
    Chunk TypeScript/JSX code into functions, classes, interfaces, and types using regex.
    """
    def __init__(self, max_content_length: int = int(os.getenv('MAX_TS_CHUNK_CONTENT', '100000'))):
        self.max_content_length = max_content_length
        # Matches function, class, interface, or type declarations
        self.pattern = re.compile(
            r"\b(function|class|interface|type)\s+(\w+)"
        )

    def chunk(self, document: Document) -> List[Document]:
        content = document.content or ""
        if len(content) > self.max_content_length:
            canvas.warning(
                f"Skipping TS chunk for {document.meta_data.get('file_path', '')}: "
                f"content length {len(content)} exceeds {self.max_content_length}"
            )
            return [document]

        chunks: List[Document] = []
        for match in self.pattern.finditer(content):
            start_idx = match.start()
            # Find opening brace or semicolon (for type aliases)
            brace_pos = content.find('{', match.end())
            semi_pos = content.find(';', match.end())
            if brace_pos >= 0 and (semi_pos < 0 or brace_pos < semi_pos):
                # Block declaration
                depth = 1
                idx = brace_pos + 1
                while idx < len(content) and depth > 0:
                    if content[idx] == '{': depth += 1
                    elif content[idx] == '}': depth -= 1
                    idx += 1
                end_idx = idx
            elif semi_pos >= 0:
                # Single-line type or interface alias
                end_idx = semi_pos + 1
            else:
                continue

            snippet = content[start_idx:end_idx].strip()
            if not snippet:
                continue

            # Metadata
            decl_type = match.group(1)
            name = match.group(2)
            h = hashlib.sha256(snippet.encode()).hexdigest()
            meta = {
                'chunk_name': name,
                'chunk_type': decl_type,
                'content_hash': h,
                'language': 'typescript',
                'file_path': document.meta_data.get('file_path', ''),
            }
            chunks.append(Document(content=snippet, meta_data=meta))

        canvas.info(f"Chunked {len(chunks)} TS blocks")
        return chunks
