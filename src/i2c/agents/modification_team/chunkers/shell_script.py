from typing import List
from agno.document.base import Document

class ShellScriptChunkingStrategy:
    def chunk(self, document) -> List[Document]:
        lines = document.content.splitlines()
        chunks = []
        start = 0
        current = []

        for i, line in enumerate(lines):
            if line.strip().startswith("#") and current:
                chunks.append(Document(
                    content="\n".join(current),
                    id=None,
                    name=document.name,
                    meta_data={
                        "chunk_type": "shell_block",
                        "chunk_name": f"shell_block_{len(chunks)}",
                        "start_line": start + 1,
                        "end_line": i,
                        "language": "bash"
                    }
                ))
                current = []
                start = i
            current.append(line)

        # final block
        if current:
            chunks.append(Document(
                content="\n".join(current),
                id=None,
                name=document.name,
                meta_data={
                    "chunk_type": "shell_block",
                    "chunk_name": f"shell_block_{len(chunks)}",
                    "start_line": start + 1,
                    "end_line": len(lines),
                    "language": "bash"
                }
            ))

        return chunks
