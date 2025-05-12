from i2c.bootstrap import initialize_environment
initialize_environment()
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from i2c.workflow.agentic_orchestrator import execute_agentic_evolution_sync

@pytest.fixture
def valid_objective():
    return {
        "task": "modify",
        "description": "Add type hints to all functions in sample.py",
        "constraints": {"max_tokens": 2048},
        "quality_gates": ["lint", "types", "security"]
    }

@pytest.fixture
def mock_orchestration_team():
    with patch("i2c.workflow.agentic_orchestrator.build_orchestration_team") as mock_build_team:
        mock_team = MagicMock()
        mock_team.arun = AsyncMock()
        mock_build_team.return_value = mock_team
        yield mock_team.arun

def test_full_agentic_flow(valid_objective, mock_orchestration_team):
    project_path = Path("tests/assets/agentic_integration")

    mock_orchestration_team.return_value = MagicMock(
        content='{"decision": "approve", "modifications": [{"file": "sample.py", "changes": ["Added type hints"]}], "reasoning_trajectory": ["analysis", "modification", "validation"]}'
    )

    result = execute_agentic_evolution_sync(valid_objective, project_path)

    assert isinstance(result, dict)
    assert result.get("decision") == "approve"
    assert "modifications" in result
    assert "reasoning_trajectory" in result

def test_agentic_flow_with_missing_content(valid_objective, mock_orchestration_team):
    project_path = Path("tests/assets/agentic_integration")

    mock_orchestration_team.return_value = MagicMock(content=None)

    with pytest.raises(ValueError, match="Result content is missing or invalid."):
        execute_agentic_evolution_sync(valid_objective, project_path)

def test_agentic_flow_with_invalid_json(valid_objective, mock_orchestration_team):
    project_path = Path("tests/assets/agentic_integration")

    mock_orchestration_team.return_value = MagicMock(content="not a valid json string")

    with pytest.raises(ValueError, match="Failed to parse result content as JSON"):
        execute_agentic_evolution_sync(valid_objective, project_path)

def test_agentic_flow_with_reject_decision(valid_objective, mock_orchestration_team):
    project_path = Path("tests/assets/agentic_integration")

    with patch("i2c.workflow.modification.rag_config.get_embed_model", side_effect=ImportError):
        mock_orchestration_team.return_value = MagicMock(
            content='{"decision": "reject", "reason": "Failed security checks"}'
        )

        result = execute_agentic_evolution_sync(valid_objective, project_path)

        assert result.get("decision") == "reject"
        assert result.get("reason") == "Failed security checks"
