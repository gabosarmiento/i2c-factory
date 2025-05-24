import pytest
from pathlib import Path
import asyncio
import json
from i2c.agents.code_orchestration_agent import CodeOrchestrationAgent

@pytest.mark.integration
def test_sre_direct_integration(tmp_path):
    """
    Test that the SRE checks work directly through CodeOrchestrationAgent
    without message delegation (avoiding LLM calls and 503 errors).
    """
    # --- Setup test files ---
    app_file = tmp_path / "app.py"
    app_file.write_text("""
def calculate(x, y):
    return x + y

def main():
    result = calculate(10, 20)
    print(f"Calculation result: {result}")
    return result

if __name__ == "__main__":
    main()
""")

    # --- Create requirements.txt to test dependency checking ---
    req_file = tmp_path / "requirements.txt" 
    req_file.write_text("requests==2.25.1\n")

    # --- Setup session state ---
    session_state = {
        "project_path": str(tmp_path),
        "modified_files": {
            "app.py": app_file.read_text()
        }
    }

    # --- Create orchestration agent ---
    agent = CodeOrchestrationAgent(session_state=session_state)
    
    # --- Test direct SRE integration ---
    async def test_direct_sre_checks():
        # Prepare modification result
        modification_result = {
            "modified_files": session_state["modified_files"]
        }
        
        # Call _run_operational_checks directly (no message passing)
        result = await agent._run_operational_checks(modification_result)
        
        return result
    
    # Run the async test
    loop = asyncio.get_event_loop()
    sre_response = loop.run_until_complete(test_direct_sre_checks())
    
    # --- Validate response structure ---
    print("\nDirect SRE Integration Response:", json.dumps(sre_response, indent=2))
    
    # Check required fields
    assert isinstance(sre_response, dict), "Response should be a dictionary"
    assert "passed" in sre_response, "Response should have 'passed' field"
    assert "issues" in sre_response, "Response should have 'issues' field"
    assert "check_results" in sre_response, "Response should have 'check_results' field"
    assert "summary" in sre_response, "Response should have 'summary' field"
    
    # Validate check_results structure
    check_results = sre_response.get("check_results", {})
    expected_checks = ["sandbox", "dependencies", "version_control"]
    
    for check_name in expected_checks:
        if check_name in check_results:
            check_result = check_results[check_name]
            assert isinstance(check_result, dict), f"{check_name} result should be dict"
            assert "passed" in check_result, f"{check_name} should have 'passed' field"
            assert "issues" in check_result, f"{check_name} should have 'issues' field"
            print(f"✅ {check_name} check format validated")
    
    # Validate summary structure
    summary = sre_response.get("summary", {})
    assert isinstance(summary, dict), "Summary should be a dictionary"
    assert "total_issues" in summary, "Summary should have total_issues"
    assert "deployment_ready" in summary, "Summary should have deployment_ready"
    
    # Validate issues is a list
    issues = sre_response.get("issues", [])
    assert isinstance(issues, list), "Issues should be a list"
    
    print(f"\n✅ Direct SRE integration test completed successfully")
    print(f"📊 Operational Status: {'READY' if sre_response.get('passed', False) else 'ISSUES FOUND'}")
    print(f"📋 Total Issues: {len(issues)}")
    
    return sre_response


@pytest.mark.integration
def test_sre_error_handling_direct(tmp_path):
    """Test SRE direct integration handles errors gracefully"""
    
    # --- Test with non-existent project path ---
    session_state = {
        "project_path": "/non/existent/path",
        "modified_files": {"test.py": "def test(): pass"}
    }
    
    agent = CodeOrchestrationAgent(session_state=session_state)
    
    async def test_error_handling():
        modification_result = {"modified_files": session_state["modified_files"]}
        result = await agent._run_operational_checks(modification_result)
        return result
    
    loop = asyncio.get_event_loop()
    error_response = loop.run_until_complete(test_error_handling())
    
    # Should handle gracefully without crashing
    assert isinstance(error_response, dict)
    assert "passed" in error_response
    assert "issues" in error_response
    
    print("✅ SRE direct error handling test completed")


if __name__ == "__main__":
    print("Running direct SRE integration tests...")
    pytest.main(["-xvs", __file__])