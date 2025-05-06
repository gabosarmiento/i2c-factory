# lean_knowledge_ingest.py
import json
import hashlib
import lancedb
import pyarrow as pa
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Union


from agno.document import Document
from agno.document.reader.pdf_reader import PDFReader
from agno.document.reader.text_reader import TextReader
from agno.document.reader.json_reader import JSONReader
from agno.document.reader.docx_reader import DocxReader
from agno.document.reader.url_reader import URLReader
from agno.utils.log import logger

from db_utils import get_db_connection, add_knowledge_chunks, TABLE_KNOWLEDGE_BASE, SCHEMA_KNOWLEDGE_BASE_V2

# Shim for batch embedding
from sentence_transformers import SentenceTransformer
class MyEmbedder:
    """
    Wrapper to expose a batch get_embeddings API over SentenceTransformer.
    """
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self._m = SentenceTransformer(model_name)
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        vectors = self._m.encode(texts, show_progress_bar=False)
        return [vec.tolist() for vec in vectors]


def add_document_to_knowledge_base(
    file_path: Union[str, Path],
    document_type: str,
    knowledge_space: str,
    embed_model: Any,
    metadata: Dict[str, Any] = None
) -> bool:
    """
    Lean ingestion: uses AGNO readers and AgentKnowledge to extract, embed, and store.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False

    # Compute hash for idempotency
    raw = file_path.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()

    # Choose reader
    suffix = file_path.suffix.lower()
    if suffix == '.pdf':
        reader = PDFReader()
    elif suffix == '.txt':
        reader = TextReader()
    elif suffix == '.json':
        reader = JSONReader()
    elif suffix in ('.doc', '.docx'):
        reader = DocxReader()
    elif suffix.startswith('http'):
        reader = URLReader()
    else:
        logger.error(f"Unsupported file type: {suffix}")
        return False

    # Read documents
    # Read documents
    try:
        if suffix.startswith('http'):
            docs: List[Document] = reader.read(url=str(file_path))
        else:
            docs: List[Document] = reader.read(file_path)
    except Exception as e:
        logger.error(f"Error reading document: {e}")
        return False

    # Prepare embeddings & chunks
    contents = [doc.content for doc in docs]
    vectors = embed_model.get_embeddings(contents)

    chunks = []
    for doc, vec in zip(docs, vectors):
        # Safely get chunk_type
        chunk_type = ''
        if hasattr(doc, 'metadata') and isinstance(doc.metadata, dict):
            chunk_type = doc.metadata.get('chunk_type', '')

        chunks.append({
            'source': str(file_path),
            'content': doc.content,
            'vector': vec,
            'category': document_type,
            'last_updated': datetime.utcnow().isoformat(),
            'knowledge_space': knowledge_space,
            'document_type': document_type,
            'framework': metadata.get('framework','') if metadata else '',
            'version': metadata.get('version','') if metadata else '',
            'parent_doc_id': '',
            'chunk_type': chunk_type,
            'source_hash': source_hash,
            'metadata_json': json.dumps(metadata or {}),
        })

    db = get_db_connection()
    if not db:
        logger.error("DB connection failed")
        return False

    return add_knowledge_chunks(db, chunks, knowledge_space)
