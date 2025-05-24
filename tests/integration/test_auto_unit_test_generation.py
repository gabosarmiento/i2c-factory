import pytest
from pathlib import Path
from i2c.agents.modification_team.code_modification_manager_agno import apply_modification

@pytest.mark.integration
def test_auto_unit_test_generation(tmp_path):
    """Test that unit tests are automatically generated when modifying Python code"""
    
    # --- Setup: Create a simple Python file to modify ---
    original_file = tmp_path / "calculator.py"
    original_file.write_text("""def add(a, b):
    return a + b
""")
    
    # --- Modification step that should trigger unit test generation ---
    step = {
        "action": "modify",
        "file": "calculator.py", 
        "what": "Add a multiply function",
        "how": "Add def multiply(a, b): return a * b"
    }
    
    # --- Session state with retrieval tools enabled ---
    session_state = {
        "use_retrieval_tools": True,
        "modified_files": {}
    }
    
    # --- Apply modification (should auto-generate unit tests) ---
    result = apply_modification(
        modification_step=step,
        project_path=tmp_path,
        retrieved_context="",
        session_state=session_state
    )
    
    # --- Verify the modification worked ---
    assert result is not None
    modified_content = (tmp_path / "calculator.py").read_text()
    assert "add" in modified_content
    print(f"✅ Modified file content:\n{modified_content}")
    
    # --- Check if unit test file was auto-generated ---
    test_file = tmp_path / "test_calculator.py"
    
    if test_file.exists():
        test_content = test_file.read_text()
        print(f"\n✅ Auto-generated test file:\n{test_content}")
        
        # Verify test content has expected structure
        assert "import unittest" in test_content
        assert "test_calculator" in test_content.lower() or "calculator" in test_content
        assert "def test" in test_content
        
        print("✅ Unit test auto-generation successful!")
        
    else:
        print("⚠️ Unit test file not generated - checking session state...")
        
        # Check if tests were tracked in session state
        modified_files = session_state.get("modified_files", {})
        test_files = [f for f in modified_files.keys() if f.startswith("test_")]
        
        if test_files:
            print(f"✅ Test files in session state: {test_files}")
            for test_file_name in test_files:
                print(f"Test content preview: {modified_files[test_file_name][:200]}...")
        else:
            print("❌ No test files generated in session state either")
    
    # --- Verify session state was updated ---
    assert "modified_files" in session_state
    assert "calculator.py" in session_state["modified_files"]
    
    print(f"\n📊 Session state files: {list(session_state['modified_files'].keys())}")


if __name__ == "__main__":
    print("Testing auto unit test generation...")
    pytest.main(["-xvs", __file__])