# debug_knowledge_base.py
from i2c.bootstrap import initialize_environment
initialize_environment()

from i2c.db_utils import (
    get_db_connection,
    TABLE_KNOWLEDGE_BASE,
    SCHEMA_KNOWLEDGE_BASE
)
import pyarrow as pa

# Connect to database
db = get_db_connection()
if not db:
    print("Failed to connect to database")
    exit(1)

print("Connected to database successfully")

# Check if knowledge_base table exists
if TABLE_KNOWLEDGE_BASE in db.table_names():
    print(f"Table '{TABLE_KNOWLEDGE_BASE}' exists")
    
    # Try to open it
    try:
        tbl = db.open_table(TABLE_KNOWLEDGE_BASE)
        print(f"Opened table: {tbl}")
        
        # Print schema
        print("\nCurrent schema:")
        for field in tbl.schema:
            print(f"  - {field.name}: {field.type}")
            
        # Compare with target schema
        print("\nTarget schema (V2):")
        for field in SCHEMA_KNOWLEDGE_BASE:
            print(f"  - {field.name}: {field.type}")
            
        # Try to get data
        try:
            df = tbl.to_pandas()
            print(f"\nTable has {len(df)} rows")
            if not df.empty:
                print("Columns:", df.columns.tolist())
                print("\nSample row:")
                print(df.iloc[0].to_dict())
        except Exception as e:
            print(f"Error getting data: {e}")
            
    except Exception as e:
        print(f"Error opening table: {e}")
else:
    print(f"Table '{TABLE_KNOWLEDGE_BASE}' does not exist")
    
    # Try to create it
    try:
        tbl = db.create_table(TABLE_KNOWLEDGE_BASE, schema=SCHEMA_KNOWLEDGE_BASE)
        print(f"Created new table with V2 schema: {tbl}")
    except Exception as e:
        print(f"Error creating table: {e}")