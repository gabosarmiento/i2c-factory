# Run this as a one-time fix to make sure tables are created correctly
import lancedb
from pathlib import Path
import pyarrow as pa

# Configuration
DB_PATH = "./data/lancedb"
TABLE_CODE_CONTEXT = "code_context"
TABLE_KNOWLEDGE_BASE = "knowledge_base"
VECTOR_DIMENSION = 384

# Schema definitions
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

# Start fresh
import shutil
try:
    shutil.rmtree(DB_PATH)
    print(f"Removed existing database at {DB_PATH}")
except:
    pass

# Create the database directory
Path(DB_PATH).mkdir(parents=True, exist_ok=True)

# Connect and create tables
db = lancedb.connect(DB_PATH)

# Create tables
try:
    if TABLE_CODE_CONTEXT in db.table_names():
        db.drop_table(TABLE_CODE_CONTEXT)
    db.create_table(TABLE_CODE_CONTEXT, schema=SCHEMA_CODE_CONTEXT)
    print(f"Created table {TABLE_CODE_CONTEXT}")
except Exception as e:
    print(f"Error creating {TABLE_CODE_CONTEXT}: {e}")

try:
    if TABLE_KNOWLEDGE_BASE in db.table_names():
        db.drop_table(TABLE_KNOWLEDGE_BASE)
    db.create_table(TABLE_KNOWLEDGE_BASE, schema=SCHEMA_KNOWLEDGE_BASE)
    print(f"Created table {TABLE_KNOWLEDGE_BASE}")
except Exception as e:
    print(f"Error creating {TABLE_KNOWLEDGE_BASE}: {e}")

print("Database reset complete.")