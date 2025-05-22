import re
from typing import List, Optional
from agno.document.base import Document

class CSSCodeChunkingStrategy:
    """
    Splits CSS content into selector blocks.
    """

    def __init__(self, chunk_size: Optional[int] = None, overlap: Optional[int] = None):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document: Document) -> List[Document]:
        lines = document.content.splitlines()
        chunks: List[Document] = []
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if '{' in stripped:
                # Start of a CSS selector block
                selector = stripped.split('{')[0].strip()
                start_line = i + 1
                block = [line]
                # Track matching braces
                brace_count = stripped.count('{') - stripped.count('}')
                i += 1
                while i < len(lines) and brace_count > 0:
                    block.append(lines[i])
                    brace_count += lines[i].count('{') - lines[i].count('}')
                    i += 1
                content = "\n".join(block)
                chunks.append(
                    Document(
                        content=content,
                        id=None,
                        name=document.name,
                        meta_data={
                            "chunk_name": selector,
                            "chunk_type": "selector",
                            "start_line": start_line,
                            "end_line": i,
                            "language": "css"
                        }
                    )
                )
            else:
                i += 1

        return chunks
