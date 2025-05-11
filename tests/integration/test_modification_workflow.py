# test_modification_workflow.py
import pytest
import tempfile
import shutil
from pathlib import Path

from i2c.workflow.modification.execute_cycle import execute_modification_cycle
from i2c.db_utils import get_db_connection
from i2c.workflow.modification.rag_config import get_embed_model

@pytest.fixture
def test_project():
   
    """Create a test project in output/tests directory."""
    test_dir = Path("output/tests").absolute()
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test files
    test_file = test_dir / "test_module.py"
    test_file.write_text("""
# A simple test module
def greet(name):
    return f"Hello, {name}!"
        
# TODO: Add more functions
""")
    
    # Create simple __init__.py
    init_file = test_dir / "__init__.py"
    init_file.touch()
    
    yield test_dir
    
    # Clean up
    shutil.rmtree(test_dir)

def test_modify_function_parameter(test_project):
    """Test modifying a function parameter."""
    # Define the modification request
    user_request = "Add a title parameter to the greet function with a default value of None"
    
    # Get DB and embed model for RAG
    db = get_db_connection()
    embed_model = get_embed_model()
    
    # Run the modification cycle
    result = execute_modification_cycle(
        user_request=user_request,
        project_path=test_project,
        language="python",
        db=db,
        embed_model=embed_model
    )
    
    # Verify success
    assert result.get("success", False), "Modification cycle failed"
    
    # Verify the file was modified correctly
    test_file = test_project / "test_module.py"
    content = test_file.read_text()
    
    # Check for the expected modification
    assert "def greet(name, title=None):" in content, "Expected modification not found"
    
    # Verify no diff markers remain in the file
    assert "+def" not in content, "Diff markers (+) found in final content"
    assert "-def" not in content, "Diff markers (-) found in final content"

def test_create_new_file(test_project):
    """Test creating a new file."""
    # Define the modification request
    user_request = "Create a new file called math_utils.py with a square function"
    
    # Get DB and embed model for RAG
    db = get_db_connection()
    embed_model = get_embed_model()
    
    # Run the modification cycle
    result = execute_modification_cycle(
        user_request=user_request,
        project_path=test_project,
        language="python",
        db=db,
        embed_model=embed_model
    )
    
    # Verify success
    assert result.get("success", False), "Modification cycle failed"
    
    # Verify the new file was created
    new_file = test_project / "math_utils.py"
    assert new_file.exists(), "New file not created"
    
    # Check content
    content = new_file.read_text()
    assert "def square" in content, "Expected function not found in new file"
    
    # Verify no diff markers in the file
    assert "+" not in content or "-" not in content, "Diff markers found in new file content"