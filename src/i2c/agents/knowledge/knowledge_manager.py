# /agents/knowledge/knowledge_manager.py
"""ExternalKnowledgeManager

Coordinates ingestion and retrieval of external knowledge with existing RAG system.
"""

from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from i2c.cli.controller import canvas
from i2c.db_utils import get_db_connection, add_or_update_chunks, TABLE_KNOWLEDGE_BASE, SCHEMA_KNOWLEDGE_BASE,query_context
from i2c.workflow.modification.rag_retrieval import retrieve_context_for_planner

class ExternalKnowledgeManager:
    """Manages external knowledge ingestion and retrieval."""
    
    def __init__(self, embed_model, db_path: str = "./data/lancedb"):
        self.embed_model = embed_model
        self.db_path = db_path
        self.db_connection = get_db_connection()
        if self.db_connection is None:
            raise ConnectionError("Failed to initialize database connection")

    def ingest_knowledge(
        self, source: str, content: str, metadata: Optional[Dict] = None
    ) -> bool:
        """Ingest external knowledge into the knowledge_base table."""
        try:
            if not content.strip():
                canvas.warning(f"Empty content for source {source}. Skipping.")
                return False

            # Generate embedding - handle both numpy arrays and lists
            embedding = self.embed_model.encode(content)
            if isinstance(embedding, np.ndarray):
                vector = embedding.tolist()
            else:
                vector = list(embedding)

            # Create chunk
            chunk = {
                "source": source,
                "content": content,
                "vector": vector,
                "category": metadata.get("category", "doc") if metadata else "doc",
                "last_updated": metadata.get("last_updated", "2025-05-03") if metadata else "2025-05-03"
            }

            # Add to LanceDB
            add_or_update_chunks(
                db=self.db_connection,
                table_name=TABLE_KNOWLEDGE_BASE,
                schema=SCHEMA_KNOWLEDGE_BASE,
                identifier_field="source",
                identifier_value=source,
                chunks=[chunk],
            )
            canvas.success(f"Ingested knowledge from {source}")
            return True

        except Exception as e:
            canvas.error(f"Failed to ingest knowledge from {source}: {e}")
            return False

    def retrieve_knowledge(
        self, query: str, limit: int = 5
    ) -> Optional[List[Dict]]:
        """Retrieve relevant knowledge for a query."""
        try:
            
            vector = self.embed_model.encode(query).tolist()
            results_df = query_context(
                self.db_connection,          # db handle
                TABLE_KNOWLEDGE_BASE,        # table name
                vector,                      # query vector
                limit=limit,
            )
            if results_df is None or results_df.empty:
                canvas.warning("No relevant knowledge found.")
                return []

            return [
                {"source": row["source"], "content": row["content"]}
                for _, row in results_df.iterrows()
            ]

        except Exception as e:
            canvas.error(f"Error retrieving knowledge: {e}")
            return None

    def batch_ingest_from_files(self, files: List[Path]) -> int:
        """Ingest multiple files (e.g., markdown docs) into knowledge_base."""
        success_count = 0
        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")
                source = str(file_path)
                if self.ingest_knowledge(source, content):
                    success_count += 1
            except Exception as e:
                canvas.error(f"Failed to ingest {file_path}: {e}")
        canvas.info(f"Batch ingested {success_count}/{len(files)} files.")
        return success_count