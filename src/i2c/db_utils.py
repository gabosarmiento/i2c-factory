# /db_utils.py
# Enhanced utilities for both Code Context and Knowledge Base systems
'''To reset the database, you can add a --recreate-db flag 
   just run poetry run i2c --recreate-db when you need to reset the database, 
   instead of manually deleting the directory.
'''
import lancedb
from pathlib import Path
import pyarrow as pa
import pandas as pd
from typing import Optional, Dict, Any, List
import json
from datetime import datetime

# Import CLI for logging
try:
    from i2c.cli.controller import canvas
except ImportError:
    # Basic fallback logger
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARNING]: {msg}")
        def error(self, msg): print(f"[ERROR]: {msg}")
        def info(self, msg): print(f"[INFO]: {msg}")
        def success(self, msg): print(f"[SUCCESS]: {msg}")
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

# --- Schema for Knowledge Base Table (Unified V2 Schema) ---
SCHEMA_KNOWLEDGE_BASE = pa.schema([
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
        canvas.error(f"Failed to connect to LanceDB at {db_uri}: {e}")
        return None

# def get_or_create_table(
#     db: lancedb.db.LanceDBConnection,
#     table_name: str,
#     schema: pa.Schema,
#     force_recreate: bool = False
# ) -> Optional[lancedb.table.LanceTable]:
#     """Gets or creates a LanceDB table with a specific schema.
    
#     Args:
#         db: LanceDB connection
#         table_name: Name of the table
#         schema: PyArrow schema defining the table structure
#         force_recreate: If True, drops and recreates the table even if it exists
        
#     Returns:
#         LanceTable object or None if operation fails
#     """
#     try:
#         # Handle force recreation
#         if force_recreate and table_name in db.table_names():
#             canvas.info(f"Dropping existing {table_name} table")
#             try:
#                 db.drop_table(table_name)
#             except Exception as e:
#                 canvas.warning(f"Error dropping table {table_name}: {e}")
                
#         # Check if table exists
#         if table_name in db.table_names():
#             tbl = db.open_table(table_name)
#             # Debug: Print schema equality check details
#             canvas.info(f"Schema equality check for {table_name}: {tbl.schema == schema}")
#             canvas.info(f"Schema hash comparison: {hash(str(tbl.schema))} vs {hash(str(schema))}")
            
#             # Additional debug for field-by-field comparison
#             tbl_fields = {f.name: (str(f.type), f.nullable) for f in tbl.schema}
#             schema_fields = {f.name: (str(f.type), f.nullable) for f in schema}
            
#             # Check fields and properties
#             for name in schema_fields:
#                 if name not in tbl_fields:
#                     canvas.error(f"Field {name} missing in table schema")
#                 elif tbl_fields[name] != schema_fields[name]:
#                     canvas.error(f"Field {name} differs: table={tbl_fields[name]}, expected={schema_fields[name]}")
            
#             # Check the list of field names matches exactly
#             if set(tbl_fields.keys()) != set(schema_fields.keys()):
#                 canvas.error(f"Field sets don't match: table has {set(tbl_fields.keys())}, expected {set(schema_fields.keys())}")
            
#             # Check for schema compatibility
#             if tbl.schema != schema:
#                 canvas.error(f"Table schema: {tbl.schema}")
#                 canvas.error(f"Expected schema: {schema}")
#                 canvas.error(f"Schema mismatch for '{table_name}'. Use force_recreate=True to reset.")
#                 return None
#             return tbl
#         else:
#             canvas.info(f"Creating {table_name} table")
#             return db.create_table(table_name, schema=schema)
#     except Exception as e:
#         canvas.error(f"Open/create table '{table_name}' failed: {e}")
#         return None
def get_or_create_table(
    db: lancedb.db.LanceDBConnection,
    table_name: str,
    schema: pa.Schema,
    force_recreate: bool = False
) -> Optional[lancedb.table.LanceTable]:
    """Gets or creates a LanceDB table with a specific schema."""
    try:
        # Handle force recreation
        if force_recreate and table_name in db.table_names():
            canvas.info(f"Dropping existing {table_name} table")
            try:
                db.drop_table(table_name)
            except Exception as e:
                canvas.warning(f"Error dropping table {table_name}: {e}")
                
        # Check if table exists
        if table_name in db.table_names():
            try:
                tbl = db.open_table(table_name)
            except Exception as e:
                canvas.error(f"Error opening existing table '{table_name}': {e}")
                return None
            
            # Schema equality check (already passing based on logs)
            canvas.info(f"Schema equality check for {table_name}: {tbl.schema == schema}")
            
            # Check for schema compatibility
            if tbl.schema != schema:
                canvas.error(f"Schema mismatch for '{table_name}'. Use force_recreate=True to reset.")
                return None
                
            # Table access check - try to perform a simple operation
            try:
                canvas.info(f"Testing table '{table_name}' access...")
                # Try to get row count or perform a simple query
                count = tbl.count_rows()
                canvas.info(f"Table '{table_name}' has {count} rows")
                return tbl
            except Exception as e:
                canvas.error(f"Table '{table_name}' access test failed: {e}")
                return None
        else:
            canvas.info(f"Creating {table_name} table")
            try:
                new_tbl = db.create_table(table_name, schema=schema)
                canvas.info(f"Successfully created table '{table_name}'")
                return new_tbl
            except Exception as e:
                canvas.error(f"Error creating table '{table_name}': {e}")
                return None
    except Exception as e:
        canvas.error(f"Open/create table '{table_name}' failed: {e}")
        return None
# --- Chunk Upsert for Code & Knowledge ---

def add_or_update_chunks(
    db: lancedb.db.LanceDBConnection,
    table_name: str,
    schema: pa.Schema,
    identifier_field: str,
    identifier_value: str,
    chunks: List[Dict[str, Any]]
) -> bool:
    """Add or update chunks in a table, removing existing ones with the same identifier.
    
    Args:
        db: LanceDB connection
        table_name: Name of the table
        schema: Schema for the table
        identifier_field: Field name to use for identifying existing chunks
        identifier_value: Value of the identifier to match
        chunks: List of chunk dictionaries to add
        
    Returns:
        True if operation succeeds, False otherwise
    """
    table = get_or_create_table(db, table_name, schema)
    if table is None:
        canvas.error(f"Table '{table_name}' inaccessible")
        return False
        
    # Delete old chunks with the same identifier
    try:
        table.delete(f"""{identifier_field} = '{identifier_value.replace("'", "''")}'""")
    except Exception as e:
        canvas.warning(f"Error deleting existing chunks: {e}")
        
    # Insert new chunks if any
    if chunks:
        try:
            table.add(chunks)
            canvas.success(f"Added {len(chunks)} chunks to {table_name}")
            return True
        except Exception as e:
            canvas.error(f"Error adding chunks to {table_name}: {e}")
            return False
    
    return True  # No chunks to add is still a success

# --- Basic Query Context ---

def query_context(
    db: lancedb.db.LanceDBConnection,
    table_name: str,
    query_vector: List[float],
    limit: int = 5
) -> Optional[pd.DataFrame]:
    """Search for similar contexts using vector similarity.
    
    Args:
        db: LanceDB connection
        table_name: Name of the table to search
        query_vector: Vector representation of the query
        limit: Maximum number of results to return
        
    Returns:
        DataFrame with search results or None if search fails
    """
    try:
        tbl = db.open_table(table_name)
        exp_dim = tbl.schema.field("vector").type.list_size
        
        # Validate vector dimensions
        if len(query_vector) != exp_dim:
            canvas.error(f"Invalid vector length {len(query_vector)} != {exp_dim}")
            return None
            
        # Execute search
        df = tbl.search(query_vector).select([n for n in tbl.schema.names if n != "vector"]).limit(limit).to_df()
        return df
    except Exception as e:
        canvas.error(f"query_context error: {e}")
        return None

# --- Enhanced Knowledge API ---

def query_context_filtered(
    db: lancedb.db.LanceDBConnection,
    table_name: str,
    query_vector: List[float],
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 5
) -> Optional[pd.DataFrame]:
    """Search for similar contexts with additional filters.
    
    Args:
        db: LanceDB connection
        table_name: Name of the table to search
        query_vector: Vector representation of the query
        filters: Dictionary of field:value pairs to filter results
        limit: Maximum number of results to return
        
    Returns:
        DataFrame with search results or None if search fails
    """
    try:
        tbl = db.open_table(table_name)
        exp_dim = tbl.schema.field("vector").type.list_size
        
        # Validate vector dimensions
        if len(query_vector) != exp_dim:
            canvas.error("Invalid vector length for filtered query")
            return None
            
        # Start search query
        q = tbl.search(query_vector)
        
        # Add filters if provided
        if filters:
            conds = []
            for k, v in filters.items():
                if isinstance(v, str):
                    escaped_v = v.replace("'", "''")
                    conds.append(f"{k} = '{escaped_v}'")
                else:
                    conds.append(f"{k} = {v}")
            
            if conds:
                q = q.where(" AND ".join(conds))
        
        # Execute query
        df = q.select([n for n in tbl.schema.names if n != "vector"]).limit(limit).to_df()
        return df
    except Exception as e:
        canvas.error(f"query_context_filtered error: {e}")
        return None

# --- Knowledge Chunk Convenience ---

def add_knowledge_chunks(
    db: lancedb.db.LanceDBConnection,
    chunks: List[Dict[str, Any]],
    knowledge_space: str = "default"
) -> bool:
    """Add knowledge chunks to the knowledge base table.
    
    Args:
        db: LanceDB connection
        chunks: List of chunk dictionaries to add
        knowledge_space: Namespace for the knowledge chunks
        
    Returns:
        True if successful, False otherwise
    """
    tbl = get_or_create_table(db, TABLE_KNOWLEDGE_BASE, SCHEMA_KNOWLEDGE_BASE)
    if tbl is None:
        canvas.error("Failed to access knowledge_base table")
        return False
        
    prepared = []
    for c in chunks:
        # Create a copy to avoid modifying the original
        chunk = c.copy()
        
        # Set default values for required fields
        chunk.setdefault("knowledge_space", knowledge_space)
        chunk.setdefault("last_updated", datetime.now().isoformat())
        chunk.setdefault("category", chunk.get("category", "general"))
        chunk.setdefault("document_type", chunk.get("document_type", "text"))
        chunk.setdefault("framework", chunk.get("framework", ""))
        chunk.setdefault("version", chunk.get("version", ""))
        chunk.setdefault("parent_doc_id", chunk.get("parent_doc_id", ""))
        chunk.setdefault("chunk_type", chunk.get("chunk_type", "text"))
        chunk.setdefault("source_hash", chunk.get("source_hash", ""))
        
        # Handle metadata
        if "metadata" in chunk and isinstance(chunk["metadata"], dict):
            chunk["metadata_json"] = json.dumps(chunk.pop("metadata"))
        if "metadata_json" not in chunk:
            chunk["metadata_json"] = json.dumps({})
            
        prepared.append(chunk)
    
    # Add to database
    try:
        tbl.add(prepared)
        canvas.success(f"Added {len(prepared)} knowledge chunks")
        return True
    except Exception as e:
        canvas.error(f"Error adding knowledge chunks: {e}")
        return False

# --- Utilities ---

def list_knowledge_spaces(db: lancedb.db.LanceDBConnection) -> List[str]:
    """List all knowledge spaces in the knowledge base.
    
    Args:
        db: LanceDB connection
        
    Returns:
        List of knowledge space names
    """
    try:
        df = db.open_table(TABLE_KNOWLEDGE_BASE).to_pandas()
        if 'knowledge_space' in df.columns:
            return df['knowledge_space'].unique().tolist()
        return ["default"]
    except Exception as e:
        canvas.warning(f"Error listing knowledge spaces: {e}")
        return ["default"]

# --- Initialization ---
def initialize_db(force_recreate: bool = False) -> Optional[lancedb.db.LanceDBConnection]:
    """Initialize database, create tables if needed.
    
    Args:
        force_recreate: If True, drop and recreate all tables
        
    Returns:
        Database connection or None if initialization fails
    """
    # Get database connection
    db = get_db_connection()
    if not db:
        canvas.error("Database connection failed")
        return None

    # Initialize code_context table
    canvas.info("Initializing code_context table...")
    code_ctx_tbl = get_or_create_table(
        db, 
        TABLE_CODE_CONTEXT, 
        SCHEMA_CODE_CONTEXT,
        force_recreate=force_recreate
    )
    
    if not code_ctx_tbl:
        canvas.error("Failed to initialize code_context table")
        # Continue anyway - we can still work with knowledge_base
        
    # Initialize knowledge_base table
    canvas.info("Initializing knowledge_base table...")
    kb_tbl = get_or_create_table(
        db, 
        TABLE_KNOWLEDGE_BASE, 
        SCHEMA_KNOWLEDGE_BASE,
        force_recreate=force_recreate
    )
    
    if not kb_tbl:
        canvas.error("Failed to initialize knowledge_base table")
        return None
        
    canvas.success("Database tables created successfully")
    return db