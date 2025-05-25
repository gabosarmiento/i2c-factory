import os
import re
import hashlib
from typing import List, Optional

from agno.document.base import Document
from agno.document.chunking.strategy import ChunkingStrategy
from .generic import GenericTextChunkingStrategy  # fallback import

# Logger fallback
try:
    from i2c.cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def info(self, msg):    print(f"[INFO_JSX] {msg}")
        def warning(self, msg): print(f"[WARN_JSX] {msg}")
        def error(self, msg):   print(f"[ERROR_JSX] {msg}")
    canvas = FallbackCanvas()

class JSXCodeChunkingStrategy(ChunkingStrategy):
    """
    Chunk JSX/React code into components, hooks, and functions using regex.
    More robust than esprima for JSX syntax.
    """

    def __init__(self, max_content_length: Optional[int] = None):
        self.max_content_length = max_content_length or int(os.getenv('MAX_JSX_CHUNK_CONTENT', '100000'))

    def chunk(self, document: Document) -> List[Document]:
        content = document.content or ""
        if len(content) > self.max_content_length:
            canvas.warning(
                f"Skipping JSX chunk for {document.meta_data.get('file_path', '')}: "
                f"content length {len(content)} exceeds {self.max_content_length}"
            )
            return [document]

        chunks: List[Document] = []
        patterns = [
            (r'(?:export\s+(?:default\s+)?)?(?:const|function)\s+(\w+)\s*=?\s*\([^)]*\)\s*=>\s*\{', 'component'),
            (r'class\s+(\w+)\s+extends\s+(?:React\.)?Component\s*\{', 'class_component'),
            (r'(?:export\s+)?function\s+(\w+)\s*\([^)]*\)\s*\{', 'function'),
            (r'(?:export\s+)?const\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*\{', 'arrow_function'),
            (r'(?:export\s+)?(?:const|function)\s+(use\w+)\s*[=\(]', 'hook'),
        ]

        for pattern, chunk_type in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                start_idx = match.start()
                component_name = match.group(1)
                brace_search_start = match.end() - 1
                body_brace_pos = content.find('{', brace_search_start)
                if body_brace_pos == -1:
                    continue

                end_idx = self._find_function_end(content, body_brace_pos)
                if end_idx > start_idx:
                    snippet = content[start_idx:end_idx].strip()
                    if len(snippet) > 10:
                        h = hashlib.sha256(snippet.encode()).hexdigest()
                        meta = {
                            'chunk_name': component_name,
                            'chunk_type': chunk_type,
                            'content_hash': h,
                            'language': 'jsx',
                            'file_path': document.meta_data.get('file_path', ''),
                            'start_pos': start_idx,
                            'end_pos': end_idx
                        }
                        chunks.append(Document(content=snippet, meta_data=meta))

        # Regex fallback → generic, but label as jsx_file
        if not chunks:
            canvas.warning(
                f"No JSX patterns found in {document.meta_data.get('file_path', '')}; "
                "falling back to GenericTextChunkingStrategy"
            )
            fallback = GenericTextChunkingStrategy().chunk(document)
            for ch in fallback:
                # override for JSX fallback
                ch.meta_data['chunk_type'] = 'jsx_file'
                ch.meta_data.setdefault('chunk_name', 'jsx_content')
            return fallback

        canvas.info(f"Chunked {len(chunks)} JSX blocks from {document.meta_data.get('file_path', '')}")
        return chunks

    def _find_function_end(self, content: str, start_idx: int) -> int:
        brace_start = content.find('{', start_idx)
        if brace_start == -1:
            return start_idx + 100
        brace_count = 1
        idx = brace_start + 1
        while idx < len(content) and brace_count > 0:
            if content[idx] == '{':
                brace_count += 1
            elif content[idx] == '}':
                brace_count -= 1
            idx += 1
        while idx < len(content) and content[idx] in ' \n\t;':
            idx += 1
        return idx

    def __repr__(self):
        return f"JSXCodeChunkingStrategy(max_content_length={self.max_content_length})"
