# tests/integration/test_full_integration.py

import json
import pytest
from pathlib import Path

from i2c.agents.modification_team.code_modification_manager_agno import apply_modification
from i2c.agents.modification_team.patch import Patch
from i2c.agents.modification_team.code_modification_manager import (
    AnalyzerAdapter,
    ModifierAdapter,
    ValidatorAdapter,
    AnalysisResult,
    ModificationPlan,
    ValidationReport,
)

@pytest.fixture
def sample_file(tmp_path):
    # Create a dummy Python file
    f = tmp_path / "i2c_test" / "test.py"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("a = 1\n")
    return f

def test_full_manager_pipeline(monkeypatch, sample_file):
    project_root = sample_file.parent

    # 1) Analyzer → empty analysis
    monkeypatch.setattr(
        AnalyzerAdapter,
        "analyze",
        lambda self, req: AnalysisResult(details=""),
    )

    # 2) Modifier → well-formed JSON payload
    def fake_modify(self, request, analysis):
        payload = {
            "file_path": "test.py",
            "original": "a = 1\n",
            "modified": "a = 1\nprint('done')\n",
        }
        return ModificationPlan(diff_hints=json.dumps(payload))
    monkeypatch.setattr(ModifierAdapter, "modify", fake_modify)

    # 3) Validator → always pass (new signature)
    def fake_validate(self, req, plan, analysis):
        return ValidationReport(ok=True, messages=["PASSED"])
    monkeypatch.setattr(ValidatorAdapter, "validate", fake_validate)

    # 4) Run the real Manager path
    step = {"dummy": "data"}
    result = apply_modification(step, project_root)

    # 5) Normalize into a diff string
    if isinstance(result, Patch):
        diff = result.unified_diff
    else:
        # fallback dict: extract from raw_reply
        raw = result.get("raw_reply", "")
        # pull everything between "## Patch" and the next "##"
        body = raw.split("## Patch",1)[1]
        diff = body.split("\n##",1)[0].strip()

    # 6) Assertions on the diff
    assert "--- test.py (original)" in diff, "Original header missing"
    assert "+++ test.py (modified)" in diff, "Modified header missing"
    assert "+print('done')" in diff, "New print line missing"
    # ensure exactly one hunk
    assert sum(1 for line in diff.splitlines() if line.startswith("@@")) == 1
