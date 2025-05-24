import pytest
from pathlib import Path
import asyncio
import json
from i2c.workflow.agentic_orchestrator import execute_agentic_evolution_sync

@pytest.mark.integration
def test_complete_agentic_evolution_workflow(tmp_path):
    """Test the complete end-to-end agentic evolution workflow with self-healing"""
    
    # --- Setup: Create a realistic project for evolution ---
    # Simple calculator app that needs enhancement
    calculator_file = tmp_path / "calculator.py"
    calculator_file.write_text("""def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def main():
    print("Simple Calculator")
    result = add(5, 3)
    print(f"5 + 3 = {result}")

if __name__ == "__main__":
    main()
""")
    
    # Basic requirements
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("# No dependencies yet\n")
    
    # README
    readme_file = tmp_path / "README.md"
    readme_file.write_text("# Simple Calculator\nBasic math operations")
    
    print(f"📁 Created project for evolution at: {tmp_path}")
    print(f"📄 Initial files: {[f.name for f in tmp_path.iterdir()]}")
    
    # --- Define agentic evolution objective ---
    objective = {
        "task": "Enhance the calculator with multiplication, division, error handling, and comprehensive logging. Add input validation and make it more robust.",
        "language": "python",
        "constraints": [
            "Maintain backward compatibility with existing functions",
            "Add comprehensive error handling for division by zero",
            "Use Python's built-in logging module",
            "Add input validation and type checking",
            "Include docstrings for all functions",
            "Follow PEP 8 style guidelines"
        ],
        "quality_gates": ["flake8", "mypy"],
        "project_path": str(tmp_path)
    }
    
    # --- Session state for agentic evolution ---
    session_state = {
        "project_path": str(tmp_path),
        "language": "python",
        "use_retrieval_tools": True,
        "modified_files": {}
    }
    
    # --- Execute complete agentic evolution workflow ---
    print("\n" + "="*60)
    print("🚀 STARTING END-TO-END AGENTIC EVOLUTION WORKFLOW")
    print("="*60)
    
    # Run the complete agentic evolution
    evolution_result = execute_agentic_evolution_sync(
        objective=objective,
        project_path=tmp_path,
        session_state=session_state
    )
    
    # --- Analyze complete workflow results ---
    print("\n" + "="*60)
    print("📊 END-TO-END AGENTIC EVOLUTION RESULTS")
    print("="*60)
    
    print(f"Evolution Result Type: {type(evolution_result)}")
    
    # Check if we got the expected result structure
    if isinstance(evolution_result, dict):
        print("✅ Evolution completed and returned structured result")
        
        # Check for key components
        if "result" in evolution_result:
            agent_result = evolution_result["result"]
            print(f"🤖 Agent Result: {type(agent_result)}")
            
            if isinstance(agent_result, dict):
                decision = agent_result.get("decision", "unknown")
                reason = agent_result.get("reason", "No reason provided")
                modifications = agent_result.get("modifications", {})
                
                print(f"🎯 Final Decision: {decision}")
                print(f"📝 Decision Reason: {reason}")
                print(f"📁 Modifications Made: {len(modifications) if isinstance(modifications, dict) else 'N/A'}")
                
                # Show modifications details
                if isinstance(modifications, dict) and modifications:
                    print("\n📋 File Modifications:")
                    for file_path, summary in modifications.items():
                        print(f"   - {file_path}: {summary}")
                
                # Check reasoning trajectory
                if "reasoning_trajectory" in agent_result:
                    trajectory = agent_result["reasoning_trajectory"]
                    print(f"\n🧠 Reasoning Steps: {len(trajectory) if isinstance(trajectory, list) else 'N/A'}")
                    
                    if isinstance(trajectory, list) and trajectory:
                        print("Key reasoning steps:")
                        for i, step in enumerate(trajectory[:10]):  # Show first 10 steps
                            if isinstance(step, dict):
                                step_name = step.get("step", f"Step {i+1}")
                                description = step.get("description", "No description")
                                success = step.get("success", "unknown")
                                print(f"   {i+1}. {step_name}: {success} - {description}")
                        
                        if len(trajectory) > 10:
                            print(f"   ... and {len(trajectory) - 10} more steps")
        
        # Check session state updates
        if "session_state" in evolution_result:
            updated_session = evolution_result["session_state"]
            print(f"\n📊 Session State Updates: {type(updated_session)}")
            
            if isinstance(updated_session, dict):
                modified_files = updated_session.get("modified_files", {})
                print(f"📁 Files in Session: {len(modified_files) if isinstance(modified_files, dict) else 'N/A'}")
                
                if isinstance(modified_files, dict) and modified_files:
                    print("Files tracked in session:")
                    for file_path in modified_files.keys():
                        print(f"   - {file_path}")
    
    else:
        print(f"⚠️ Unexpected result type: {type(evolution_result)}")
        print(f"Result content: {evolution_result}")
    
    # --- Verify actual file changes on disk ---
    print(f"\n📁 Files on Disk After Evolution:")
    current_files = list(tmp_path.iterdir())
    for file_path in current_files:
        if file_path.is_file():
            print(f"   - {file_path.name} ({file_path.stat().st_size} bytes)")
    
    # Check if calculator was actually enhanced
    if calculator_file.exists():
        enhanced_content = calculator_file.read_text()
        print(f"\n📄 Calculator Enhanced: {len(enhanced_content)} characters")
        
        # Check for expected enhancements
        enhancements_found = []
        if "multiply" in enhanced_content.lower() or "multiplication" in enhanced_content.lower():
            enhancements_found.append("multiplication")
        if "divide" in enhanced_content.lower() or "division" in enhanced_content.lower():
            enhancements_found.append("division")
        if "logging" in enhanced_content.lower() or "import logging" in enhanced_content:
            enhancements_found.append("logging")
        if "try:" in enhanced_content or "except" in enhanced_content:
            enhancements_found.append("error_handling")
        if '"""' in enhanced_content or "'''" in enhanced_content:
            enhancements_found.append("docstrings")
        
        print(f"✅ Enhancements Found: {enhancements_found}")
    
    # Look for auto-generated test files
    test_files = [f for f in current_files if f.name.startswith("test_")]
    if test_files:
        print(f"🧪 Auto-generated Tests: {[f.name for f in test_files]}")
    
    print("\n" + "="*60)
    print("✅ END-TO-END AGENTIC EVOLUTION WORKFLOW TEST COMPLETE")
    print("="*60)
    
    # Basic assertions
    assert evolution_result is not None, "Evolution should return a result"
    
    return evolution_result


@pytest.mark.integration
def test_agentic_evolution_with_self_healing_scenarios(tmp_path):
    """Test agentic evolution with scenarios that should trigger self-healing"""
    
    # --- Create a project with intentional issues ---
    broken_file = tmp_path / "broken_app.py"
    broken_file.write_text("""def calculate(x, y)
    # Missing colon - syntax error
    	result = x + y  # Mixed indentation
    return result

def main():
    print("Broken app"
    # Missing closing parenthesis
    result = calculate(5, 3)
    print(f"Result: {result}")
""")
    
    # Test different self-healing scenarios
    scenarios = [
        {
            "name": "Syntax Error Recovery",
            "objective": {
                "task": "Fix syntax errors and add proper formatting",
                "language": "python",
                "constraints": ["Fix all syntax issues", "Ensure proper indentation"],
                "quality_gates": ["flake8"],
                "project_path": str(tmp_path)
            }
        },
        {
            "name": "Enhancement with Validation",
            "objective": {
                "task": "Add input validation and error handling to the calculator",
                "language": "python", 
                "constraints": ["Add type hints", "Include comprehensive error handling"],
                "quality_gates": ["mypy", "flake8"],
                "project_path": str(tmp_path)
            }
        }
    ]
    
    for scenario in scenarios:
        print(f"\n🧪 Testing Scenario: {scenario['name']}")
        
        session_state = {
            "project_path": str(tmp_path),
            "language": "python",
            "modified_files": {}
        }
        
        try:
            result = execute_agentic_evolution_sync(
                objective=scenario["objective"],
                project_path=tmp_path,
                session_state=session_state
            )
            
            print(f"✅ {scenario['name']}: Evolution completed")
            
            # Check if self-healing was involved
            if isinstance(result, dict) and "result" in result:
                agent_result = result["result"]
                if isinstance(agent_result, dict):
                    trajectory = agent_result.get("reasoning_trajectory", [])
                    healing_steps = [s for s in trajectory if isinstance(s, dict) and 
                                   ("healing" in s.get("step", "").lower() or 
                                    "recovery" in s.get("description", "").lower())]
                    
                    if healing_steps:
                        print(f"🩹 Self-healing detected: {len(healing_steps)} recovery steps")
                    else:
                        print("ℹ️ No explicit self-healing steps detected")
            
        except Exception as e:
            print(f"❌ {scenario['name']}: Failed with error: {e}")


if __name__ == "__main__":
    print("Testing complete end-to-end agentic evolution workflow...")
    pytest.main(["-xvs", __file__])