# /db_utils.py
# Utilities for interacting with the LanceDB vector database.

import lancedb
from pathlib import Path
import pyarrow as pa
from cli.controller import canvas # For logging
import pandas as pd # Import pandas for easier result handling

# --- Configuration ---
DB_PATH = "./data/lancedb" # Store LanceDB data in a subdirectory
TABLE_NAME = "code_context"
# Ensure this matches the embedding model dimension
VECTOR_DIMENSION = 384 # For 'all-MiniLM-L6-v2'

# --- <<< Updated Schema with Static Analysis Metadata >>> ---
SCHEMA = pa.schema([
    pa.field("path", pa.string()),          # Relative path to the file
    pa.field("chunk_name", pa.string()),    # Name of the function/class/chunk
    pa.field("chunk_type", pa.string()),    # 'function', 'class', or 'file'
    pa.field("content", pa.string()),       # The actual code content of the chunk
    pa.field("vector", pa.list_(pa.float32(), list_size=VECTOR_DIMENSION)), # Embedding vector
    # --- New Static Analysis Fields ---
    # Store Ruff results as a list of strings (or potentially structured JSON string)
    pa.field("lint_errors", pa.list_(pa.string())),
    # Store extracted import names as a list of strings
    pa.field("dependencies", pa.list_(pa.string())),
    # Placeholder for future complexity score
    # pa.field("complexity", pa.int32()),
])
# --- <<< End Schema Update >>> ---

def get_db_connection():
    """Establishes a connection to the LanceDB database."""
    db_uri = Path(DB_PATH)
    db_uri.mkdir(parents=True, exist_ok=True)
    try:
        db = lancedb.connect(str(db_uri))
        return db
    except Exception as e:
        canvas.error(f"[DB] Failed to connect to LanceDB at {db_uri}: {e}")
        raise

def get_or_create_table(db: lancedb.db.LanceDBConnection, table_name: str = TABLE_NAME, schema: pa.Schema = SCHEMA) -> lancedb.table.LanceTable | None:
    """Gets a LanceDB table, creating it if it doesn't exist."""
    try:
        table_names = db.table_names()
        if table_name in table_names:
            canvas.info(f"   [DB] Opening existing table: {table_name}")
            tbl = db.open_table(table_name)
            # Basic schema check (more robust checks/migration might be needed)
            if tbl.schema != schema:
                 canvas.warning(f"   [DB] Warning: Table '{table_name}' schema mismatch.")
                 canvas.warning(f"      > Expected: {schema}")
                 canvas.warning(f"      > Found:    {tbl.schema}")
                 canvas.warning(f"      > Delete './data/lancedb' directory if errors occur due to schema change.")
                 # Forcing recreation on mismatch might be safer depending on use case
                 # print(f"   [DB] Recreating table '{table_name}' due to schema mismatch.")
                 # db.drop_table(table_name)
                 # tbl = db.create_table(table_name, schema=schema)
            return tbl
        else:
            canvas.info(f"   [DB] Creating new table: {table_name} with schema:\n{schema}")
            tbl = db.create_table(table_name, schema=schema)
            canvas.info(f"   [DB] Table '{table_name}' created successfully.")
            return tbl
    except Exception as e:
        canvas.error(f"[DB] Failed to open or create table '{table_name}'.")
        canvas.error(f"[DB] Specific Error Type: {type(e).__name__}")
        canvas.error(f"[DB] Specific Error Value: {e}")
        return None

def add_or_update_chunks(table: lancedb.table.LanceTable, file_path: str, chunks: list[dict]):
    """
    Adds/updates context chunks for a specific file.
    Deletes existing chunks for the file first, then adds new ones.

    Args:
        table: The LanceTable instance.
        file_path: The relative path of the file being processed.
        chunks: A list of dictionaries, each representing a chunk with schema fields.
    """
    # Delete existing chunks for this file path first
    try:
        safe_file_path = file_path.replace("'", "''") # Basic SQL quote escaping
        delete_query = f"path = '{safe_file_path}'"
        table.delete(delete_query)
    except Exception as e:
        # It's often okay if delete fails (e.g., table empty or file not previously indexed)
        canvas.warning(f"      [DB] Info: Could not delete existing chunks for {file_path} (might be first time): {e}")

    # Add new chunks
    if chunks:
        try:
            # Ensure data matches the schema before adding (basic check)
            required_keys = set(SCHEMA.names)
            for i, chunk in enumerate(chunks):
                 chunk_keys = set(chunk.keys())
                 if not required_keys.issubset(chunk_keys):
                      missing = required_keys - chunk_keys
                      extra = chunk_keys - required_keys
                      error_msg = f"Chunk data schema mismatch for {file_path} (chunk {i}). Missing: {missing}, Extra: {extra}"
                      canvas.error(f"   ❌ [DB] {error_msg}")
                      # Decide whether to skip this chunk or raise error for the whole batch
                      raise ValueError(error_msg) # Raise error for now

            table.add(chunks)
        except Exception as e:
            canvas.error(f"   ❌ [DB] Error adding chunk data for {file_path}: {e}")
            # Optionally include details about the chunk data that failed
            # canvas.error(f"      Problematic chunk data (first chunk): {chunks[0] if chunks else 'N/A'}")
            raise # Re-raise after logging might be useful here

def query_context(table: lancedb.table.LanceTable, query_vector: list[float], limit: int = 5) -> pd.DataFrame | None:
    """Performs a vector similarity search on the table."""
    if not query_vector or len(query_vector) != VECTOR_DIMENSION:
         canvas.error(f"[DB Query] Invalid query vector provided (length mismatch or None). Expected {VECTOR_DIMENSION} dimensions.")
         return None

    canvas.info(f"   [DB Query] Searching for {limit} most relevant chunks...")
    try:
        results_df = table.search(query_vector)\
                          .select(["path", "chunk_name", "chunk_type", "content"])\
                          .limit(limit)\
                          .to_df()
        canvas.info(f"   [DB Query] Found {len(results_df)} relevant chunk(s).")
        return results_df
    except Exception as e:
        canvas.error(f"   ❌ [DB Query] Error during vector search: {e}")
        return None

