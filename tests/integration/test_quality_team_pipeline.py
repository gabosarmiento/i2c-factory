import pytest
from pathlib import Path
from i2c.agents.quality_team.quality_team import build_quality_team
from agno.agent import Message

@pytest.mark.integration
def test_quality_lead_agent_direct_validate(tmp_path):
    from i2c.agents.quality_team.quality_team import QualityLeadAgent
    from pathlib import Path
    import asyncio

    file_path = tmp_path / "sample.py"
    file_path.write_text("def add(a, b):\n    return a + b\n\ndef unused():\n    pass\n")

    files_dict = {
        "sample.py": file_path.read_text()
    }

    quality_lead = QualityLeadAgent()
    
    results = asyncio.run(quality_lead.validate_changes(
        project_path=tmp_path,
        modified_files=files_dict,
        quality_gates=["flake8", "mypy"]
    ))

    assert isinstance(results, dict)
    assert "passed" in results
    assert "issues" in results
    assert "gate_results" in results
    print("✅ Quality check results:", results)
