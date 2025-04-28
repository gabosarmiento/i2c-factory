import sys, os
# Ensure project root is on PYTHONPATH for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from pathlib import Path
import workflow.orchestrator as orch
from workflow.orchestrator import route_and_execute

class DummyCommitRecorder:
    def __init__(self):
        self.called = False
        self.args = None

@pytest.fixture(autouse=True)
def patch_all(monkeypatch):
    # Stub generation and modification cycles
    monkeypatch.setattr(
        orch, 'execute_generation_cycle',
        lambda detail, path: {"success": True, "language": "python", "code_map": {"file.py": "code"}}
    )
    monkeypatch.setattr(
        orch, 'execute_modification_cycle',
        lambda detail, path, lang: {"success": True, "language": "python", "code_map": {"file.py": "code"}}
    )
    # Stub SRE and quality agents
    monkeypatch.setattr(
        orch.static_analysis_agent, 'get_analysis_summary',
        lambda path: {"errors": [], "total_lint_errors": 0, "files_with_lint_errors": [], "all_dependencies": []}
    )
    monkeypatch.setattr(
        orch.dependency_verifier, 'check_dependencies',
        lambda path: []
    )
    monkeypatch.setattr(
        orch.sandbox_executor, 'execute',
        lambda path, lang: (True, "")
    )
    monkeypatch.setattr(
        orch.integration_checker_agent, 'check_integrations',
        lambda path: []
    )
    monkeypatch.setattr(
        orch.reviewer_agent, 'review_code',
        lambda structured_goal, code_map, analysis_summary: "Review OK"
    )
    monkeypatch.setattr(
        orch.guardrail_agent, 'evaluate_results',
        lambda static_analysis_summary, dependency_summary, syntax_check_result, review_feedback: (
            orch.GUARDRAIL_CONTINUE, []
        )
    )
    # Record commits
    recorder = DummyCommitRecorder()
    monkeypatch.setattr(
        orch.version_controller, 'initialize_and_commit',
        lambda path, msg: setattr(recorder, 'called', True)
    )
    return recorder


def test_route_and_execute_generate_success(patch_all, tmp_path):
    recorder = patch_all
    structured_goal = {"language": "python", "objective": "Test generate"}
    result = route_and_execute(
        action_type='generate',
        action_detail=structured_goal,
        current_project_path=tmp_path,
        current_structured_goal=structured_goal
    )
    assert result is True
    assert recorder.called, "Expected version_controller.initialize_and_commit to be called"


def test_route_and_execute_modify_success(patch_all, tmp_path):
    recorder = patch_all
    structured_goal = {"language": "python", "objective": "Test modify"}
    result = route_and_execute(
        action_type='modify',
        action_detail='some request',
        current_project_path=tmp_path,
        current_structured_goal=structured_goal
    )
    assert result is True
    assert recorder.called, "Expected version_controller.initialize_and_commit to be called"


def test_route_and_execute_unknown_action(tmp_path):
    # No need to patch; should immediately return False
    result = route_and_execute(
        action_type='unknown',
        action_detail=None,
        current_project_path=tmp_path,
        current_structured_goal=None
    )
    assert result is False
