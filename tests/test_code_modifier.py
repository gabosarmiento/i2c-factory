# tests/test_code_modifier.py

import os
import pytest
from pathlib import Path

from i2c.agents.modification_team.code_modifier import CodeModifierAgent

@pytest.fixture
def test_project(tmp_path):
    """Create a test project structure with minimal files for testing."""
    # Create src directory
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    
    # Create a simple main.py file
    main_file = src_dir / "main.py"
    main_file.write_text("""def calculate(x):
    return x * 2
""")
    
    # Create a simple __init__.py file with docstring to satisfy pattern validator
    init_file = src_dir / "__init__.py"
    init_file.write_text("""\"\"\"Module for main functionality.\"\"\"

def helper_function():
    try:
        return "Helper"
    except Exception as e:
        print(f"Error: {e}")
        return None
""")
    
    return tmp_path

def test_modification_validation_flow(test_project):
    agent = CodeModifierAgent()
    
    modification_step = {
        'action': 'modify',
        'file': 'src/main.py',
        'what': 'Add type hints',
        'how': 'Add int return type annotation'
    }
    
    result = agent.modify_code(
        modification_step,
        test_project,
        retrieved_context="Context from RAG"
    )
    
    # Check if result is a dictionary (indicating validation issues)
    if isinstance(result, dict):
        assert 'code' in result
        assert 'valid' in result
        assert 'errors' in result
        modified_code = result['code']
    else:
        # Result is a string with the modified code
        modified_code = result
    
    # Verify the modification was made
    assert 'def calculate(x' in modified_code
    assert '-> int' in modified_code  # The int return type was added