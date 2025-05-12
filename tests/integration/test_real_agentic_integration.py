import pytest
from pathlib import Path
from i2c.workflow.agentic_orchestrator import execute_agentic_evolution_sync

@pytest.mark.integration
def test_real_agentic_orchestration_flow():
    # Objective for real modification
    objective = {
        "task": "modify",
        "description": "Add type hints to all functions in sample.py",
        "constraints": {"max_tokens": 2048},
        "quality_gates": ["lint", "types", "security"]
    }

    # Path where sample.py is located
    project_path = Path("tests/assets/agentic_integration")

    # Run the real orchestration (no mocks)
    result = execute_agentic_evolution_sync(objective, project_path)

    # Assertions on real flow result
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "decision" in result, "Result should contain 'decision'"
    # After extracting decision

    assert result["decision"] in ["approve", "reject"], "Decision must be 'approve' or 'reject'"
    assert "modifications" in result, "Result should contain 'modifications'"
    assert isinstance(result["modifications"], dict), "Modifications should be a dictionary"
    assert "reasoning_trajectory" in result, "Result should contain 'reasoning_trajectory'"
    assert isinstance(result["reasoning_trajectory"], list), "Reasoning trajectory should be a list"

    print(f"✅ Real Agentic Flow Result: {result}")
