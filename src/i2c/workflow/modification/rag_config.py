# workflow/modification/rag_config.py
"""Tiny accessors so any code (or tests) can obtain the RAG resources."""

from pathlib import Path
from typing import Any

# LanceDB – create or connect -------------------------------------------------
def get_rag_table() -> Any | None:
    try:
        import lancedb
        db_path = Path("data/lancedb")
        db = lancedb.connect(db_path)           # will create dir if missing
        return db.open_table("code_chunks")     # or create/open as you wish
    except Exception as e:
        # During unit‑tests we’re fine with no DB.
        print(f"[RAG] No LanceDB table available: {e}")
        return None

# Embedding model -------------------------------------------------------------
def get_embed_model():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as e:
        print(f"[RAG] No embedding model: {e}")
        return None
