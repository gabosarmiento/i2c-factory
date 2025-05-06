# /db_utils.py
# Enhanced utilities for both Code Context and Knowledge Base systems

import lancedb
from pathlib import Path
import pyarrow as pa
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
import json
from datetime import datetime

# Import CLI for logging
try:
    from i2c.cli.controller import canvas
except ImportError:
    # Basic fallback logger
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_DB] {msg}")
        def error(self, msg): print(f"[ERROR_DB] {msg}")
        def info(self, msg): print(f"[INFO_DB] {msg}")
        def success(self, msg): print(f"[SUCCESS_DB] {msg}")
    canvas = FallbackCanvas()

# --- Configuration ---
DB_PATH = "./data/lancedb"            # Store LanceDB data in a subdirectory
TABLE_CODE_CONTEXT = "code_context"    # Table for code chunks
TABLE_KNOWLEDGE_BASE = "knowledge_base" # Table for external knowledge
VECTOR_DIMENSION = 384                 # For 'all-MiniLM-L6-v2'

# --- Schema for Code Context Table ---
SCHEMA_CODE_CONTEXT = pa.schema([
    pa.field("path", pa.string()),
    pa.field("chunk_name", pa.string()),
    pa.field("chunk_type", pa.string()),
    pa.field("content", pa.string()),
    pa.field("vector", pa.list_(pa.float32(), list_size=VECTOR_DIMENSION)),
    pa.field("lint_errors", pa.list_(pa.string())),
    pa.field("dependencies", pa.list_(pa.string())),
    pa.field("start_line", pa.int32()),
    pa.field("end_line", pa.int32()),
    pa.field("content_hash", pa.string()),
    pa.field("language", pa.string()),
])

# --- Original Schema for Knowledge Base Table (v1) ---
SCHEMA_KNOWLEDGE_BASE = pa.schema([
    pa.field("source", pa.string()),
    pa.field("content", pa.string()),
    pa.field("vector", pa.list_(pa.float32(), list_size=VECTOR_DIMENSION)),
    pa.field("category", pa.string()),
    pa.field("last_updated", pa.string()),
])

# --- Extended Schema for Knowledge Base Table (v2) ---
SCHEMA_KNOWLEDGE_BASE_V2 = pa.schema([
    pa.field("source", pa.string()),
    pa.field("content", pa.string()),
    pa.field("vector", pa.list_(pa.float32(), list_size=VECTOR_DIMENSION)),
    pa.field("category", pa.string()),
    pa.field("last_updated", pa.string()),
    pa.field("knowledge_space", pa.string()),
    pa.field("document_type", pa.string()),
    pa.field("framework", pa.string()),
    pa.field("version", pa.string()),
    pa.field("parent_doc_id", pa.string()),
    pa.field("chunk_type", pa.string()),
    pa.field("source_hash", pa.string()),
    pa.field("metadata_json", pa.string()),
])

# --- Core DB Helpers ---

def get_db_connection() -> Optional[lancedb.db.LanceDBConnection]:
    """Establishes a connection to the LanceDB database."""
    db_uri = Path(DB_PATH)
    db_uri.mkdir(parents=True, exist_ok=True)
    try:
        return lancedb.connect(str(db_uri))
    except Exception as e:
        canvas.error(f"[DB] Failed to connect to LanceDB at {db_uri}: {e}")
        return None


def get_or_create_table(
    db: lancedb.db.LanceDBConnection,
    table_name: str,
    schema: pa.Schema
) -> Optional[lancedb.table.LanceTable]:
    """Gets or creates a LanceDB table with a specific schema."""
    try:
        if table_name in db.table_names():
            tbl = db.open_table(table_name)
            if tbl.schema != schema:
                canvas.warning(f"[DB] Schema mismatch for '{table_name}'")
                return None
            return tbl
        else:
            canvas.info(f"[DB] Creating table '{table_name}'")
            return db.create_table(table_name, schema=schema)
    except Exception as e:
        canvas.error(f"[DB] Open/create table '{table_name}' failed: {e}")
        return None

# --- Migration-Enabled Table Getter ---

def get_or_create_table_with_migration(
    db: lancedb.db.LanceDBConnection,
    table_name: str,
    base_schema: pa.Schema,
    target_schema: pa.Schema
) -> Optional[lancedb.table.LanceTable]:
    """Gets or creates a table, migrating schema from base to target if needed."""
    try:
        if table_name in db.table_names():
            tbl = db.open_table(table_name)
            if tbl.schema == target_schema:
                return tbl
            # migrate
            canvas.info(f"[DB] Migrating '{table_name}' to v2 schema...")
            df = tbl.to_pandas()
            rows: List[Dict[str, Any]] = []
            for _, r in df.iterrows():
                new_r = {}
                for f in target_schema.names:
                    if f in df.columns:
                        new_r[f] = r[f]
                    else:
                        if f == "knowledge_space": new_r[f] = "default"
                        elif f == "last_updated": new_r[f] = r.get("last_updated", datetime.now().isoformat())
                        elif f == "metadata_json": new_r[f] = json.dumps({})
                        else: new_r[f] = None
                rows.append(new_r)
            # replace table
            db.drop_table(table_name)
            return db.create_table(table_name, data=rows, schema=target_schema)
        else:
            canvas.info(f"[DB] Creating new migrated table '{table_name}'")
            return db.create_table(table_name, schema=target_schema)
    except Exception as e:
        canvas.error(f"[DB] Migration for '{table_name}' failed: {e}")
        return None

# --- Chunk Upsert for Code & Knowledge ---

def add_or_update_chunks(
    db: lancedb.db.LanceDBConnection,
    table_name: str,
    schema: pa.Schema,
    identifier_field: str,
    identifier_value: str,
    chunks: List[Dict[str, Any]]
) -> None:
    table = get_or_create_table(db, table_name, schema)
    if table is None:
        raise ConnectionError(f"Table '{table_name}' inaccessible")
    # delete old
    try:
        table.delete(f"""{identifier_field} = '{identifier_value.replace("'", "''")}'""")
    except Exception:
        pass
    # insert new
    if chunks:
        table.add(chunks)

# --- Basic Query Context ---

def query_context(
    db: lancedb.db.LanceDBConnection,
    table_name: str,
    query_vector: List[float],
    limit: int = 5
) -> Optional[pd.DataFrame]:
    try:
        tbl = db.open_table(table_name)
        exp_dim = tbl.schema.field("vector").type.list_size
        if len(query_vector) != exp_dim:
            canvas.error(f"Invalid vector length {len(query_vector)} != {exp_dim}")
            return None
        df = tbl.search(query_vector).select([n for n in tbl.schema.names if n!="vector"]).limit(limit).to_df()
        return df
    except Exception as e:
        canvas.error(f"[DB] query_context error: {e}")
        return None

# --- Enhanced Knowledge API ---

def query_context_filtered(
    db: lancedb.db.LanceDBConnection,
    table_name: str,
    query_vector: List[float],
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 5
) -> Optional[pd.DataFrame]:
    try:
        tbl = db.open_table(table_name)
        exp_dim = tbl.schema.field("vector").type.list_size
        if len(query_vector) != exp_dim:
            canvas.error("Invalid vector length for filtered query")
            return None
        q = tbl.search(query_vector)
        if filters:
            conds = []
            for k,v in filters.items():
                conds.append(f"{k} = '{v}'")
            q = q.where(" AND ".join(conds))
        df = q.select([n for n in tbl.schema.names if n!="vector"]).limit(limit).to_df()
        return df
    except Exception as e:
        canvas.error(f"[DB] query_context_filtered error: {e}")
        return None

# --- Knowledge Chunk Convenience ---

def add_knowledge_chunks(
    db: lancedb.db.LanceDBConnection,
    chunks: List[Dict[str, Any]],
    knowledge_space: str = "default"
) -> bool:
    tbl = get_or_create_table_with_migration(
        db,
        TABLE_KNOWLEDGE_BASE,
        SCHEMA_KNOWLEDGE_BASE,
        SCHEMA_KNOWLEDGE_BASE_V2
    )
    if tbl is None:
        return False
    prepared = []
    for c in chunks:
        chunk = c.copy()
        chunk.setdefault("knowledge_space", knowledge_space)
        chunk.setdefault("last_updated", datetime.now().isoformat())
        if "metadata" in chunk and isinstance(chunk["metadata"], dict):
            chunk["metadata_json"] = json.dumps(chunk.pop("metadata"))
        if "metadata_json" not in chunk:
            chunk["metadata_json"] = json.dumps({})
        prepared.append(chunk)
    tbl.add(prepared)
    canvas.success(f"[DB] Added {len(prepared)} knowledge chunks")
    return True

# --- Utilities ---

def list_knowledge_spaces(db: lancedb.db.LanceDBConnection) -> List[str]:
    try:
        df = db.open_table(TABLE_KNOWLEDGE_BASE).to_pandas()
        return df.get("knowledge_space", pd.Series(["default"])).unique().tolist()
    except Exception:
        return ["default"]


def migrate_knowledge_base(db: lancedb.db.LanceDBConnection) -> bool:
    tbl = get_or_create_table_with_migration(
        db,
        TABLE_KNOWLEDGE_BASE,
        SCHEMA_KNOWLEDGE_BASE,
        SCHEMA_KNOWLEDGE_BASE_V2
    )
    return tbl is not None

# --- Initialization ---
def initialize_db() -> Optional[lancedb.db.LanceDBConnection]:
    """Initialize database, create or migrate tables."""
    db = get_db_connection()
    if not db:
        canvas.error("[DB Init] Connection failed")
        return None

    code_context_failed = False
    # --- Optional code_context setup ---
    try:
        get_or_create_table(db, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT)
    except Exception as e:
        code_context_failed = True
        canvas.warning(
            "[DB Init] code_context table setup issue; proceeding without context: %s",
            e
        )

    # --- Critical knowledge_base migration ---
    try:
        ok = get_or_create_table_with_migration(
            db,
            TABLE_KNOWLEDGE_BASE,
            SCHEMA_KNOWLEDGE_BASE,
            SCHEMA_KNOWLEDGE_BASE_V2
        )
        if not ok:
            canvas.error("[DB Init] knowledge_base migration failed")
            return None
    except Exception as e:
        canvas.error(f"[DB Init] knowledge_base table setup issue: {e}")
        return None

    # Success message reflects whether code_context is available
    suffix = " (code_context unavailable)" if code_context_failed else ""
    canvas.success(f"[DB Init] Database ready with Knowledge Base v2{suffix}")

    # You could attach an attribute here: db.context_available = not code_context_failed
    return db