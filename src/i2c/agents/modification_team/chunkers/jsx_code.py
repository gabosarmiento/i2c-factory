# agents/modification_team/chunkers/jsx_code.py

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
        def info(self, msg):    print(f"[INFO_JSX] {msg}")
        def warning(self, msg): print(f"[WARN_JSX] {msg}")
        def error(self, msg):   print(f"[ERROR_JSX] {msg}")
    canvas = FallbackCanvas()


class JSXCodeChunkingStrategy(ChunkingStrategy):
    """
    Chunk JSX/React code into components, hooks, and functions using regex.
    More robust than esprima for JSX syntax.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
        max_content_length: int = int(os.getenv('MAX_JSX_CHUNK_CONTENT', '100000'))
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.max_content_length = max_content_length

        if chunk_size or overlap:
            canvas.warning(f"Ignoring chunk_size={chunk_size}, overlap={overlap} for JSX chunker")

    def chunk(self, document: Document) -> List[Document]:
        content = document.content or ""
        if len(content) > self.max_content_length:
            canvas.warning(
                f"Skipping JSX chunk for {document.meta_data.get('file_path', '')}: "
                f"content length {len(content)} exceeds {self.max_content_length}"
            )
            return [document]

        chunks: List[Document] = []
        
        # Extract React components, functions, and hooks
        patterns = [
            # React functional components
            (r'(?:export\s+(?:default\s+)?)?(?:const|function)\s+(\w+)\s*=?\s*\([^)]*\)\s*=>\s*\{', 'component'),
            # Class components  
            (r'class\s+(\w+)\s+extends\s+(?:React\.)?Component\s*\{', 'class_component'),
            # Regular functions
            (r'(?:export\s+)?function\s+(\w+)\s*\([^)]*\)\s*\{', 'function'),
            # Arrow functions
            (r'(?:export\s+)?const\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*\{', 'arrow_function'),
            # Custom hooks
            (r'(?:export\s+)?(?:const|function)\s+(use\w+)\s*[=\(]', 'hook'),
        ]

        for pattern, chunk_type in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                start_idx = match.start()
                component_name = match.group(1)
                
                # Find the end of this component/function
                end_idx = self._find_function_end(content, start_idx)
                
                if end_idx > start_idx:
                    snippet = content[start_idx:end_idx].strip()
                    if len(snippet) > 10:  # Skip tiny snippets
                        
                        # Create metadata
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

        # If no chunks found, create a general chunk
        if not chunks:
            canvas.warning(f"No JSX patterns found in {document.meta_data.get('file_path', '')}, using full content")
            
            # Create a single chunk with the full content
            h = hashlib.sha256(content.encode()).hexdigest()
            meta = {
                'chunk_name': 'jsx_content',
                'chunk_type': 'jsx_file',
                'content_hash': h,
                'language': 'jsx',
                'file_path': document.meta_data.get('file_path', ''),
            }
            chunks.append(Document(content=content, meta_data=meta))

        canvas.info(f"Chunked {len(chunks)} JSX blocks from {document.meta_data.get('file_path', '')}")
        return chunks

    def _find_function_end(self, content: str, start_idx: int) -> int:
        """Find the end of a function/component by matching braces"""
        # Find the opening brace
        brace_start = content.find('{', start_idx)
        if brace_start == -1:
            return start_idx + 100  # Fallback
        
        # Count braces to find matching closing brace
        brace_count = 1
        idx = brace_start + 1
        
        while idx < len(content) and brace_count > 0:
            char = content[idx]
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            idx += 1
        
        # Add a bit more context (like trailing semicolon)
        while idx < len(content) and content[idx] in ' \n\t;':
            idx += 1
        
        return idx