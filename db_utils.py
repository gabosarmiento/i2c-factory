# /db_utils.py
# Utilities for interacting with the LanceDB vector database.

import lancedb
from pathlib import Path
import pyarrow as pa
import pandas as pd
from typing import Optional

# Import CLI for logging
try:
    from cli.controller import canvas
except ImportError:
    # Basic fallback logger
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_DB] {msg}")
        def error(self, msg): print(f"[ERROR_DB] {msg}")
        def info(self, msg): print(f"[INFO_DB] {msg}")
        def success(self, msg): print(f"[SUCCESS_DB] {msg}")
    canvas = FallbackCanvas()


# --- Configuration ---
DB_PATH = "./data/lancedb" # Store LanceDB data in a subdirectory
TABLE_CODE_CONTEXT = "code_context" # Table for code chunks
TABLE_KNOWLEDGE_BASE = "knowledge_base" # Table for external knowledge
VECTOR_DIMENSION = 384 # For 'all-MiniLM-L6-v2'

# --- Schema for Code Context Table ---
SCHEMA_CODE_CONTEXT = pa.schema([
    pa.field("path", pa.string()),          # Relative path to the file
    pa.field("chunk_name", pa.string()),    # Name of the function/class/chunk
    pa.field("chunk_type", pa.string()),    # 'function', 'class', or 'file', 'file_parse_error', etc.
    pa.field("content", pa.string()),       # The actual code content of the chunk
    pa.field("vector", pa.list_(pa.float32(), list_size=VECTOR_DIMENSION)), # Embedding vector
    # --- Static Analysis Metadata ---
    pa.field("lint_errors", pa.list_(pa.string())), # List of lint errors/warnings from Ruff
    pa.field("dependencies", pa.list_(pa.string())),# List of imported modules
    # --- Chunk Metadata ---
    pa.field("start_line", pa.int32()),      # Starting line number of the chunk (-1 if N/A)
    pa.field("end_line", pa.int32()),        # Ending line number of the chunk (-1 if N/A)
    pa.field("content_hash", pa.string()),   # SHA256 hash of the chunk content
    pa.field("language", pa.string()),      # Programming language (e.g., 'python')
])

# --- Schema for Knowledge Base Table ---
SCHEMA_KNOWLEDGE_BASE = pa.schema([
    pa.field("source", pa.string()),    # Source identifier (e.g., filename, URL)
    pa.field("content", pa.string()),   # The text chunk content
    pa.field("vector", pa.list_(pa.float32(), list_size=VECTOR_DIMENSION)),
    # Add other metadata as needed (e.g., page_number, chunk_index)
])


def get_db_connection() -> Optional[lancedb.db.LanceDBConnection]:
    """Establishes a connection to the LanceDB database."""
    db_uri = Path(DB_PATH)
    db_uri.mkdir(parents=True, exist_ok=True)
    try:
        db = lancedb.connect(str(db_uri))
        return db
    except Exception as e:
        canvas.error(f"[DB] Failed to connect to LanceDB at {db_uri}: {e}")
        return None # Return None on failure

def get_or_create_table(db: lancedb.db.LanceDBConnection, table_name: str, schema: pa.Schema) -> Optional[lancedb.table.LanceTable]:
    """Gets a LanceDB table with a specific name and schema, creating it if it doesn't exist."""
    try:
        table_names = db.table_names()
        if table_name in table_names:
            # canvas.info(f"   [DB] Opening existing table: {table_name}") # Reduce verbosity
            tbl = db.open_table(table_name)
            # Basic schema check
            if tbl.schema != schema:
                 canvas.warning(f"   [DB] Warning: Table '{table_name}' schema mismatch.")
                 canvas.warning(f"      > Expected: {schema}")
                 canvas.warning(f"      > Found:    {tbl.schema}")
                 canvas.error(f"   [DB] Critical Schema Mismatch for table '{table_name}'. Delete './data/lancedb' and restart.")
                 return None # Fail hard on schema mismatch
            return tbl
        else:
            canvas.info(f"   [DB] Creating new table: {table_name} with schema...")
            # canvas.info(f"{schema}") # Optional: Log schema details
            tbl = db.create_table(table_name, schema=schema)
            canvas.info(f"   [DB] Table '{table_name}' created successfully.")
            return tbl
    except Exception as e:
        canvas.error(f"[DB] Failed to open or create table '{table_name}'.")
        canvas.error(f"[DB] Specific Error Type: {type(e).__name__}")
        canvas.error(f"[DB] Specific Error Value: {e}")
        return None

def add_or_update_chunks(db: lancedb.db.LanceDBConnection, table_name: str, schema: pa.Schema, identifier_field: str, identifier_value: str, chunks: list[dict]):
    """
    Adds/updates context chunks for a specific identifier.
    Deletes existing chunks first, then adds new ones.
    """
    table = get_or_create_table(db, table_name, schema)
    if table is None:
        canvas.error(f"[DB] Cannot add/update chunks: Failed to get table '{table_name}'.")
        raise ConnectionError(f"Could not access table '{table_name}'") # Raise error

    # Delete existing chunks for this identifier first
    try:
        safe_identifier_value = identifier_value.replace("'", "''")
        delete_query = f"{identifier_field} = '{safe_identifier_value}'"
        delete_count = table.delete(delete_query)
        # if delete_count > 0:
        #     canvas.info(f"      [DB] Deleted {delete_count} existing chunk(s) for identifier: {identifier_value}")
    except Exception as e:
        canvas.warning(f"      [DB] Info: Could not delete existing chunks for {identifier_value} in {table_name}: {e}")

    # Add new chunks
    if chunks:
        try:
            # Basic schema validation before adding
            required_keys = set(schema.names)
            validated_chunks = []
            for i, chunk in enumerate(chunks):
                 chunk_keys = set(chunk.keys())
                 if not required_keys.issubset(chunk_keys):
                      missing = required_keys - chunk_keys
                      extra = chunk_keys - required_keys
                      canvas.warning(f"   ⚠️ Chunk data schema mismatch for {identifier_value} (chunk {i}) in table '{table_name}'. Missing: {missing}, Extra: {extra}. Skipping chunk.")
                      continue # Skip this chunk

                 # Ensure types match schema (basic attempt)
                 for field in schema:
                     key = field.name
                     expected_type = field.type
                     value = chunk.get(key)
                     # Basic type checks - LanceDB might handle more complex conversions
                     if isinstance(expected_type, pa.ListType) and not isinstance(value, list):
                          chunk[key] = [] if value is None else [value] # Attempt simple conversion
                     elif pa.types.is_integer(expected_type) and not isinstance(value, int):
                          chunk[key] = int(value) if value is not None else -1 # Default int
                     elif pa.types.is_string(expected_type) and not isinstance(value, str):
                          chunk[key] = str(value) if value is not None else "" # Default string
                     # Add more type checks as needed

                 validated_chunks.append(chunk)

            if validated_chunks:
                table.add(validated_chunks)
                # canvas.info(f"      [DB] Added/Updated {len(validated_chunks)} chunks for: {identifier_value} in table '{table_name}'")
            elif chunks: # If we had chunks initially but none were valid
                 canvas.warning(f"      [DB] No valid chunks to add for {identifier_value} after validation.")

        except Exception as e:
            canvas.error(f"   ❌ [DB] Error adding chunk data for {identifier_value} in table '{table_name}': {e}")
            raise # Re-raise after logging


def query_context(db: lancedb.db.LanceDBConnection, table_name: str, query_vector: list[float], limit: int = 5) -> pd.DataFrame | None:
    """
    Performs a vector similarity search on the specified table.
    """
    try:
        table = db.open_table(table_name) # Assume table exists for querying
    except Exception as e: # Catch error if table doesn't exist
         canvas.error(f"[DB Query] Failed to open table '{table_name}': {e}")
         return None

    # Check vector dimension against the table schema
    try:
        schema_vector_field = table.schema.get_field_index("vector")
        if schema_vector_field == -1:
             canvas.error(f"[DB Query] Table '{table_name}' does not have a 'vector' field.")
             return None
        expected_dimension = table.schema.field("vector").type.list_size
    except Exception as e:
         canvas.error(f"[DB Query] Error accessing schema for table '{table_name}': {e}")
         return None


    if not query_vector or len(query_vector) != expected_dimension:
         canvas.error(f"[DB Query] Invalid query vector. Expected {expected_dimension}, got {len(query_vector) if query_vector else 'None'}.")
         return None

    canvas.info(f"   [DB Query] Searching table '{table_name}' for {limit} most relevant chunks...")
    try:
        # Select all fields except the vector itself for the result
        select_cols = [field.name for field in table.schema if field.name != 'vector']
        results_df = table.search(query_vector)\
                          .select(select_cols)\
                          .limit(limit)\
                          .to_df()
        canvas.info(f"   [DB Query] Found {len(results_df)} relevant chunk(s).")
        return results_df
    except Exception as e:
        canvas.error(f"   ❌ [DB Query] Error during vector search on table '{table_name}': {e}")
        return None

# ------ Add these debug functions to your db_utils.py --------


def verify_db_connection(db_path: str = DB_PATH) -> bool:
    """Verifies the database connection with detailed logging."""
    from pathlib import Path
    
    # Check if directory exists and is writable
    path = Path(db_path)
    canvas.info(f"[DB Debug] Checking DB path: {path.absolute()}")
    
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
            canvas.info(f"[DB Debug] Created DB directory: {path.absolute()}")
        except Exception as e:
            canvas.error(f"[DB Debug] Failed to create DB directory: {e}")
            return False
    
    # Check write permissions by creating a test file
    try:
        test_file = path / "test_write.txt"
        with open(test_file, 'w') as f:
            f.write("Test write access")
        test_file.unlink()  # Delete the test file
        canvas.info(f"[DB Debug] Directory is writable: {path.absolute()}")
    except Exception as e:
        canvas.error(f"[DB Debug] Directory is not writable: {e}")
        return False
    
    # Try to establish connection with more detailed logging
    try:
        db = lancedb.connect(str(path))
        canvas.info(f"[DB Debug] Successfully connected to LanceDB at {path.absolute()}")
        
        # Test basic operations
        try:
            table_names = db.table_names()
            canvas.info(f"[DB Debug] Successfully listed tables: {table_names}")
            return True
        except Exception as e:
            canvas.error(f"[DB Debug] Connected but failed to list tables: {e}")
            return False
            
    except Exception as e:
        canvas.error(f"[DB Debug] Failed to connect to LanceDB: {e}")
        return False

def initialize_db():
    """Initialize database with better error handling and debugging."""
    from pathlib import Path
    import shutil
    import os
    
    # If DB path exists but is corrupted, try to reset it
    db_path = Path(DB_PATH)
    if db_path.exists():
        try:
            # Try to connect first
            db = get_db_connection()
            if db is None:
                canvas.warning(f"[DB Init] Connection failed, attempting to reset DB at {db_path}")
                # Backup the old DB directory first
                backup_path = db_path.with_name(f"{db_path.name}_backup")
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                shutil.move(db_path, backup_path)
                canvas.info(f"[DB Init] Backed up old DB to {backup_path}")
                # Create fresh directory
                db_path.mkdir(parents=True, exist_ok=True)
                # Try connection again
                db = get_db_connection()
        except Exception as e:
            canvas.error(f"[DB Init] Failed to reset database: {e}")
            return None
    else:
        # Create directory and connect
        db_path.mkdir(parents=True, exist_ok=True)
        db = get_db_connection()
    
    if db is None:
        canvas.error("[DB Init] Could not establish database connection")
        return None
        
    # Test table creation
    test_table = get_or_create_table(db, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT)
    if test_table is None:
        canvas.error("[DB Init] Table creation failed")
        return None
        
    canvas.success("[DB Init] Database initialized successfully")
    return db