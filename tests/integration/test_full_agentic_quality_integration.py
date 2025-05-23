
import pytest
import asyncio
from pathlib import Path
from i2c.agents.code_orchestration_agent import CodeOrchestrationAgent

@pytest.mark.integration
def test_full_agentic_quality_integration(tmp_path):
    # Step 1: Create a file that should trigger quality issues
    file_path = tmp_path / "bad_code.py"
    file_path.write_text("""def add(a, b):
    return a + b

def unused_function():
    pass
""")

    # Step 2: Construct a session_state as expected by the orchestration agent
    session_state = {
        "project_path": str(tmp_path),
        "modified_files": {
            "bad_code.py": file_path.read_text()
        },
        "objective": {
            "task": "Validate modified Python files using enterprise and static quality gates.",
            "quality_gates": ["flake8", "mypy"]
        }
    }

    # Step 3: Instantiate the orchestration agent with the session
    agent = CodeOrchestrationAgent(session_state=session_state)

    # Step 4: Run the quality check pipeline
    result = asyncio.run(agent._run_quality_checks(
        modification_result=session_state,
        quality_gates=["flake8", "mypy"]
    ))

    # Step 5: Validate result structure
    assert isinstance(result, dict)
    assert "passed" in result
    assert "issues" in result
    assert "gate_results" in result
    print("\n✅ FULL AGENTIC INTEGRATION RESULT:", result)
