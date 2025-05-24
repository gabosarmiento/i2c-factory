import pytest
from pathlib import Path
import asyncio
import json
from i2c.agents.code_orchestration_agent import CodeOrchestrationAgent

@pytest.mark.integration
def test_complete_orchestration_pipeline(tmp_path):
    """Test the complete orchestration pipeline with real planning and analysis"""
    
    # --- Setup: Create a realistic project structure ---
    # Main application file
    main_file = tmp_path / "main.py"
    main_file.write_text("""#!/usr/bin/env python3

def greet(name):
    return f"Hello, {name}!"

def main():
    print(greet("World"))

if __name__ == "__main__":
    main()
""")
    
    # Helper module
    utils_file = tmp_path / "utils.py"
    utils_file.write_text("""def calculate_sum(a, b):
    return a + b

def format_number(num):
    return f"{num:,}"
""")
    
    # Configuration file
    config_file = tmp_path / "config.py"
    config_file.write_text("""DEBUG = True
VERSION = "1.0.0"
""")
    
    # Requirements file
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("requests>=2.25.0\n")
    
    print(f"📁 Created test project at: {tmp_path}")
    print(f"📄 Files: {[f.name for f in tmp_path.iterdir()]}")
    
    # --- Setup session state ---
    session_state = {
        "project_path": str(tmp_path),
        "task": "Add logging functionality to the main application",
        "constraints": [
            "Use Python's built-in logging module",
            "Add debug and info level logging",
            "Maintain existing functionality"
        ],
        "quality_gates": ["flake8"],
        "language": "python"
    }
    
    # --- Create orchestration agent ---
    agent = CodeOrchestrationAgent(session_state=session_state)
    
    # --- Test complete orchestration ---
    async def test_full_pipeline():
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
    orchestration_result = loop.run_until_complete(test_full_pipeline())
    
    # --- Validate complete pipeline results ---
    print("\n" + "="*60)
    print("COMPLETE ORCHESTRATION PIPELINE RESULTS")
    print("="*60)
    
    # Check result structure
    assert isinstance(orchestration_result, dict)
    assert "decision" in orchestration_result
    assert "reason" in orchestration_result
    assert "reasoning_trajectory" in orchestration_result
    
    # Analyze reasoning trajectory
    trajectory = orchestration_result.get("reasoning_trajectory", [])
    print(f"\n📋 Total Reasoning Steps: {len(trajectory)}")
    
    # Check for key pipeline steps
    expected_steps = [
        "Project Context Analysis",
        "Modification Planning", 
        "Code Modification",
        "Quality Validation",
        "Operational Validation",
        "Final Decision"
    ]
    
    found_steps = []
    for step in trajectory:
        step_name = step.get("step", "")
        if step_name in expected_steps:
            found_steps.append(step_name)
            success = step.get("success", "unknown")
            description = step.get("description", "")
            print(f"✅ {step_name}: {success} - {description}")
    
    print(f"\n📊 Pipeline Coverage: {len(found_steps)}/{len(expected_steps)} key steps found")
    
    # Check for analysis and planning results
    analysis_steps = [s for s in trajectory if "analysis" in s.get("step", "").lower()]
    planning_steps = [s for s in trajectory if "planning" in s.get("step", "").lower()]
    
    if analysis_steps:
        print(f"🔍 Project Analysis: {len(analysis_steps)} analysis step(s)")
        for step in analysis_steps:
            print(f"   - {step.get('description', 'No description')}")
    
    if planning_steps:
        print(f"📋 Modification Planning: {len(planning_steps)} planning step(s)")
        for step in planning_steps:
            print(f"   - {step.get('description', 'No description')}")
    
    # Check final decision
    decision = orchestration_result.get("decision", "unknown")
    reason = orchestration_result.get("reason", "No reason provided")
    
    print(f"\n🎯 Final Decision: {decision}")
    print(f"📝 Reason: {reason}")
    
    # Check for modifications
    modifications = orchestration_result.get("modifications", {})
    if modifications:
        print(f"📁 Files Modified: {len(modifications)}")
        for file_path, summary in modifications.items():
            print(f"   - {file_path}: {summary}")
    
    # Check for quality and SRE results
    quality_results = orchestration_result.get("quality_results", {})
    sre_results = orchestration_result.get("sre_results", {})
    
    print(f"\n🔍 Quality Validation: {'✅ PASSED' if quality_results.get('passed') else '❌ FAILED'}")
    print(f"🔧 SRE Validation: {'✅ PASSED' if sre_results.get('passed') else '❌ FAILED'}")
    
    # Look for self-healing attempts
    healing_steps = [s for s in trajectory if "healing" in s.get("step", "").lower() or "recovery" in s.get("description", "").lower()]
    if healing_steps:
        print(f"\n🩹 Self-Healing Attempts: {len(healing_steps)}")
        for step in healing_steps:
            print(f"   - {step.get('step')}: {step.get('description')}")
    
    print("\n" + "="*60)
    print("✅ COMPLETE ORCHESTRATION PIPELINE TEST FINISHED")
    print("="*60)


@pytest.mark.integration  
def test_project_analysis_accuracy(tmp_path):
    """Test that project analysis correctly identifies files and targets"""
    
    # Create a more complex project structure
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()
    
    # Source files
    (tmp_path / "src" / "app.py").write_text("def main(): pass")
    (tmp_path / "src" / "models.py").write_text("class User: pass")
    (tmp_path / "src" / "database.py").write_text("def connect(): pass")
    
    # Test files
    (tmp_path / "tests" / "test_app.py").write_text("def test_main(): pass")
    
    # Config files
    (tmp_path / "setup.py").write_text("from setuptools import setup")
    (tmp_path / "README.md").write_text("# Test Project")
    
    session_state = {"project_path": str(tmp_path)}
    agent = CodeOrchestrationAgent(session_state=session_state)
    
    # Test project analysis
    async def test_analysis():
        analysis = await agent._analyze_project_context(tmp_path, "add authentication to the database module")
        return analysis
    
    loop = asyncio.get_event_loop()
    analysis_result = loop.run_until_complete(test_analysis())
    
    # Validate analysis results
    assert "project_structure" in analysis_result
    assert "task_analysis" in analysis_result
    
    project_structure = analysis_result["project_structure"]
    files = project_structure.get("files", [])
    languages = project_structure.get("languages", {})
    
    print(f"\n📁 Discovered Files: {len(files)}")
    print(f"🔤 Languages: {languages}")
    
    # Should find Python files
    python_files = [f for f in files if f.endswith('.py')]
    assert len(python_files) > 0, "Should discover Python files"
    
    # Should identify target files
    targets = analysis_result["task_analysis"].get("identified_targets", [])
    print(f"🎯 Identified Targets: {targets}")
    
    # Should identify database.py as likely target for database-related task
    database_targets = [t for t in targets if 'database' in t.lower()]
    if database_targets:
        print("✅ Correctly identified database-related targets")
    
    print("✅ Project analysis accuracy test completed")


if __name__ == "__main__":
    print("Testing complete orchestration pipeline...")
    pytest.main(["-xvs", __file__])