# agents/modification_team/chunkers/java_code.py
import os
import re
import hashlib
from typing import List, Optional

from agno.document.base import Document
from agno.document.chunking.strategy import ChunkingStrategy

# Optional Java parser (for future enhancement)
try:
    import javalang
except ImportError:
    javalang = None

# Logger fallback
try:
    from cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def info(self, msg):    print(f"[INFO_JAVA] {msg}")
        def warning(self, msg): print(f"[WARN_JAVA] {msg}")
        def error(self, msg):   print(f"[ERROR_JAVA] {msg}")
    canvas = FallbackCanvas()

class JavaCodeChunkingStrategy(ChunkingStrategy):
    """
    Chunk Java code into class/interface/enum definitions (naive regex-based),
    with an optional javalang fallback for parsing.
    """
    def __init__(self, max_content_length: int = int(os.getenv('MAX_JAVA_CHUNK_CONTENT', '100000'))):
        self.max_content_length = max_content_length
        # Matches class, interface, or enum declarations
        self.pattern = re.compile(r"\b(class|interface|enum)\s+(\w+)")

    def chunk(self, document: Document) -> List[Document]:
        content = document.content or ""
        if len(content) > self.max_content_length:
            canvas.warning(
                f"Skipping Java chunk for {document.meta_data.get('file_path', '')}: "
                f"content length {len(content)} exceeds {self.max_content_length}"
            )
            return [document]

        chunks: List[Document] = []
        # If javalang available, could enhance parsing here
        if javalang is None:
            canvas.info("javalang not installed; using regex-based chunking.")

        for match in self.pattern.finditer(content):
            start_idx = match.start()
            # Find opening brace
            brace_pos = content.find('{', match.end())
            if brace_pos < 0:
                continue
            # Find matching closing brace
            depth = 1
            idx = brace_pos + 1
            while idx < len(content) and depth > 0:
                if content[idx] == '{': depth += 1
                elif content[idx] == '}': depth -= 1
                idx += 1
            end_idx = idx
            snippet = content[start_idx:end_idx].strip()
            if not snippet:
                continue

            # Metadata
            name = match.group(2)
            h = hashlib.sha256(snippet.encode()).hexdigest()
            meta = {
                'chunk_name': name,
                'chunk_type': match.group(1),
                'content_hash': h,
                'language': 'java',
                'file_path': document.meta_data.get('file_path', ''),
            }
            chunks.append(Document(content=snippet, meta_data=meta))

        canvas.info(f"Chunked {len(chunks)} Java blocks")
        return chunks
