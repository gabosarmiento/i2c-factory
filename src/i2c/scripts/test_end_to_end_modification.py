# test_end_to_end_modification.py
from i2c.bootstrap import initialize_environment
initialize_environment()
import os
import shutil
import tempfile
from pathlib import Path
import sys
import traceback
import json

# Add your project to the sys.path if needed
# sys.path.insert(0, str(Path(__file__).parent.parent))

# Import necessary components
from i2c.workflow.modification.execute_cycle import execute_modification_cycle
from i2c.db_utils import get_db_connection
from i2c.workflow.modification.rag_config import get_embed_model

def test_end_to_end_modification():
    """
    Test the entire modification workflow from request to final files.
    This test:
    1. Creates a temporary project with test files
    2. Runs the modification cycle with a specific request
    3. Verifies the final files contain the expected changes
    4. Cleans up the temporary project
    """
    print("\n=== STARTING END-TO-END MODIFICATION TEST ===\n")
    
    # Create a temporary test directory
    test_dir = Path(tempfile.mkdtemp())
    print(f"Created test directory: {test_dir}")
    
    try:
        # 1. Create test files
        setup_test_project(test_dir)
        
        # 2. Run the modification cycle
        user_request = {
            "file": "test_module.py",
            "action": "modify",
            "what": "Change function signature",
            "how": "Replace 'def greet(name):' with 'def greet(name, title=None):' and update the return statement to include title"
        }
        print(f"\nRunning modification with request: '{user_request}'")
        
        # Get DB and embed model for RAG
        db = get_db_connection()
        embed_model = get_embed_model()
        
        # Test the ModifierAgent directly
        from i2c.agents.modification_team.code_modification_manager import ModifierAgent
        from agno.agent import Message
        
        print("\n--- Testing ModifierAgent directly ---")
        agent = ModifierAgent()
        prompt = "You are the Code Modifier.\nFile: test_module.py\nTask: Add title parameter\nDetails: Add optional title parameter"
        response = agent.predict([Message(role="user", content=prompt)])
        print(f"Agent direct response: {response}")
        print("\n--- End of direct test ---\n")
        # Execute the modification cycle
        result = execute_modification_cycle(
            user_request=json.dumps(user_request),  # Convert dict to JSON string
            project_path=test_dir,
            language="python",
            db=db,
            embed_model=embed_model
        )
        
        # 3. Verify the results
        if result.get("success", False):
            print("\n✅ Modification cycle reported success")
            
            # Check if code map has the expected files
            code_map = result.get("code_map", {})
            print(f"Code map contains {len(code_map)} modified files")
            
            # Verify the file content was modified as expected
            test_file = test_dir / "test_module.py"
            if test_file.exists():
                content = test_file.read_text()
                print(f"\nFinal file content:\n{content}")
                
                # Check for the expected modification
                if "def greet(name, title=None):" in content:
                    print("\n✅ Expected modification found in final file")
                else:
                    print("\n❌ Expected modification NOT found in final file")
                
                # Verify no diff markers remain in the file
                if "+def" in content or "-def" in content:
                    print("\n❌ ERROR: Diff markers found in final file content")
                else:
                    print("\n✅ No diff markers in final file content")
            else:
                print(f"\n❌ Test file not found: {test_file}")
        else:
            print(f"\n❌ Modification cycle failed: {result}")
    
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        traceback.print_exc()
    
    finally:
        # 4. Clean up
        try:
            shutil.rmtree(test_dir)
            print(f"\nCleaned up test directory: {test_dir}")
        except Exception as e:
            print(f"Warning: Failed to clean up test directory: {e}")
    
    print("\n=== END-TO-END MODIFICATION TEST COMPLETED ===\n")

def setup_test_project(project_dir: Path):
    """Set up a simple test project with files to modify."""
    # Create test_module.py
    test_file = project_dir / "test_module.py"
    test_file.write_text("""
# A simple test module
def greet(name):
    return f"Hello, {name}!"
        
# TODO: Add more functions
""")
    print(f"Created test file: {test_file}")
    
    # Create simple __init__.py
    init_file = project_dir / "__init__.py"
    init_file.touch()
    print(f"Created init file: {init_file}")
    
    # Optionally create more test files if needed for your test case
    # For example:
    utils_dir = project_dir / "utils"
    utils_dir.mkdir(exist_ok=True)
    utils_init = utils_dir / "__init__.py"
    utils_init.touch()
    utils_file = utils_dir / "formatting.py"
    utils_file.write_text("""
# Formatting utilities
def format_name(name):
    return name.title()
""")
    print(f"Created utility files in: {utils_dir}")

if __name__ == "__main__":
    test_end_to_end_modification()