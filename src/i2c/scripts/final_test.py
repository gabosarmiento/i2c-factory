# final_test.py
from i2c.bootstrap import initialize_environment
initialize_environment()
from pathlib import Path
import logging
import traceback

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("final_test")

def run_final_test():
    """Test the fixed indexing system"""
    # Create test dir and file
    test_dir = Path("./final_test")
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "final_example.py"
    test_file.write_text("""
def final_example():
    \"\"\"This is the final test example.\"\"\"
    return "Success!"
""")
    logger.info(f"Created test file: {test_file}")
    
    # Create and run reader
    try:
        from i2c.agents.modification_team.context_reader.context_reader_agent import ContextReaderAgent
        
        reader = ContextReaderAgent(test_dir)
        logger.info(f"Created reader agent: {reader}")
        
        result = reader.index_project_context()
        logger.info(f"Indexing result: {result}")
        
        # Verify results
        from i2c.db_utils import get_db_connection, TABLE_CODE_CONTEXT
        
        db = get_db_connection()
        if db and TABLE_CODE_CONTEXT in db.table_names():
            table = db.open_table(TABLE_CODE_CONTEXT)
            row_count = table.count_rows()
            logger.info(f"Final table has {row_count} rows")
            
            if row_count > 0:
                # Check for our file
                df = table.to_pandas()
                paths = df['path'].unique()
                logger.info(f"Paths in table: {paths}")
                
                if "final_example.py" in paths:
                    logger.info("✅ Successfully indexed our test file!")
                    
                    # Get content
                    file_df = df[df['path'] == "final_example.py"]
                    logger.info(f"Found {len(file_df)} chunks for our file")
                    if not file_df.empty:
                        logger.info(f"Content: {file_df['content'].iloc[0]}")
        
    except Exception as e:
        logger.error(f"Error in test: {e}")
        logger.error(traceback.format_exc())
    
    logger.info("Test completed")

if __name__ == "__main__":
    run_final_test()