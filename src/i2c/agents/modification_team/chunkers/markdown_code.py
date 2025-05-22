import re
from typing import List, Optional
from agno.document.base import Document

class MarkdownChunkingStrategy:
    """
    Splits a markdown document into sections based on headings.
    """

    def __init__(self, chunk_size: Optional[int] = None, overlap: Optional[int] = None):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document: Document) -> List[Document]:
        lines = document.content.splitlines()
        chunks: List[Document] = []
        current_chunk: List[str] = []
        current_heading: str = "Introduction"
        start_line: int = 0

        for i, line in enumerate(lines):
            if re.match(r"^#{1,6} ", line):  # Markdown heading
                # Flush existing chunk
                if current_chunk:
                    chunks.append(
                        Document(
                            content="\n".join(current_chunk),
                            id=None,
                            name=document.name,
                            meta_data={
                                "chunk_name": current_heading,
                                "chunk_type": "markdown_section",
                                "start_line": start_line + 1,
                                "end_line": i,
                                "language": "markdown"
                            }
                        )
                    )
                # Start new chunk
                current_chunk = [line]
                current_heading = line.lstrip('#').strip()
                start_line = i
            else:
                current_chunk.append(line)

        # Final flush
        if current_chunk:
            chunks.append(
                Document(
                    content="\n".join(current_chunk),
                    id=None,
                    name=document.name,
                    meta_data={
                        "chunk_name": current_heading,
                        "chunk_type": "markdown_section",
                        "start_line": start_line + 1,
                        "end_line": len(lines),
                        "language": "markdown"
                    }
                )
            )

        return chunks
