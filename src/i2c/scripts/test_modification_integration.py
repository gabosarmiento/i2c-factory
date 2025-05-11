# test_modification_integration.py
from i2c.bootstrap import initialize_environment
initialize_environment()
from pathlib import Path
import shutil
import tempfile
import json

# Import necessary components
from i2c.workflow.modification.execute_cycle import execute_modification_cycle
from i2c.db_utils import get_db_connection
from i2c.workflow.modification.rag_config import get_embed_model

def test_code_modification():
    """Test the integrated code modification workflow"""
    # Create a temporary test directory
    test_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create a test file
        test_file = test_dir / "test_module.py"
        test_file.write_text("""
# A simple test module
def greet(name):
    return f"Hello, {name}!"
        
# TODO: Add more functions
""")
        
        print(f"Created test file at {test_file}")
        
        # Define a simple modification request
        user_request = "add a title parameter to the greet function with a default value of None"
        
        # Get DB and embed model for RAG
        db = get_db_connection()
        embed_model = get_embed_model()
        
        # Run the modification cycle
        result = execute_modification_cycle(
            user_request=user_request,
            project_path=test_dir,
            language="python",
            db=db,
            embed_model=embed_model
        )
        
        # Check if modification was successful
        if result.get("success", False):
            # Read the modified file
            modified_content = test_file.read_text()
            print("Modification succeeded!")
            print(f"Modified content:\n{modified_content}")
            
            # Verify the modification
            if "def greet(name, title=None):" in modified_content:
                print("✅ Correct modification found!")
            else:
                print("❌ Expected modification not found!")
        else:
            print(f"❌ Modification failed: {result}")
    
    finally:
        # Clean up the test directory
        shutil.rmtree(test_dir)

if __name__ == "__main__":
    test_code_modification()