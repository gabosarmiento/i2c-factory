import pytest
from pathlib import Path
from i2c.agents.modification_team.code_modification_manager_agno import apply_modification

@pytest.mark.integration
def test_basic_modification_pipeline(tmp_path):
    # --- Simulate scenario step ---
    # This will try to add a comment to a small file
    file_name = tmp_path / "hello.py"
    file_name.write_text("def greet(name):\n    return f\"Hello, {name}!\"")
    
    step = {
        "file": "hello.py",
        "action": "modify",
        "what": "Insert a comment above the greet function",
        "how": ""
    }
    
    # Set up a session to enable retrieval tools (if wanted)
    session_state = {"use_retrieval_tools": True}
    
    # --- Optionally: minimal 'retrieved_context' string, or just "" for baseline ---
    retrieved_context = ""
    
    # --- Run the pipeline ---
    patch_obj = apply_modification(
        modification_step=step,
        project_path=tmp_path,
        retrieved_context=retrieved_context,
        session_state=session_state,
    )
    
    # --- Validate outcome ---
    result_code = (tmp_path / "hello.py").read_text()
    # You expect the comment to be present (tune this if your system produces a different string)
    assert "comment" in result_code.lower()
    assert "greet" in result_code
    # Optionally: check patch_obj.unified_diff or other metadata

    print("Integration pipeline output:\n", result_code)

