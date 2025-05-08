# test_db_access.py
from i2c.db_utils import (
    get_db_connection,
    get_or_create_table,
    TABLE_CODE_CONTEXT,
    SCHEMA_CODE_CONTEXT,
    TABLE_KNOWLEDGE_BASE,
    SCHEMA_KNOWLEDGE_BASE,
)
import time

print("Creating database connection...")
db = get_db_connection()

print(f"Creating table '{TABLE_CODE_CONTEXT}'...")
code_ctx_table = get_or_create_table(db, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT)
print(f"Table created: {code_ctx_table is not None}")

print(f"Creating table '{TABLE_KNOWLEDGE_BASE}'...")
kb_table = get_or_create_table(db, TABLE_KNOWLEDGE_BASE, SCHEMA_KNOWLEDGE_BASE)
print(f"Table created: {kb_table is not None}")

print("\nWaiting 1 second...\n")
time.sleep(1)

# Try to access the tables again
print("Accessing tables again...")
code_ctx_table2 = db.open_table(TABLE_CODE_CONTEXT)
print(f"Could access '{TABLE_CODE_CONTEXT}': {code_ctx_table2 is not None}")

kb_table2 = db.open_table(TABLE_KNOWLEDGE_BASE)
print(f"Could access '{TABLE_KNOWLEDGE_BASE}': {kb_table2 is not None}")

# Try with a fresh connection
print("\nTrying with a fresh connection...")
db2 = get_db_connection()
try:
    code_ctx_table3 = db2.open_table(TABLE_CODE_CONTEXT)
    print(f"Fresh connection could access '{TABLE_CODE_CONTEXT}': {code_ctx_table3 is not None}")
except Exception as e:
    print(f"Fresh connection could not access '{TABLE_CODE_CONTEXT}': {e}")

try:
    kb_table3 = db2.open_table(TABLE_KNOWLEDGE_BASE)
    print(f"Fresh connection could access '{TABLE_KNOWLEDGE_BASE}': {kb_table3 is not None}")
except Exception as e:
    print(f"Fresh connection could not access '{TABLE_KNOWLEDGE_BASE}': {e}")