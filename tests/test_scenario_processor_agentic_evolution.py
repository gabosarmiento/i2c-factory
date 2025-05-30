import pytest
from unittest.mock import patch
from i2c.workflow.scenario_processor import ScenarioProcessor


class DummyScenarioProcessor(ScenarioProcessor):
    def __init__(self):
        self.project_name = "dummy_project"
        self.current_project_path = "/tmp/test_project"
        self.session_state = {"knowledge_base": "mock_kb"}  # Simulate shared cache

    @patch("i2c.workflow.scenario_processor.execute_agentic_evolution_sync")
    def test_process_agentic_evolution_step_calls_executor(self, mock_executor):
        processor = DummyScenarioProcessor()

        step = {
            "type": "agentic_evolution",
            "name": "Refactor Code",
            "objective": {
                "task": "Refactor the code",
                "constraints": ["no libraries"]
            }
        }

        processor._process_agentic_evolution_step(step)

        mock_executor.assert_called_once()
        args = mock_executor.call_args[0][0]  # unpack first positional arg
        assert "task" in args
        assert args["project_path"] == "/tmp/test_project"
        assert any("quality" in c.lower() for c in args["constraints"])  # checks quality constraint was injected
