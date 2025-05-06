# src/i2c/scripts/init_lancedb_tables.py
from i2c.bootstrap import initialize_environment
initialize_environment()

from i2c.db_utils import (
    get_db_connection,
    get_or_create_table,
    TABLE_CODE_CONTEXT,
    SCHEMA_CODE_CONTEXT,
    TABLE_KNOWLEDGE_BASE,
    SCHEMA_KNOWLEDGE_BASE,
)

def init_tables():
    db = get_db_connection()
    for name, schema in [
        (TABLE_CODE_CONTEXT,   SCHEMA_CODE_CONTEXT),
        (TABLE_KNOWLEDGE_BASE, SCHEMA_KNOWLEDGE_BASE),
    ]:
        tbl = get_or_create_table(db, name, schema)
        print(f"✅ Table '{name}' ready")

if __name__ == "__main__":
    init_tables()
