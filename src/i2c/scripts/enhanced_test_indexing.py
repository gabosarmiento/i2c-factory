# enhanced_test_indexing.py
from i2c.bootstrap import initialize_environment
initialize_environment()
from pathlib import Path
import sys
import logging

# Configure detailed logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Silence other loggers
for logger_name in logging.root.manager.loggerDict:
    if logger_name != 'root':
        logging.getLogger(logger_name).setLevel(logging.INFO)

# Define our test logger
logger = logging.getLogger("indexing_test")
logger.setLevel(logging.DEBUG)

def test_indexing():
    """Test the RAG indexing system with detailed debugging"""
    logger.info("Starting enhanced indexing test")
    
    # Import required modules
    try:
        from i2c.db_utils import (
            get_db_connection, 
            get_or_create_table, 
            add_or_update_chunks,
            TABLE_CODE_CONTEXT, 
            SCHEMA_CODE_CONTEXT
        )
        logger.info("✅ Imported database utilities")
        
        from i2c.agents.modification_team.context_reader.context_reader_agent import ContextReaderAgent
        from i2c.agents.modification_team.context_reader.context_indexer import ContextIndexer
        logger.info("✅ Imported context reader modules")
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False
    
    # Test database connection
    logger.info("Testing database connection...")
    db = get_db_connection()
    if not db:
        logger.error("❌ Database connection failed")
        return False
    logger.info(f"✅ Connected to database: {type(db).__name__}")
    
    # Check available tables
    tables = db.table_names()
    logger.info(f"Tables in database: {tables}")
    
    # Check if code_context table exists
    if TABLE_CODE_CONTEXT in tables:
        logger.info(f"✅ Table '{TABLE_CODE_CONTEXT}' exists")
        # Try to open the table
        try:
            table = db.open_table(TABLE_CODE_CONTEXT)
            logger.info(f"✅ Successfully opened table: {table}")
            # Check row count
            row_count = table.count_rows()
            logger.info(f"Table has {row_count} rows")
        except Exception as e:
            logger.error(f"❌ Error opening table: {e}")
    else:
        logger.info(f"Table '{TABLE_CODE_CONTEXT}' doesn't exist, will be created during indexing")
    
    # Create test directory and file
    test_dir = Path("./better_indexing_test")
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "sample.py"
    test_file.write_text("""
# Sample Python code for testing RAG indexing
def sample_function():
    \"\"\"
    This is a sample function that does nothing.
    It's used to test the RAG indexing system.
    \"\"\"
    return "Hello, world!"

class SampleClass:
    def __init__(self):
        self.value = 42
        
    def get_value(self):
        return self.value
""")
    logger.info(f"✅ Created test file at {test_file}")
    
    # Test direct table creation
    logger.info("Testing direct table manipulation...")
    try:
        # Sample chunk for testing
        chunk = {
            'path': str(test_file.relative_to(test_dir)),
            'chunk_name': 'test_chunk',
            'chunk_type': 'function',
            'content': 'def test(): return "test"',
            'vector': [0.1] * 384,  # 384-dimensional dummy vector
            'start_line': 1,
            'end_line': 2,
            'content_hash': 'test_hash',
            'language': 'python',
            'lint_errors': [],
            'dependencies': [],
        }
        
        # Try add_or_update_chunks directly
        logger.info("Adding test chunk directly...")
        result = add_or_update_chunks(
            db,
            TABLE_CODE_CONTEXT,
            SCHEMA_CODE_CONTEXT,
            'path',
            str(test_file.relative_to(test_dir)),
            [chunk]
        )
        logger.info(f"Direct chunk addition result: {result}")
        
        # Check if chunk was added
        if TABLE_CODE_CONTEXT in db.table_names():
            table = db.open_table(TABLE_CODE_CONTEXT)
            row_count = table.count_rows()
            logger.info(f"After direct addition, table has {row_count} rows")
    except Exception as e:
        logger.error(f"❌ Error in direct table manipulation: {e}")
    
    # Create reader agent
    logger.info("Creating ContextReaderAgent...")
    reader = ContextReaderAgent(test_dir)
    logger.info(f"✅ Created reader agent: {reader}")
    
    # Look inside the reader agent
    indexer = getattr(reader, "indexer", None)
    logger.info(f"Reader's indexer: {indexer}")
    if indexer:
        logger.info(f"Indexer's table: {getattr(indexer, 'table', None)}")
    
    # Test indexing
    logger.info("Indexing project...")
    result = reader.index_project_context()
    logger.info(f"Indexing result: {result}")
    
    # Final verification
    logger.info("Verifying final state...")
    db = get_db_connection()  # Get fresh connection
    if db and TABLE_CODE_CONTEXT in db.table_names():
        table = db.open_table(TABLE_CODE_CONTEXT)
        row_count = table.count_rows()
        logger.info(f"Final table row count: {row_count}")
        
        if row_count > 0:
            # Try to query the table
            logger.info("Querying first row...")
            df = table.to_pandas(limit=1)
            if not df.empty:
                logger.info(f"Columns: {list(df.columns)}")
                logger.info(f"Content snippet: {df['content'].iloc[0][:50]}...")
    
    logger.info("Test completed")
    return True

if __name__ == "__main__":
    test_indexing()