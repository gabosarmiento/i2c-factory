# enhanced_recovery_test.py
from i2c.bootstrap import initialize_environment
initialize_environment()
from pathlib import Path
import logging
import json
import os

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("recovery_test")

def run_recovery_test():
    """Test with enhanced recovery for the RAG table"""
    # Step 1: Import utilities
    from i2c.db_utils import get_db_connection, TABLE_CODE_CONTEXT
    
    # Step 2: Check database path
    db_path = Path("./data/lancedb")
    logger.info(f"Database path: {db_path} (exists: {db_path.exists()})")
    if db_path.exists():
        tables = os.listdir(db_path)
        logger.info(f"Directories in DB path: {tables}")
        
        # Check for table directory
        table_dir = db_path / TABLE_CODE_CONTEXT
        if table_dir.exists():
            logger.info(f"Table directory exists: {table_dir}")
            # Check table contents
            table_contents = list(table_dir.glob("**/*"))
            logger.info(f"Table directory contents: {table_contents}")
            
            # Check versions directory 
            versions_dir = table_dir / "_versions"
            if versions_dir.exists():
                logger.info(f"Versions directory exists: {versions_dir}")
                version_contents = list(versions_dir.glob("**/*"))
                logger.info(f"Versions directory contents: {version_contents}")
    
    # Step 3: Create test project
    test_dir = Path("./recovery_test")
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "example.py"
    test_file.write_text("""
# Example code
def example_function():
    \"\"\"This is an example function.\"\"\"
    return "Example"
""")
    logger.info(f"Created test file: {test_file}")
    
    # Step 4: Try indexing with robust recovery
    logger.info("Creating ContextReaderAgent with recovery...")
    
    try:
        # Create the context reader with robust recovery
        from i2c.agents.modification_team.context_reader.context_reader_agent import ContextReaderAgent
        reader = ContextReaderAgent(test_dir)
        logger.info(f"Created reader: {reader}")
        
        # Perform indexing
        logger.info("Starting indexing with robust recovery...")
        result = reader.index_project_context()
        logger.info(f"Indexing result: {json.dumps(result, indent=2)}")
        
        # Check results
        from i2c.db_utils import get_db_connection, TABLE_CODE_CONTEXT
        db = get_db_connection()
        if db and TABLE_CODE_CONTEXT in db.table_names():
            table = db.open_table(TABLE_CODE_CONTEXT)
            row_count = table.count_rows()
            logger.info(f"Final table has {row_count} rows")
            
            if row_count > 0:
                # Get rows about our test file
                query = f"path = 'example.py'"
                try:
                    # Try to search by path
                    df = table.search(where=query).to_pandas()
                    logger.info(f"Found {len(df)} rows for example.py")
                    if not df.empty:
                        logger.info(f"First row content sample: {df['content'].iloc[0][:50]}...")
                except Exception as e:
                    logger.error(f"Error querying table: {e}")
                    
                    # Try general query
                    df = table.to_pandas()
                    logger.info(f"Total rows in table: {len(df)}")
                    logger.info(f"Available paths: {df['path'].unique()}")
    except Exception as e:
        logger.error(f"Error in test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
    logger.info("Recovery test completed")

if __name__ == "__main__":
    run_recovery_test()