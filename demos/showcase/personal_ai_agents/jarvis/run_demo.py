#!/usr/bin/env python3
"""
Jarvis Emotional Intelligence Advisor Demo
"""
from i2c.bootstrap import initialize_environment
initialize_environment()
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

def run_jarvis_demo():
    """Run the Jarvis emotional intelligence demo"""
    
    print("🤖 Starting Jarvis - Emotional Intelligence Advisor Demo")
    print("=" * 60)
    
    try:
        from i2c.workflow.scenario_processor import run_scenario
        from i2c.agents.budget_manager import BudgetManagerAgent
        
        # Setup
        scenario_path = Path(__file__).parent / "scenario.json"
        budget_manager = BudgetManagerAgent(session_budget=None)
        
        print("🚀 Generating Jarvis emotional intelligence system...")
        success = run_scenario(str(scenario_path), budget_manager=budget_manager)
        
        if success:
            print("✅ Jarvis demo completed successfully!")
            print("\n📁 Check the generated code in: ./output/jarvis_emotional_advisor/")
            print("\n🎯 Next: Review the AGNO agents that work together to prevent conflicts")
        else:
            print("❌ Demo failed - check logs for details")
            
    except Exception as e:
        print(f"❌ Error running demo: {e}")
        return False
    
    return success

if __name__ == "__main__":
    run_jarvis_demo()
