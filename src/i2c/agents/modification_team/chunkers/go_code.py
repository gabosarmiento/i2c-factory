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
        def info(self, msg):    print(f"[INFO_GO] {msg}")
        def warning(self, msg): print(f"[WARN_GO] {msg}")
        def error(self, msg):   print(f"[ERROR_GO] {msg}")
    canvas = FallbackCanvas()


class GoCodeChunkingStrategy(ChunkingStrategy):
    """
    Chunk Go code into functions, methods, structs, and interfaces via regex.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
        max_content_length: int = int(os.getenv('MAX_GO_CHUNK_CONTENT', '100000'))
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.max_content_length = max_content_length
        self.pattern = re.compile(
            r"^func\s*(?:\(.*?\))?\s*(?P<name>\w+)\s*\([\s\S]*?\)\s*\{"  # funcs/methods
            r"|^type\s+(?P<type_name>\w+)\s+(?P<kind>struct|interface)",  # type declarations
            re.MULTILINE
        )

    def chunk(self, document: Document) -> List[Document]:
        content = document.content or ""
        if len(content) > self.max_content_length:
            canvas.warning(
                f"Skipping Go chunk for {document.meta_data.get('file_path', '')}: "
                f"content length {len(content)} exceeds {self.max_content_length}"
            )
            return [document]

        chunks: List[Document] = []
        for match in self.pattern.finditer(content):
            start_idx = match.start()
            name = match.group('name') or match.group('type_name')
            kind = 'function' if match.group('name') else match.group('kind')

            if kind == 'function':
                brace_pos = content.find('{', match.end())
                depth = 1
                idx = brace_pos + 1
                while idx < len(content) and depth > 0:
                    if content[idx] == '{':
                        depth += 1
                    elif content[idx] == '}':
                        depth -= 1
                    idx += 1
                end_idx = idx
            else:
                brace_pos = content.find('{', match.end())
                if brace_pos < 0:
                    end_idx = content.find('\n', match.end()) or len(content)
                else:
                    depth = 1
                    idx = brace_pos + 1
                    while idx < len(content) and depth > 0:
                        if content[idx] == '{':
                            depth += 1
                        elif content[idx] == '}':
                            depth -= 1
                        idx += 1
                    end_idx = idx

            snippet = content[start_idx:end_idx].strip()
            if not snippet:
                continue

            h = hashlib.sha256(snippet.encode()).hexdigest()
            meta = {
                'chunk_name': name,
                'chunk_type': kind,
                'content_hash': h,
                'language': 'go',
                'file_path': document.meta_data.get('file_path', ''),
            }
            chunks.append(Document(content=snippet, meta_data=meta))

        canvas.info(f"Chunked {len(chunks)} Go blocks")
        return chunks
