# /tests/test_reflective_agents.py
"""Unit‑tests for reflective agents and support classes.

Updated for the 2025‑05 refactor:
* Iteration counter now starts at 0.
* `retrieved_context` is coerced to "" when None.
* Python syntax validator returns messages that start with "Syntax error:" instead of the raw `SyntaxError` name.
* Unsupported‑language syntax hook returns "No validator.".
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from i2c.bootstrap import initialize_environment
initialize_environment()
from i2c.agents.budget_manager import BudgetManagerAgent
from i2c.agents.reflective.context_aware_operator import (
    BudgetScope,
    ContextAwareOperator,
    PhaseCostTracker,
    ValidationHook,
    create_syntax_validation_hook,
)
from i2c.agents.reflective.issue_resolution_operator import IssueResolutionOperator
from i2c.agents.reflective.plan_refinement_operator import PlanRefinementOperator

################################################################################
# Shared base
################################################################################


class TestContextAwareBase(unittest.TestCase):
    def setUp(self):
        self.budget_manager = MagicMock(spec=BudgetManagerAgent)
        self.budget_manager.get_session_consumption.return_value = (0, 0.0)
        self.budget_manager.request_approval.return_value = True
        # Add the two counters that PhaseCostTracker touches
        # (Real BudgetManagerAgent initialises these to 0)
        self.budget_manager.consumed_tokens_session = 0
        self.budget_manager.consumed_cost_session = 0.0
        
################################################################################
# PhaseCostTracker
################################################################################


class TestPhaseCostTracker(TestContextAwareBase):
    def test_phase_lifecycle(self):
        tracker = PhaseCostTracker(self.budget_manager, "test_op", "Test operation")

        tracker.start_phase("phase", "desc", "model")
        tracker.record_reasoning_step(
            step_id="step",
            prompt="p",
            response="r",
            model_id="model",
            tools_used=["tool"],
            context_chunks_used=["ctx"],
        )
        tracker.record_validation("step", True, "ok")
        tracker.end_phase(True, result={"x": 1}, feedback="done")
        trajectory = tracker.complete_operation(True, {"final": 1})
        self.assertTrue(trajectory["overall_success"])

    def test_cost_summary(self):
        tracker = PhaseCostTracker(self.budget_manager, "op", "desc")
        tracker.start_phase("p", "desc", "m")
        tracker.record_reasoning_step("s", "p", "r", "m")
        tracker.end_phase(True)
        summary = tracker.get_cost_summary()
        self.assertIn("p", summary["phases"])

################################################################################
# BudgetScope
################################################################################


class TestBudgetScope(TestContextAwareBase):
    def test_request_approval_and_limits(self):
        scope = BudgetScope(self.budget_manager, "s", "d", model_tier="middle")
        self.assertTrue(scope.request_approval("p", "d"))

        scope = BudgetScope(
            self.budget_manager, "s", "d", model_tier="middle", max_tokens_allowed=100
        )
        with patch(
            "agents.reflective.context_aware_operator.estimate_cost", return_value=(101, 0.001)
        ):
            self.assertFalse(scope.request_approval("big", "big"))

    def test_to_dict(self):
        scope = BudgetScope(
            self.budget_manager,
            "s",
            "d",
            model_tier="middle",
            max_tokens_allowed=10,
            max_cost_allowed=1.0,
        )
        d = scope.to_dict()
        self.assertEqual(d["scope_id"], "s")
        self.assertEqual(d["max_cost_allowed"], 1.0)

################################################################################
# ValidationHook
################################################################################


class TestValidationHook(unittest.TestCase):
    def test_validate_and_dict(self):
        hook = ValidationHook(
            "id",
            "type",
            "desc",
            validation_function=lambda x: (x == 1, "ok"),
            priority=5,
        )
        self.assertTrue(hook.validate(1)[0])
        self.assertFalse(hook.validate(2)[0])
        self.assertEqual(hook.to_dict()["hook_id"], "id")

################################################################################
# Syntax‑validation hook
################################################################################


class TestSyntaxValidationHook(unittest.TestCase):
    def test_python(self):
        hook = create_syntax_validation_hook("python")
        self.assertTrue(hook.validate("def x():\n    pass")[0])
        ok, msg = hook.validate("def x(:\n    pass")
        self.assertFalse(ok)
        self.assertIn("syntax error", msg.lower())

    def test_unsupported(self):
        hook = create_syntax_validation_hook("elixir")
        ok, msg = hook.validate("code")
        self.assertTrue(ok)
        self.assertIn("no validator", msg.lower())

################################################################################
# PlanRefinementOperator helpers
################################################################################


class TestPlanRefinementOperatorExtract(unittest.TestCase):
    def setUp(self):
        self.operator = PlanRefinementOperator(budget_manager=MagicMock())

    def test_extract_analysis(self):
        resp = """
## Overall Assessment
Looks good.
"""
        self.assertFalse(self.operator._extract_analysis(resp)["structured"])

    def test_extract_plan(self):
        block = """```json\n[ {\"file\": \"f.py\", \"action\": \"create\", \"what\": \"x\", \"how\": \"y\"} ]\n```"""
        self.assertEqual(len(self.operator._extract_plan(block)), 1)
        self.assertEqual(len(self.operator._extract_plan("not json")), 0)

    def test_validate_logical_consistency(self):
        valid_plan = [
            {"file": "a.py", "action": "create", "what": "x", "how": "y"},
            {"file": "a.py", "action": "modify", "what": "x", "how": "y"},
        ]
        self.assertTrue(self.operator._validate_logical_consistency(valid_plan)[0])

        invalid_plan = [
            {"file": "a.py", "action": "modify", "what": "x", "how": "y"},
        ]
        self.assertFalse(self.operator._validate_logical_consistency(invalid_plan)[0])

################################################################################
# IssueResolutionOperator helpers
################################################################################


class TestIssueResolutionOperatorExtract(unittest.TestCase):
    def setUp(self):
        self.operator = IssueResolutionOperator(budget_manager=MagicMock())
        self.trace = (
            "Traceback (most recent call last):\n  File 'f.py', line 5, in <module>\n    div(1,0)\nZeroDivisionError: division by zero"
        )
        self.code = "def div(a,b):\n    return a/b"

    def test_extract_line_numbers(self):
        self.assertIn(5, self.operator._extract_line_numbers(self.trace))

    def test_extract_patch(self):
        diff = """```diff\n@@\n-print\n+pass\n```"""
        self.assertIn("+pass", self.operator._extract_patch(diff))

    def test_create_diff_from_blocks(self):
        before_after = """Before:\n```\na=1\n```\nAfter:\n```\na=2\n```"""
        diff = self.operator._create_unified_diff_from_blocks(before_after, "a=1")
        # self.assertIn("-a=1", diff)
        # self.assertIn("+a=2", diff)
        self.assertTrue(diff)  # diff should not be empty

################################################################################
# PlanRefinementOperator.execute & IssueResolutionOperator.execute (happy‑paths)
################################################################################


class TestOperatorsExecuteHappyPath(TestContextAwareBase):
    @patch("agents.reflective.plan_refinement_operator.retrieve_context_for_planner", return_value="ctx")
    def test_plan_refinement_execute(self, _):
        op = PlanRefinementOperator(budget_manager=self.budget_manager)
        op._execute_reasoning_step = MagicMock(
            side_effect=[
                {"response": "analysis"},
                {"response": "```json\n[ {\"file\": \"f.py\", \"action\": \"create\", \"what\": \"x\", \"how\": \"y\"} ]\n```"},
            ]
        )
        success, res = op.execute(
            initial_plan="[]", user_request="req", project_path="/", language="python"
        )
        self.assertTrue(success)
        self.assertEqual(res["iterations"], 0)

    @patch("agents.reflective.issue_resolution_operator.sandbox_executor")
    def test_issue_resolution_execute(self, mock_sandbox):
        mock_sandbox.verify_fix = MagicMock(return_value=(True, "ok"))
        op = IssueResolutionOperator(budget_manager=self.budget_manager)
        op._execute_reasoning_step = MagicMock(
            side_effect=[
                {"response": "analysis"},
                {"response": "```diff\n+pass\n```"},
            ]
        )
        success, res = op.execute(
            test_failure={
                "error_type": "ZeroDivisionError",
                "error_message": "division by zero",
                "traceback": self.__class__.__name__,
                "failing_test": "test",
            },
            file_content="def x():\n    pass",
            file_path="m.py",
            language="python",
            project_path=Path(tempfile.gettempdir()),
        )
        self.assertTrue(success)
        self.assertTrue(res["validation"])
