# rag_diagnostics.py
from i2c.bootstrap import initialize_environment
initialize_environment()
from pathlib import Path
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("rag_diagnostics")

def diagnose_rag_system():
    """Diagnose issues with the RAG system"""
    logger.info("Starting RAG system diagnostics...")
    
    # Import required modules
    try:
        from i2c.db_utils import (
            get_db_connection,
            get_or_create_table,
            TABLE_CODE_CONTEXT,
            SCHEMA_CODE_CONTEXT,
        )
        logger.info("✅ Successfully imported db_utils")
    except ImportError as e:
        logger.error(f"❌ Failed to import db_utils: {e}")
        return False
    
    # Test database connection
    try:
        db = get_db_connection()
        if db is None:
            logger.error("❌ get_db_connection() returned None")
            return False
        logger.info(f"✅ Connected to database: {db}")
        
        # Check table existence
        table_names = db.table_names()
        logger.info(f"Tables in database: {table_names}")
        
        if TABLE_CODE_CONTEXT in table_names:
            logger.info(f"✅ Table '{TABLE_CODE_CONTEXT}' exists")
            
            # Try to open the table
            try:
                table = db.open_table(TABLE_CODE_CONTEXT)
                logger.info(f"✅ Successfully opened table '{TABLE_CODE_CONTEXT}'")
                
                # Check table schema
                schema = table.schema
                logger.info(f"Table schema fields: {[f.name for f in schema]}")
                
                # Check row count
                try:
                    row_count = table.count_rows()
                    logger.info(f"Table has {row_count} rows")
                except Exception as e:
                    logger.error(f"❌ Failed to get row count: {e}")
                    
                # Test a simple query
                try:
                    # Try to get a single row
                    logger.info("Attempting to query the table...")
                    df = table.to_pandas(limit=1)
                    logger.info(f"Query succeeded. Columns: {list(df.columns) if not df.empty else 'No data'}")
                except Exception as e:
                    logger.error(f"❌ Failed to query table: {e}")
            except Exception as e:
                logger.error(f"❌ Failed to open table: {e}")
        else:
            logger.warning(f"⚠️ Table '{TABLE_CODE_CONTEXT}' does not exist")
            
            # Try to create the table
            try:
                logger.info(f"Attempting to create table '{TABLE_CODE_CONTEXT}'...")
                table = get_or_create_table(db, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT)
                if table is not None:
                    logger.info(f"✅ Successfully created table '{TABLE_CODE_CONTEXT}'")
                else:
                    logger.error(f"❌ get_or_create_table() returned None")
            except Exception as e:
                logger.error(f"❌ Failed to create table: {e}")
                
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        return False
    
    # Test embedding model
    try:
        from i2c.workflow.modification.rag_config import get_embed_model
        embed_model = get_embed_model()
        if embed_model is None:
            logger.error("❌ get_embed_model() returned None")
            return False
        logger.info(f"✅ Successfully loaded embedding model: {embed_model}")
        
        # Test embedding generation
        test_text = "This is a test embedding"
        try:
            vector = embed_model.encode(test_text)
            logger.info(f"✅ Successfully generated embedding with shape: {vector.shape}")
        except Exception as e:
            logger.error(f"❌ Failed to generate embedding: {e}")
    except Exception as e:
        logger.error(f"❌ Error loading embedding model: {e}")
        
    # Test context indexer
    try:
        from i2c.agents.modification_team.context_reader.context_reader_agent import ContextReaderAgent
        from i2c.agents.modification_team.context_reader.context_indexer import ContextIndexer
        
        logger.info("✅ Successfully imported ContextReaderAgent and ContextIndexer")
        
        # Create a test project
        test_dir = Path("./rag_test_project")
        test_dir.mkdir(exist_ok=True)
        
        # Create a test file
        test_file = test_dir / "test.py"
        test_file.write_text("# This is a test file\ndef hello():\n    print('Hello world')\n")
        logger.info(f"✅ Created test file at {test_file}")
        
        # Create reader agent
        reader_agent = ContextReaderAgent(test_dir)
        logger.info(f"✅ Created ContextReaderAgent with project path: {test_dir}")
        
        # Try indexing
        logger.info("Attempting to index test project...")
        result = reader_agent.index_project_context()
        logger.info(f"Indexing result: {result}")
        
    except Exception as e:
        logger.error(f"❌ Error testing context indexer: {e}")
        
    logger.info("Diagnostics completed.")
    return True

if __name__ == "__main__":
    diagnose_rag_system()