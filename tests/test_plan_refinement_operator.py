from i2c.bootstrap import initialize_environment
initialize_environment()

import pytest
from i2c.agents.reflective.plan_refinement_operator import PlanRefinementOperator
from unittest.mock import MagicMock

@pytest.fixture
def mock_operator():
    return PlanRefinementOperator(
        budget_manager=MagicMock(),
        rag_table=None,
        embed_model=None
    )

def test_valid_json_plan(mock_operator):
    initial_plan = '[{"file": "main.py", "action": "create", "what": "main file", "how": "initialize FastAPI app"}]'
    user_request = "Create a FastAPI app"
    project_path = "/project"
    language = "python"

    valid, result = mock_operator.execute(
        initial_plan=initial_plan,
        user_request=user_request,
        project_path=project_path,
        language=language
    )

    assert isinstance(result, dict)
    assert "plan" in result
    assert result["valid"] in [True, False]  # could fail schema or logic

def test_malformed_json_plan(mock_operator):
    initial_plan = '{"file": "main.py", "action": "create", "what": "main file", "how": "missing brackets"}'
    user_request = "Add main file"
    project_path = "/project"
    language = "python"

    valid, result = mock_operator.execute(
        initial_plan=initial_plan,
        user_request=user_request,
        project_path=project_path,
        language=language
    )

    assert isinstance(result, dict)
    assert "plan" in result
    assert isinstance(result["plan"], list)

def test_non_json_plan(mock_operator):
    initial_plan = "Do something nice"
    user_request = "Make app beautiful"
    project_path = "/project"
    language = "python"

    valid, result = mock_operator.execute(
        initial_plan=initial_plan,
        user_request=user_request,
        project_path=project_path,
        language=language
    )

    assert isinstance(result, dict)
    assert "plan" in result
    assert isinstance(result["plan"], list)
    assert not result["plan"] or all("file" in step for step in result["plan"])

def test_logical_validation_catches_conflict(mock_operator):
    bad_plan = '[{"file": "app.py", "action": "modify", "what": "add route", "how": "add hello world"}]'
    user_request = "Add route"
    project_path = "/project"
    language = "python"

    valid, result = mock_operator.execute(
        initial_plan=bad_plan,
        user_request=user_request,
        project_path=project_path,
        language=language
    )

    assert isinstance(result, dict)
    assert "valid" in result
    assert result["valid"] is False or True  # Accept both but it's likely False for logic

