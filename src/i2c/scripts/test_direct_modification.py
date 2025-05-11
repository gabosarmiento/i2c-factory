# test_direct_modification.py
from i2c.bootstrap import initialize_environment
initialize_environment()
from pathlib import Path
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("direct_test")

def test_direct_modification():
    """Test direct modification of a file with RAG"""
    # Create a simple test file
    test_dir = Path("./direct_mod_test")
    test_dir.mkdir(exist_ok=True)
    
    main_file = test_dir / "main.py"
    main_file.write_text("""
# Simple FastAPI app
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
""")
    
    # Index for RAG
    from i2c.agents.modification_team.context_reader.context_reader_agent import ContextReaderAgent
    reader = ContextReaderAgent(test_dir)
    result = reader.index_project_context()
    logger.info(f"Indexing result: {result}")
    
    # Get RAG components
    from i2c.db_utils import get_db_connection
    from i2c.workflow.modification.rag_config import get_embed_model
    
    db = get_db_connection()
    embed_model = get_embed_model()
    
    # Get RAG context
    from i2c.workflow.modification.rag_retrieval import retrieve_context_for_planner
    context = retrieve_context_for_planner(
        user_request="Add a /items/{item_id} endpoint",
        db=db,
        embed_model=embed_model
    )
    logger.info(f"Retrieved context: {len(context) if context else 0} characters")
    
    # Create modification step
    step = {
        "file": "main.py",
        "action": "modify",
        "what": "Add a /items/{item_id} endpoint",
        "how": "Create a new GET endpoint that returns the item_id and an item object"
    }
    
    # Apply modification
    from i2c.workflow.modification.code_modifier_adapter import apply_modification
    
    result = apply_modification(
        modification_step=step,
        project_path=test_dir,
        retrieved_context=context
    )
    
    # Log the result
    if isinstance(result, dict) and "error" in result:
        logger.error(f"Modification failed: {result['error']}")
    else:
        logger.info("Modification succeeded!")
        logger.info(f"Unified diff:\n{result.unified_diff}")
        
        # Apply the changes
        from i2c.workflow.modification.file_operations import write_files_to_disk
        
        code_map = {
            "main.py": result.unified_diff
        }
        write_files_to_disk(code_map, test_dir)
        
        # Show the modified file
        logger.info(f"Modified file:\n{main_file.read_text()}")
    
if __name__ == "__main__":
    test_direct_modification()