# scripts/fix_db_connection.py
"""Fix database connection issues"""

import os
from pathlib import Path

def fix_db_connection():
    """Create necessary directories and fix DB connection"""
    # Create data directory if it doesn't exist
    data_dir = Path("./data/lancedb")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a simple test to verify LanceDB connection
    try:
        import lancedb
        db = lancedb.connect(str(data_dir))
        print(f"✓ Successfully connected to LanceDB at {data_dir}")
        
        # Try to create a test table
        import pyarrow as pa
        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("content", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), 384))
        ])
        
        # Check if test table exists or create it
        if "test_table" in db.table_names():
            print("✓ Test table already exists")
        else:
            db.create_table("test_table", schema=schema)
            print("✓ Created test table successfully")
            
    except Exception as e:
        print(f"✗ Error with LanceDB: {e}")
        print("You may need to install lancedb: pip install lancedb")


if __name__ == "__main__":
    fix_db_connection()