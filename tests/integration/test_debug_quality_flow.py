import pytest
from pathlib import Path
from src.i2c.agents.code_orchestration_agent import CodeOrchestrationAgent

@pytest.mark.asyncio
async def test_debug_gate_resolution_flow(tmp_path):
    # Create a temporary source file that should trigger quality gates
    sample_code = "def unused(): pass\n"
    file_path = tmp_path / "sample.py"
    file_path.write_text(sample_code)

    # Initialize the orchestration agent
    session_state = {
        "project_path": str(tmp_path),
        "modified_files": {str(file_path): sample_code},
        "quality_gates": ["python"],
    }

    agent = CodeOrchestrationAgent(session_state=session_state)

    # Act
    result = await agent._run_quality_checks(
        modification_result={"modified_files": {str(file_path): sample_code}},
        quality_gates=["python"]
    )

    # Assert structure
    assert isinstance(result, dict)
    assert "passed" in result
    assert "issues" in result
    assert "gate_results" in result
    assert "debug_raw_output" in result

    debug_info = result["debug_raw_output"]
    assert isinstance(debug_info, dict)
    assert "passed" in debug_info
    assert "gate_results" in debug_info or "issues" in debug_info

    print("\n--- DEBUG RAW OUTPUT ---")
    for k, v in debug_info.items():
        print(f"{k}: {v}")

    assert result["gate_results"], "Expected at least one gate to be evaluated"
