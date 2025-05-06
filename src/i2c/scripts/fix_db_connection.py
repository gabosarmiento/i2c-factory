# src/i2c/scripts/fix_db_connection.py
"""Fix database connection issues"""

from pathlib import Path
from i2c.bootstrap import initialize_environment,PROJECT_ROOT
import builtins  
# 1) Bootstrap env & builtins (including PROJECT_ROOT)
initialize_environment()

def fix_db_connection():
    """Create necessary directories and fix LanceDB connection"""
    # 2) Use the injected PROJECT_ROOT
    data_dir = PROJECT_ROOT / "data" / "lancedb"
    data_dir.mkdir(parents=True, exist_ok=True)

    try:
        import lancedb
        db = lancedb.connect(str(data_dir))
        print(f"✓ Connected to LanceDB at {data_dir}")

        import pyarrow as pa
        schema = pa.schema([
            pa.field("id",      pa.string()),
            pa.field("content", pa.string()),
            pa.field("vector",  pa.list_(pa.float32(), 384)),
        ])

        if "test_table" in db.table_names():
            print("✓ Test table already exists")
        else:
            db.create_table("test_table", schema=schema)
            print("✓ Created test table")
    except Exception as e:
        print(f"✗ LanceDB error: {e}")
        print("You may need to install lancedb: pip install lancedb")

if __name__ == "__main__":
    fix_db_connection()
