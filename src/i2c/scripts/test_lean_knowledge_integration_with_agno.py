# test_enhanced_agno_knowledge.py
"""
Enhanced test that ensures core agents properly apply AGNO knowledge with stronger validation.
"""
from i2c.bootstrap import initialize_environment
initialize_environment()

import json
from pathlib import Path
from i2c.workflow.scenario_processor import run_scenario
from i2c.agents.budget_manager import BudgetManagerAgent
from i2c.cli.controller import canvas

def create_stronger_agno_test_scenario():
    """Create a scenario with explicit AGNO requirements that forces pattern usage"""
    
    scenario_dir = Path("./test_scenarios")
    scenario_dir.mkdir(parents=True, exist_ok=True)
    
    scenario_data = {
        "name": "Enhanced AGNO Knowledge Application Test",
        "steps": [
            {
                "type": "knowledge",
                "name": "Load AGNO Framework Documentation",
                "doc_path": "src/i2c/docs/agno_cheat_sheet.pdf",
                "doc_type": "AGNO Framework cheat sheet",
                "framework": "AGNO",
                "version": "latest",
                "global": True
            },
            {
                "type": "knowledge",
                "name": "Load AGNO Framework Documentation",
                "doc_path": "src/i2c/docs/agno_guide.pdf",
                "doc_type": "AGNO Framework Guide",
                "framework": "AGNO",
                "version": "latest",
                "global": True
            },
            {
                "type": "initial_generation",
                "name": "Generate AGNO-Compliant Multi-Agent System",
                "prompt": """Create a task management system using AGNO framework with STRICT adherence to these patterns:

REQUIRED AGNO PATTERNS (must be implemented exactly as shown):

1. IMPORTS (mandatory):
```python
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat
# OR from agno.models.anthropic import Claude
```

2. AGENT CREATION (mandatory - follow this exact pattern):
```python
task_agent = Agent(
    name="TaskManagerAgent",
    model=OpenAIChat(id="gpt-4o"),
    instructions=["Manage tasks efficiently", "Prioritize by deadline"],
    tools=[],
    reasoning=True,
    markdown=True
)
```

3. TEAM COORDINATION (mandatory):
```python
team = Team(
    name="TaskManagementTeam", 
    members=[agent1, agent2],
    mode="coordinate",
    instructions=["Work together to manage tasks"]
)
```

4. AGENT EXECUTION:
```python
result = agent.run("Create a new task")
team_result = team.run("Coordinate task management")
```

REQUIREMENTS:
- Create exactly 3 agents: TaskCreatorAgent, TaskManagerAgent, PriorityAgent
- Each agent MUST use Agent(model=..., instructions=..., tools=...)
- MUST import and use OpenAIChat or Claude model
- MUST create a Team with coordinate mode
- MUST include reasoning=True for complex agents
- MUST include proper agent names and instructions
- Follow the AGNO cheat sheet patterns exactly

The system should handle task creation, management, and prioritization using proper AGNO multi-agent coordination.""",
                "project_name": "enhanced_agno_test"
            },
            {
                "type": "agentic_evolution",
                "objective": {
                    "task": "Enhance the system with advanced AGNO patterns: Add memory persistence, custom tools with @tool decorator, and a Workflow class. Ensure all agents follow AGNO best practices with proper model configuration, tools, and instructions.",
                    "constraints": [
                        "MANDATORY: Use Agent(model=OpenAIChat(...), tools=[...], instructions=[...])",
                        "MANDATORY: Import from agno.models.openai or agno.models.anthropic", 
                        "MANDATORY: Create Team with proper mode and members",
                        "MANDATORY: Include reasoning=True for analytical agents",
                        "MANDATORY: Use @tool decorator for custom tools",
                        "MANDATORY: Follow AGNO cheat sheet patterns exactly",
                        "MANDATORY: Each agent must have specialized role and instructions"
                    ]
                }
            }
        ]
    }
    
    scenario_path = scenario_dir / "enhanced_agno_test.json"
    with open(scenario_path, 'w', encoding='utf-8') as f:
        json.dump(scenario_data, f, indent=2, ensure_ascii=False)
    
    return scenario_path

def analyze_agno_compliance(project_path: Path):
    """Enhanced analysis focusing on exact AGNO pattern compliance"""
    
    if not project_path.exists():
        return {"compliance_score": 0, "errors": ["Project not found"]}
    
    python_files = list(project_path.glob("**/*.py"))
    if not python_files:
        return {"compliance_score": 0, "errors": ["No Python files generated"]}
    
    # Critical AGNO compliance checks
    compliance_checks = {
        "agno_imports": {
            "patterns": [
                r"from\s+agno\.agent\s+import\s+Agent",
                r"from\s+agno\.team\s+import\s+Team", 
                r"from\s+agno\.models\.(openai|anthropic|groq)"
            ],
            "weight": 30,
            "found": 0
        },
        "proper_agent_creation": {
            "patterns": [
                r"Agent\s*\(\s*.*model\s*=.*OpenAI|Claude|Groq",
                r"Agent\s*\(\s*.*instructions\s*=",
                r"Agent\s*\(\s*.*name\s*="
            ],
            "weight": 25,
            "found": 0
        },
        "team_coordination": {
            "patterns": [
                r"Team\s*\(\s*.*members\s*=",
                r"Team\s*\(\s*.*mode\s*=\s*[\"']coordinate[\"']",
                r"Team\s*\(\s*.*name\s*="
            ],
            "weight": 20,
            "found": 0
        },
        "execution_patterns": {
            "patterns": [
                r"\.run\s*\(",
                r"agent\w*\.run",
                r"team\w*\.run"
            ],
            "weight": 15,
            "found": 0
        },
        "advanced_features": {
            "patterns": [
                r"reasoning\s*=\s*True",
                r"@tool",
                r"tools\s*=\s*\[",
                r"markdown\s*=\s*True"
            ],
            "weight": 10,
            "found": 0
        }
    }
    
    all_content = ""
    code_examples = []
    
    # Analyze all files
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                all_content += content + "\n"
                
                # Extract Agent and Team creation examples
                import re
                agent_examples = re.findall(r'(\w+\s*=\s*Agent\s*\([^)]+\))', content, re.MULTILINE | re.DOTALL)
                team_examples = re.findall(r'(\w+\s*=\s*Team\s*\([^)]+\))', content, re.MULTILINE | re.DOTALL)
                
                code_examples.extend(agent_examples)
                code_examples.extend(team_examples)
                
        except Exception as e:
            canvas.warning(f"Error reading {file_path}: {e}")
    
    # Check compliance patterns
    for check_name, check_data in compliance_checks.items():
        for pattern in check_data["patterns"]:
            import re
            matches = re.findall(pattern, all_content, re.IGNORECASE | re.MULTILINE)
            if matches:
                check_data["found"] += len(matches)
    
    # Calculate compliance score
    total_score = 0
    max_score = 100
    
    for check_name, check_data in compliance_checks.items():
        if check_data["found"] > 0:
            total_score += check_data["weight"]
    
    compliance_percentage = (total_score / max_score) * 100
    
    # Determine compliance level
    if compliance_percentage >= 80:
        compliance_level = "Excellent"
    elif compliance_percentage >= 60:
        compliance_level = "Good"
    elif compliance_percentage >= 40:
        compliance_level = "Fair"
    else:
        compliance_level = "Poor"
    
    return {
        "compliance_score": compliance_percentage,
        "compliance_level": compliance_level,
        "checks": compliance_checks,
        "code_examples": code_examples[:5],  # First 5 examples
        "files_analyzed": len(python_files),
        "total_content_length": len(all_content)
    }

def test_enhanced_agno_knowledge():
    """Enhanced test with stricter AGNO compliance validation"""
    
    canvas.info("🚀 Enhanced AGNO Knowledge Application Test")
    canvas.info("=" * 60)
    
    budget_manager = BudgetManagerAgent(session_budget=None)
    
    try:
        # Step 1: Create enhanced scenario
        canvas.info("📝 Creating enhanced AGNO test scenario...")
        scenario_path = create_stronger_agno_test_scenario()
        
        # Step 2: Run scenario
        canvas.info("🎯 Running scenario with explicit AGNO requirements...")
        start_tokens, start_cost = budget_manager.get_session_consumption()
        
        success = run_scenario(str(scenario_path), budget_manager=budget_manager, debug=True)
        
        end_tokens, end_cost = budget_manager.get_session_consumption()
        total_tokens = end_tokens - start_tokens
        total_cost = end_cost - start_cost
        
        canvas.info(f"   💰 Resources: {total_tokens} tokens, ${total_cost:.6f}")
        canvas.info(f"   📊 Success: {'✅' if success else '❌'}")
        
        if not success:
            canvas.error("❌ Scenario failed - cannot validate AGNO compliance")
            return False
        
        # Step 3: Enhanced compliance analysis
        canvas.info("🔍 Analyzing AGNO compliance...")
        project_path = Path("./output/enhanced_agno_test")
        
        compliance_results = analyze_agno_compliance(project_path)
        
        # Step 4: Display detailed compliance results
        canvas.info("📊 AGNO Compliance Results:")
        canvas.info(f"   📁 Files analyzed: {compliance_results['files_analyzed']}")
        canvas.info(f"   🎯 Compliance score: {compliance_results['compliance_score']:.1f}%")
        canvas.info(f"   🏆 Compliance level: {compliance_results['compliance_level']}")
        
        # Show specific compliance checks
        canvas.info("\n📋 Detailed Compliance Analysis:")
        for check_name, check_data in compliance_results["checks"].items():
            status = "✅" if check_data["found"] > 0 else "❌"
            canvas.info(f"   {status} {check_name}: {check_data['found']} patterns found (weight: {check_data['weight']})")
        
        # Show code examples
        if compliance_results["code_examples"]:
            canvas.info("\n💻 Generated Code Examples:")
            for i, example in enumerate(compliance_results["code_examples"][:3]):
                canvas.info(f"   {i+1}. {example}")
        
        # Step 5: Final validation
        canvas.info("\n🏆 Final Validation:")
        
        # Enhanced success criteria
        validation_criteria = {
            "scenario_success": success,
            "compliance_acceptable": compliance_results["compliance_score"] >= 50,  # Raised threshold
            "files_generated": compliance_results["files_analyzed"] > 0,
            "agno_imports_found": compliance_results["checks"]["agno_imports"]["found"] > 0,
            "agent_creation_correct": compliance_results["checks"]["proper_agent_creation"]["found"] > 0,
            "cost_reasonable": total_cost < 1.0
        }
        
        passed = sum(validation_criteria.values())
        test_passed = passed >= 5  # Need 5/6 to pass
        
        for criterion, result in validation_criteria.items():
            status = "✅" if result else "❌"
            canvas.info(f"   {status} {criterion}")
        
        canvas.info(f"\n🎯 ENHANCED TEST RESULT: {'✅ PASSED' if test_passed else '❌ FAILED'}")
        canvas.info(f"   📊 Criteria met: {passed}/{len(validation_criteria)}")
        canvas.info(f"   🧠 AGNO compliance: {compliance_results['compliance_score']:.1f}%")
        
        # Specific feedback
        if test_passed:
            if compliance_results["compliance_score"] >= 80:
                canvas.success("🌟 Excellent AGNO knowledge application!")
            elif compliance_results["compliance_score"] >= 60:
                canvas.success("✅ Good AGNO knowledge application!")
            else:
                canvas.info("✅ Basic AGNO knowledge application working")
        else:
            canvas.warning("⚠️ AGNO knowledge application needs improvement:")
            if compliance_results["checks"]["agno_imports"]["found"] == 0:
                canvas.warning("   📦 Missing proper AGNO imports")
            if compliance_results["checks"]["proper_agent_creation"]["found"] == 0:
                canvas.warning("   🤖 Agents not created with proper AGNO patterns")
            if compliance_results["compliance_score"] < 50:
                canvas.warning("   📚 Knowledge not being applied effectively")
        
        return test_passed
        
    except Exception as e:
        canvas.error(f"❌ Enhanced test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_enhanced_agno_knowledge()
    print(f"\nEnhanced AGNO Test: {'✅ PASSED' if success else '❌ FAILED'}")
    exit(0 if success else 1)