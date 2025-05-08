# reset_knowledge_base.py
from i2c.bootstrap import initialize_environment
initialize_environment()

from i2c.db_utils import get_db_connection, TABLE_KNOWLEDGE_BASE, SCHEMA_KNOWLEDGE_BASE_V2

# Connect to DB
db = get_db_connection()

# Drop the existing empty table
if TABLE_KNOWLEDGE_BASE in db.table_names():
    print(f"Dropping existing '{TABLE_KNOWLEDGE_BASE}' table")
    db.drop_table(TABLE_KNOWLEDGE_BASE)
    
# Create new table with V2 schema
print(f"Creating new '{TABLE_KNOWLEDGE_BASE}' with V2 schema")
tbl = db.create_table(TABLE_KNOWLEDGE_BASE, schema=SCHEMA_KNOWLEDGE_BASE_V2)
print(f"Successfully created table with schema: {tbl.schema}")
print("Done!")