import json
from pathlib import Path
import difflib
from unittest import TestCase
from unittest.mock import patch, MagicMock


def extract_json(content: str) -> dict:
    """
    Extract and parse the first valid JSON object from a string.
    Uses bracket counting to handle nested braces.
    """
    brace_count = 0
    start_idx = None

    for idx, char in enumerate(content):
        if char == '{':
            if brace_count == 0:
                start_idx = idx
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx is not None:
                json_candidate = content[start_idx:idx+1]
                try:
                    return json.loads(json_candidate)
                except json.JSONDecodeError:
                    continue

    raise ValueError(f"Content is a string but no valid JSON found: {content}")


class TestIssueResolutionOperator(TestCase):
    def setUp(self):
        from i2c.agents.reflective.issue_resolution_operator import IssueResolutionOperator

        self.operator = IssueResolutionOperator(budget_manager=MagicMock())

        # Stub reasoning steps: first analysis, then modifier response
        self.operator._execute_reasoning_step = MagicMock()
        self.operator._execute_reasoning_step.side_effect = [
            {"response": "Here is the analysis:\n{\"analysis\": \"Test analysis done\", \"dependencies\": {\"ripple_risk\": [\"math.divide\"]}}"},
            {"response": "Some log info...\n{\"file_path\": \"math.py\", \"original\": \"def divide(a, b):\\n    return a / b\\n\", \"modified\": \"def divide(a, b):\\n    if b == 0:\\n        return float('inf')\\n    return a / b\\n\"}"}
        ]

        # Disable validation hooks so valid_fix is always True
        self.operator.validation_hooks = {}

    @patch("i2c.agents.sre_team.sandbox_executor")
    def test_simple_issue_resolution(self, mock_sandbox_executor):
        file_content = "def divide(a, b):\n    return a / b\n"
        modified_content = "def divide(a, b):\n    if b == 0:\n        return float('inf')\n    return a / b\n"

        test_failure = {
            "error_type": "ZeroDivisionError",
            "error_message": "division by zero",
            "traceback": (
                "Traceback (most recent call last):\n"
                "  File \"test_math.py\", line 5, in test_divide\n"
                "    result = divide(5, 0)\n"
                "ZeroDivisionError: division by zero"
            ),
            "failing_test": (
                "def test_divide():\n"
                "    result = divide(5, 0)\n"
                "    assert result == float('inf')\n"
            ),
        }

        # Simulate sandbox verification success
        mock_sandbox_executor.verify_fix.return_value = (True, "All tests passed")

        # Patch diff creation to handle real diffing
        def real_diff_creator(original, modified):
            diff_lines = list(difflib.unified_diff(
                original.splitlines(keepends=True),
                modified.splitlines(keepends=True),
                fromfile='a/math.py',
                tofile='b/math.py'
            ))
            return ''.join(diff_lines)

        def fake_create_unified_diff(self_or_blocks, blocks=None):
            if blocks is None:
                blocks = self_or_blocks
            if isinstance(blocks, str):
                blocks = extract_json(blocks)
            return real_diff_creator(blocks["original"], blocks["modified"])

        self.operator._create_unified_diff_from_blocks = MagicMock(side_effect=fake_create_unified_diff)

        success, result = self.operator.execute(
            test_failure=test_failure,
            file_content=file_content,
            file_path="math.py",
            language="python",
            project_path=Path("/fake/path"),
        )

        expected_patch = ''.join(list(difflib.unified_diff(
            file_content.splitlines(keepends=True),
            modified_content.splitlines(keepends=True),
            fromfile='a/math.py',
            tofile='b/math.py'
        )))

        self.assertTrue(success)
        self.assertTrue(result["test_verification"])
        self.assertEqual(result["fixed_content"], modified_content)
        self.assertEqual(result["patch"], expected_patch)