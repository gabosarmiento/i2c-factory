import hashlib
from typing import List, Optional

from agno.document.base import Document
from agno.document.chunking.strategy import ChunkingStrategy

# HTML parser
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# Logger fallback
try:
    from i2c.cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def info(self, msg):    print(f"[INFO_HTML] {msg}")
        def warning(self, msg): print(f"[WARN_HTML] {msg}")
        def error(self, msg):   print(f"[ERROR_HTML] {msg}")
    canvas = FallbackCanvas()


class HTMLCodeChunkingStrategy(ChunkingStrategy):
    """
    Chunk HTML files into <script> blocks and main HTML content.
    """

    def __init__(self, chunk_size: Optional[int] = None, overlap: Optional[int] = None):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document: Document) -> List[Document]:
        content = document.content or ""
        chunks: List[Document] = []

        if BeautifulSoup is None:
            canvas.error("bs4 not installed; returning entire HTML as one chunk.")
            return [document]

        soup = BeautifulSoup(content, 'html.parser')

        # Extract <script> blocks
        for idx, script in enumerate(soup.find_all('script')):
            code = script.string or ''
            if not code.strip():
                continue
            h = hashlib.sha256(code.encode()).hexdigest()
            meta = {
                'chunk_name': f'script_{idx}',
                'chunk_type': 'script',
                'content_hash': h,
                'language': 'javascript',
                'file_path': document.meta_data.get('file_path', ''),
            }
            chunks.append(Document(content=code, meta_data=meta))

        # Remaining HTML content
        for script in soup.find_all('script'):
            script.decompose()
        html_text = soup.prettify().strip()
        if html_text:
            h = hashlib.sha256(html_text.encode()).hexdigest()
            meta = {
                'chunk_name': 'html',
                'chunk_type': 'html',
                'content_hash': h,
                'language': 'html',
                'file_path': document.meta_data.get('file_path', ''),
            }
            chunks.append(Document(content=html_text, meta_data=meta))

        canvas.info(f"Chunked {len(chunks)} HTML blocks")
        return chunks
