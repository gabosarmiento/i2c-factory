# demo/scripts/demo_runner.py

import time
import json
from pathlib import Path

from i2c.bootstrap import initialize_environment
initialize_environment()

from i2c.workflow.session import run_session
from i2c.cli.controller import canvas
from i2c.workflow.orchestrator import route_and_execute
from i2c.agents.budget_manager import BudgetManagerAgent

class DemoRunner:
    def __init__(self, scenario_file: str):
        self.scenarios = self._load_scenarios(scenario_file)
        self.budget_manager = BudgetManagerAgent(session_budget=10.0)  # $10 for demo
        self.current_project_path = None
        self.current_structured_goal = None
    
    def _load_scenarios(self, file_path: str) -> list:
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def run_demo(self):
        canvas.info("🚀 Starting I2C Factory Demo")
        
        for idx, scenario in enumerate(self.scenarios):
            self._execute_scenario(idx, scenario)
            time.sleep(2)  # Pause between scenarios for clarity
    
    def _execute_scenario(self, idx: int, scenario: dict):
        canvas.info(f"\n{'='*50}")
        canvas.info(f"Scenario {idx+1}: {scenario['name']}")
        canvas.info(f"{'='*50}")
        
        if scenario['type'] == 'initial_generation':
            self._run_initial_generation(scenario)
        elif scenario['type'] == 'modification':
            self._run_modification(scenario)
        elif scenario['type'] == 'narration':
            self._show_narration(scenario)
    
    def _run_initial_generation(self, scenario: dict):
        # Use existing generation workflow
        from i2c.agents.core_agents import input_processor_agent
        
        # Process the idea
        raw_idea = scenario['prompt']
        response = input_processor_agent.run(raw_idea)
        structured_goal = json.loads(response.content)
        
        # Set up project
        project_name = "crypto-dashboard"
        self.current_project_path = Path(__file__).parent.parent / "output" / project_name
        self.current_project_path.mkdir(parents=True, exist_ok=True)
        self.current_structured_goal = structured_goal
        
        # Execute generation
        success = route_and_execute(
            action_type='generate',
            action_detail=structured_goal,
            current_project_path=self.current_project_path,
            current_structured_goal=structured_goal
        )
        
        if success:
            canvas.success(f"✅ Generated: {scenario['name']}")
        else:
            canvas.error(f"❌ Generation failed: {scenario['name']}")
    
    def _run_modification(self, scenario: dict):
        # Use existing modification workflow
        success = route_and_execute(
            action_type='modify',
            action_detail=f'f {scenario["prompt"]}',
            current_project_path=self.current_project_path,
            current_structured_goal=self.current_structured_goal
        )
        
        if success:
            canvas.success(f"✅ Modified: {scenario['name']}")
        else:
            canvas.error(f"❌ Modification failed: {scenario['name']}")
    
    def _show_narration(self, scenario: dict):
        canvas.info(f"\n📢 {scenario['message']}")
        time.sleep(scenario.get('pause', 2))

if __name__ == "__main__":
    runner = DemoRunner("scenarios/crypto_dashboard.json")
    runner.run_demo()