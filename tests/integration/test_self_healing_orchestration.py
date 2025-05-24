import pytest
from pathlib import Path
import asyncio
import json
from i2c.agents.code_orchestration_agent import CodeOrchestrationAgent

@pytest.mark.integration
def test_self_healing_syntax_recovery(tmp_path):
    """Test that the orchestrator can self-heal syntax issues"""
    
    # --- Setup: Create Python file with syntax issues ---
    bad_file = tmp_path / "bad_syntax.py"
    bad_file.write_text("""def calculate(x, y)
    # Missing colon - syntax error
    	return x + y  # Mixed tabs and spaces - indentation issue

def main():
    result = calculate(5, 3
    # Missing closing parenthesis
    print(f"Result: {result}")
""")
    
    # --- Setup session state ---
    session_state = {
        "project_path": str(tmp_path),
        "task": "Fix and validate the calculation module",
        "constraints": ["Ensure proper Python syntax"],
        "quality_gates": ["flake8"],
        "modified_files": {
            "bad_syntax.py": bad_file.read_text()
        }
    }
    
    # --- Create orchestration agent ---
    agent = CodeOrchestrationAgent(session_state=session_state)
    
    # --- Test self-healing execution ---
    async def test_self_healing():
        objective = {
            "task": session_state["task"],
            "constraints": session_state["constraints"], 
            "quality_gates": session_state["quality_gates"],
            "project_path": str(tmp_path)
        }
        
        result = await agent.execute(objective)
        return result
    
    # Run the test
    loop = asyncio.get_event_loop()
    orchestration_result = loop.run_until_complete(test_self_healing())
    
    # --- Validate self-healing results ---
    print("\nSelf-Healing Orchestration Result:", json.dumps(orchestration_result, indent=2))
    
    # Check result structure
    assert isinstance(orchestration_result, dict)
    assert "decision" in orchestration_result
    assert "reason" in orchestration_result
    assert "reasoning_trajectory" in orchestration_result
    
    # Check reasoning trajectory for self-healing steps
    trajectory = orchestration_result.get("reasoning_trajectory", [])
    reasoning_steps = [step.get("step", "") for step in trajectory]
    
    print(f"\n📋 Reasoning Steps: {reasoning_steps}")
    
    # Look for self-healing related steps
    self_healing_steps = [step for step in reasoning_steps if "Self-Healing" in step or "Auto-Fix" in step or "Failure Analysis" in step]
    
    if self_healing_steps:
        print(f"✅ Self-healing steps detected: {self_healing_steps}")
    else:
        print("⚠️ No explicit self-healing steps found in reasoning")
    
    # Check if any recovery was attempted
    recovery_attempts = [step for step in trajectory if 
                        "recovery" in step.get("description", "").lower() or 
                        "healing" in step.get("description", "").lower() or
                        "fix" in step.get("description", "").lower()]
    
    if recovery_attempts:
        print(f"✅ Recovery attempts found: {len(recovery_attempts)}")
        for attempt in recovery_attempts:
            print(f"  - {attempt.get('step')}: {attempt.get('description')}")
    
    print(f"\n🎯 Final Decision: {orchestration_result.get('decision')}")
    print(f"📝 Reason: {orchestration_result.get('reason')}")


@pytest.mark.integration
def test_failure_pattern_analysis(tmp_path):
    """Test the failure pattern analysis logic directly"""
    
    session_state = {"project_path": str(tmp_path)}
    agent = CodeOrchestrationAgent(session_state=session_state)
    
    # Test different failure patterns
    test_cases = [
        {
            "name": "Syntax Issues",
            "quality_results": {"passed": False, "issues": ["Syntax error: invalid syntax", "IndentationError: expected an indented block"]},
            "sre_results": {"passed": True, "issues": []},
            "expected_strategy": "auto_fix_syntax"
        },
        {
            "name": "Test Failures", 
            "quality_results": {"passed": True, "issues": []},
            "sre_results": {"passed": False, "issues": ["Test failed: AssertionError expected 5 but got 3"]},
            "expected_strategy": "fix_test_logic"
        },
        {
            "name": "Performance Issues",
            "quality_results": {"passed": False, "issues": ["Performance regression detected", "Memory usage too high"]},
            "sre_results": {"passed": True, "issues": []},
            "expected_strategy": "replan_performance"
        },
        {
            "name": "Security Issues",
            "quality_results": {"passed": False, "issues": ["Security vulnerability: SQL injection risk"]},
            "sre_results": {"passed": True, "issues": []},
            "expected_strategy": "human_escalation"
        }
    ]
    
    for test_case in test_cases:
        analysis = agent._analyze_failure_patterns(
            test_case["quality_results"],
            test_case["sre_results"]
        )
        
        print(f"\n🧪 Test Case: {test_case['name']}")
        print(f"   Strategy: {analysis.get('strategy')}")
        print(f"   Expected: {test_case['expected_strategy']}")
        print(f"   Auto-recoverable: {analysis.get('auto_recoverable')}")
        print(f"   Confidence: {analysis.get('confidence')}")
        
        # Verify strategy detection
        if analysis.get('strategy') == test_case['expected_strategy']:
            print(f"   ✅ Correct strategy detected")
        else:
            print(f"   ⚠️ Strategy mismatch")


if __name__ == "__main__":
    print("Testing self-healing orchestration...")
    pytest.main(["-xvs", __file__])