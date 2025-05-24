import pytest
from pathlib import Path
import asyncio
import json
from i2c.agents.code_orchestration_agent import CodeOrchestrationAgent
from i2c.agents.sre_team.sre_team import build_sre_team

@pytest.mark.integration
def test_sre_validation_pipeline(tmp_path):
    """
    Test the SRE validation pipeline with real files and actual SRE team.
    This test exercises the _run_operational_checks method with live components.
    """
    # --- Setup a Python file that should trigger some operational checks ---
    file_name = tmp_path / "app.py"
    file_name.write_text("""
def add(a, b):
    # This function adds two numbers
    return a + b

def main():
    print("Hello World")
    result = add(5, 3)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
""")

    # --- Set up session state with operational objectives ---
    session_state = {
        "project_path": str(tmp_path),
        "objective": {
            "task": "Validate operational readiness of modified files"
        },
        "modified_files": {
            "app.py": file_name.read_text()
        }
    }

    # --- Create the code orchestration agent ---
    agent = CodeOrchestrationAgent(session_state=session_state)
    
    # --- Explicitly build and assign the SRE team ---
    agent.sre_team = build_sre_team(session_state=session_state)
    
    # Verify SRE team is properly initialized
    assert agent.sre_team is not None, "SRE team should be initialized"
    assert agent.sre_team.name == "SRETeam"
    
    # --- Run the operational validation pipeline ---
    async def run_operational_validation():
        # Prepare the modification result in the format expected by _run_operational_checks
        modification_result = {
            "modified_files": session_state["modified_files"]
        }
        
        # Run operational checks
        result = await agent._run_operational_checks(modification_result)
        
        return result
    
    # Run the async test
    loop = asyncio.get_event_loop()
    operational_result = loop.run_until_complete(run_operational_validation())
    
    # --- Validate results ---
    print("\nOperational validation output:", json.dumps(operational_result, indent=2))
    
    # Verify the result structure
    assert isinstance(operational_result, dict)
    assert "passed" in operational_result
    assert "issues" in operational_result
    assert "check_results" in operational_result
    assert "summary" in operational_result
    
    # Check for expected check results structure
    check_results = operational_result.get("check_results", {})
    expected_checks = ["sandbox", "dependencies", "version_control"]
    
    for check_name in expected_checks:
        if check_name in check_results:
            check_result = check_results[check_name]
            assert "passed" in check_result
            assert "issues" in check_result
            print(f"✅ {check_name} check structure is correct")
    
    # Summary should have expected fields
    summary = operational_result.get("summary", {})
    expected_summary_fields = ["total_issues", "deployment_ready"]
    
    for field in expected_summary_fields:
        if field in summary:
            print(f"✅ Summary field '{field}' present: {summary[field]}")
    
    print("\n✅ SRE Team delegation test completed successfully")


@pytest.mark.integration
def test_sre_team_direct_validation(tmp_path):
    """
    Test building the SRE team and verifying its name and structure
    """
    from i2c.agents.sre_team.sre_team import build_sre_team
    
    # --- Setup files ---
    file_path = tmp_path / "simple.py"
    file_path.write_text("""def hello():
    return "Hello, World!"
""")
    
    # --- Set up session state ---
    session_state = {
        "project_path": str(tmp_path),
        "modified_files": {
            "simple.py": file_path.read_text()
        }
    }
    
    # --- Build the SRE team ---
    team = build_sre_team(session_state=session_state)
    
    # --- Verify team was built correctly ---
    assert team is not None
    assert team.name == "SRETeam"
    
    # --- Verify team has required components ---
    assert len(team.members) > 0
    assert any(member.name == "SRELead" for member in team.members)
    
    print("\nSRE team created successfully with name:", team.name)
    print("Team members:", [member.name for member in team.members])


@pytest.mark.integration 
def test_sre_lead_agent_direct_validate(tmp_path):
    """Test the SRE Lead Agent validate_changes method directly"""
    from i2c.agents.sre_team.sre_team import SRELeadAgent
    import asyncio

    file_path = tmp_path / "test.py"
    file_path.write_text("def test_function():\n    return True\n")

    files_dict = {
        "test.py": file_path.read_text()
    }

    sre_lead = SRELeadAgent()
    
    results = asyncio.run(sre_lead.validate_changes(
        project_path=tmp_path,
        modified_files=files_dict
    ))

    assert isinstance(results, dict)
    assert "passed" in results
    assert "issues" in results
    assert "check_results" in results
    assert "summary" in results
    
    print("✅ SRE direct validation results:", results)


if __name__ == "__main__":
    print("Running SRE validation pipeline tests...")
    pytest.main(["-xvs", __file__])