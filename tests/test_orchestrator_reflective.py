import tempfile                   
from pathlib import Path
from unittest.mock import MagicMock, patch
import unittest
from i2c.bootstrap import initialize_environment
initialize_environment()
from i2c.workflow import orchestrator


class OrchestratorReflectiveTests(unittest.TestCase):
    # ------------------------------------------------------------------ setup
    def setUp(self):
        # 1️⃣ scratch project directory
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        (self.tmp / "f.py").write_text("print('stub')")  # file for modify path

        # 2️⃣ patch main gen / mod cycles
        self.p_gen = patch("workflow.orchestrator.execute_generation_cycle")
        self.p_mod = patch("workflow.orchestrator.execute_modification_cycle")
        self.gen = self.p_gen.start()
        self.mod = self.p_mod.start()

        # 3️⃣ patch RAG helpers (they don't exist in orchestrator)
        self.p_rag = patch("workflow.orchestrator.get_rag_table", return_value=None, create=True)
        self.p_emb = patch("workflow.orchestrator.get_embed_model", return_value=None, create=True)
        self.p_rag.start(); self.p_emb.start()

        # 4️⃣ patch reflective operators
        self.p_plan = patch("workflow.orchestrator.PlanRefinementOperator")
        self.p_issue = patch("workflow.orchestrator.IssueResolutionOperator")
        self.MockPlan = self.p_plan.start()
        self.MockIssue = self.p_issue.start()
        self.MockPlan.return_value.execute.return_value  = (True, {"plan": [{"dummy": 1}], "iterations": 0})
        self.MockIssue.return_value.execute.return_value = (True, {"fixed_content": "x", "iterations": 1})
        
        from unittest.mock import MagicMock
        fake_tracker = MagicMock()
        fake_tracker.get_cost_summary.return_value = {
            "phases": {"analyse": {"tokens": 100, "cost": 0.001}},
            "total_cost": 0.001,
        }
        self.MockPlan.return_value.cost_tracker = fake_tracker
        # 5️⃣ patch post‑SRE helpers referenced later
        self.p_dep = patch("workflow.orchestrator.dependency_verifier", create=True)
        self.p_sandbox = patch("workflow.orchestrator.sandbox_executor", create=True)
        self.p_dep.start().check_dependencies.return_value = []
        self.p_sandbox.start().execute.return_value = (True, "")

    # ------------------------------------------------------------------ teardown
    def tearDown(self):
        patch.stopall()
        self.tmp_dir.cleanup()

    def test_generate_path_invokes_plan_refiner(self):
        self.gen.return_value = {
            "success": True,
            "language": "python",
            "plan": [{"dummy": 0}],
            "code_map": {},
        }
        ok = orchestrator.route_and_execute(
            action_type="generate",
            action_detail={"objective": "demo"},
            current_project_path=self.tmp,
            current_structured_goal={"language": "python"},
        )
        self.assertIsNotNone(ok)
        self.MockPlan.assert_called_once()          # instantiated
        self.MockPlan.return_value.execute.assert_called_once()

    def test_modify_path_invokes_issue_resolver(self):
        self.mod.return_value = {
            "success": True,
            "language": "python",
            "test_failures": {"f.py": {"dummy": "fail"}},
            "code_map": {},
        }
        ok = orchestrator.route_and_execute(
            action_type="modify",
            action_detail="refactor foo",
            current_project_path=self.tmp,
            current_structured_goal={"language": "python"},
        )
        self.assertTrue(ok)
        self.MockIssue.assert_called_once()
        self.MockIssue.return_value.execute.assert_called_once()

if __name__ == "__main__":
    unittest.main()
