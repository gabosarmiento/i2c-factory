# test_simple_agno_generation.py
"""
Simple test that generates an AGNO app and outputs files for manual LLM evaluation
"""
from i2c.bootstrap import initialize_environment
initialize_environment()

import json
from pathlib import Path
from i2c.workflow.scenario_processor import run_scenario
from i2c.agents.budget_manager import BudgetManagerAgent
from i2c.cli.controller import canvas

def create_simple_scenario():
    """Create a simple, clear scenario"""
    
    scenario_dir = Path("./test_scenarios")
    scenario_dir.mkdir(parents=True, exist_ok=True)
    
    scenario_data = {
        "project_name": "agno_task_system",
        "name": "AGNO Task Management System",
        "steps": [
            {
                "type": "knowledge",
                "name": "Load AGNO Cheat Sheet",
                "doc_path": "src/i2c/docs/agno_cheat_sheet.pdf",
                "doc_type": "AGNO Framework cheat sheet",
                "framework": "AGNO",
                "version": "latest",
                "project_name": "agno_task_system",
                "global": True,
                "force_refresh": False
            },
            {
                "type": "knowledge",
                "name": "Load AGNO Guide",
                "doc_path": "src/i2c/docs/agno_guide.pdf",
                "doc_type": "AGNO Framework Guide",
                "framework": "AGNO",
                "version": "latest",
                "project_name": "agno_task_system",
                "global": True,
                "force_refresh": False
            },
            {
                "type": "initial_generation",
                "name": "Generate Task System",
                "prompt": """Create a task management system using AGNO framework.

Requirements:
- System to create, manage, and prioritize tasks
- Tasks have: title, description, priority (high/medium/low), due date, status
- Multiple specialized components working together
- Use AGNO framework capabilities appropriately
- Make it production-ready with proper error handling
- Include a way to run and test the system

Build a complete, working application.""",
                "project_name": "agno_task_system"
            },
            {
                "type": "agentic_evolution",
                "name": "Evolve to AGNO Multi-Agent Pipeline",
                "objective": {
                    "task": "Layer intelligent delegation and self-reflection over the current task system using the AGNO framework.",
                    "constraints": [
                        "Use the model 'deepseek-coder:instruct' with reasoning=True for all reasoning agents such as the Reflector and Planner.",
                        "Use the model 'meta-llama/llama-4-scout-17b-16e-instruct' for all other agents (Executor, Validator).",
                        "Set each agent’s model with id=<model_id> and api_key=GROQ_API_KEY explicitly in the code.",
                        "Load the GROQ_API_KEY from a .env file using dotenv to avoid hardcoding secrets in the codebase.",
                        "Each agent must be in its own file under /agents/, with clear docstrings explaining its role.",
                        "Each agent must log its input and output in a readable format for traceability and debugging.",
                        "Implement a Team class under /teams/ that coordinates Planner → Executor → Validator and runs post-analysis via ReflectorAgent.",
                        "Add a unit test for each agent in /tests/ using pytest, and a full pipeline test to validate the system end-to-end.",
                        "Do not remove or break original logic — only evolve it by layering the AGNO architecture."
                    ],
                    "architectural_expectations": [
                        "Agents must be orchestrated in a pipeline: TaskPlannerAgent → TaskExecutorAgent → TaskValidatorAgent → ReflectorAgent.",
                        "Use reasoning=True where necessary.",
                        "Ensure clean separation of concerns.",
                        "ReflectorAgent must analyze past task outputs and propose improvements via printed logs or return values.", 
                        "Provide a main.py to run the full team pipeline."
                    ]
                },
                "project_name": "agno_task_system",
            }            
        ]
    }
    
    scenario_path = scenario_dir / "agno_task_system.json"
    with open(scenario_path, 'w', encoding='utf-8') as f:
        json.dump(scenario_data, f, indent=2, ensure_ascii=False)
    
    return scenario_path

def print_file_tree(project_path: Path):
    """Print the generated file structure"""
    canvas.info("\n📁 Generated Files:")
    for file_path in sorted(project_path.rglob("*.py")):
        relative = file_path.relative_to(project_path)
        canvas.info(f"   {relative}")

def test_simple_agno():
    """Run simple generation and output results for evaluation"""
    
    canvas.info("🚀 Simple AGNO Generation Test")
    canvas.info("=" * 60)
    
    budget_manager = BudgetManagerAgent(session_budget=None)
    
    try:
        # Create and run scenario
        scenario_path = create_simple_scenario()
        
        canvas.info("🎯 Generating AGNO application...")
        success = run_scenario(
            str(scenario_path), 
            budget_manager=budget_manager, 
            debug=False  # Less verbose
        )
        
        project_path = Path("./output/agno_task_system")
        
        if success and project_path.exists():
            canvas.success("✅ Generation completed!")
            print_file_tree(project_path)
            
            canvas.info("\n📋 Next Steps:")
            canvas.info("1. Review the generated files in: ./output/agno_task_system")
            canvas.info("2. Pass the files to an LLM for quality evaluation")
            canvas.info("3. Check for:")
            canvas.info("   - Proper AGNO patterns (Agent, Team, etc.)")
            canvas.info("   - Multi-agent coordination")
            canvas.info("   - Complete implementation (no TODOs)")
            canvas.info("   - Working functionality")
            
            return True
        else:
            canvas.error("❌ Generation failed")
            return False
            
    except Exception as e:
        canvas.error(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    success = test_simple_agno()
    exit(0 if success else 1)