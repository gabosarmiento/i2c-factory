# simple_test.py
from i2c.bootstrap import initialize_environment
initialize_environment()
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def run_simple_test():
    """Ultra-simple test for database and table operations"""
    # Step 1: Create test file
    test_dir = Path("./simple_test")
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "test.py"
    test_file.write_text("def test(): return 'test'")
    
    # Step 2: Import database utilities
    try:
        from i2c.db_utils import get_db_connection, get_or_create_table, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT
        logger.info("✅ Imported database utilities")
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return
    
    # Step 3: Connect to database
    db = get_db_connection()
    if not db:
        logger.error("❌ Database connection failed")
        return
    logger.info(f"✅ Connected to database. Table names: {db.table_names()}")
    
    # Step 4: Create/open table directly
    table = get_or_create_table(db, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT)
    if not table:
        logger.error("❌ Failed to get/create table")
        return
    logger.info(f"✅ Opened/created table. Schema: {[f.name for f in table.schema]}")
    
    # Step 5: Create a simple record
    try:
        # Create dummy vector (384-dimensional)
        vector = [0.1] * 384
        
        # Add a simple record
        record = {
            'path': str(test_file.relative_to(test_dir)),
            'chunk_name': 'test_function',
            'chunk_type': 'function',
            'content': test_file.read_text(),
            'vector': vector,
            'start_line': 1,
            'end_line': 1,
            'content_hash': 'test_hash',
            'language': 'python',
            'lint_errors': [],
            'dependencies': [],
        }
        
        # Add directly to the table
        table.add([record])
        logger.info(f"✅ Added record to table")
        
        # Check row count
        count = table.count_rows()
        logger.info(f"✅ Table now has {count} rows")
        
        # Get one row
        df = table.to_pandas()
        df = df.head(1)
        logger.info(f"✅ Data retrieved. Columns: {list(df.columns)}")
        logger.info(f"✅ Content from table: {df['content'].iloc[0]}")
        
    except Exception as e:
        logger.error(f"❌ Error adding/querying data: {e}")
    
    logger.info("Test complete")

if __name__ == "__main__":
    run_simple_test()