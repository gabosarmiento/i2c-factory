from agno.document.base import Document

class GenericTextChunkingStrategy:
    def chunk(self, document) -> list[Document]:
        # simple paragraph split
        paragraphs = document.content.split("\n\n")
        chunks = []
        line_offset = 0

        for para in paragraphs:
            lines = para.splitlines()
            end_offset = line_offset + len(lines)
            chunks.append(Document(
                content=para,
                id=None,
                name=document.name,
                meta_data={
                    "chunk_type": "paragraph",
                    "chunk_name": para[:30],
                    "start_line": line_offset + 1,
                    "end_line": end_offset,
                    "language": document.meta_data.get("language", "")
                }
            ))
            line_offset = end_offset + 1

        # Always have at least one chunk
        return chunks or [document]
