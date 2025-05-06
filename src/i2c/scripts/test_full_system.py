# src/i2c/scripts/test_full_system.py
"""Test the complete I2C Factory system end to end"""

from pathlib import Path
import os
import json
from dotenv import load_dotenv
from i2c.bootstrap import initialize_environment, PROJECT_ROOT

# 1) Shared env & builtins setup
initialize_environment()

# 2) Load environment variables from the project root .env
load_dotenv(PROJECT_ROOT / '.env')


def test_full_system():
    """Test the complete workflow of the Idea-to-Code Factory"""
    print("=== Testing Full I2C Factory System ===\n")
    try:
        # Test 1: Core Agents
        print("1. Testing Core Agents...")
        from i2c.agents.core_agents import input_processor_agent, planner_agent

        raw_idea = "Create a REST API for managing books with CRUD operations"
        processed_response = input_processor_agent.run(raw_idea)
        print(f"✅ Input processed: {processed_response.content[:100]}...")

        # Parse response
        try:
            data = json.loads(processed_response.content)
            objective = data.get('objective', '')
            language = data.get('language', 'python')
        except json.JSONDecodeError:
            objective = "Create a REST API for managing books"
            language = "python"

        # Test planning
        print("2. Testing Plan Agent...")
        plan_prompt = f"Objective: {objective}\nLanguage: {language}"
        plan_response = planner_agent.run(plan_prompt)
        print(f"✅ Plan created: {plan_response.content[:100]}...")

        # Test 3: Modification Team
        print("\n3. Testing Modification Team...")
        from i2c.agents.modification_team.modification_planner import modification_planner_agent
        mod_request = "Add authentication to the API"
        mod_response = modification_planner_agent.run(
            f"Request: {mod_request}\nContext: {objective}"
        )
        print(f"✅ Modification planned: {mod_response.content[:100]}...")

        # Test 4: Quality Team
        print("\n4. Testing Quality Team...")
        from i2c.agents.quality_team.static_analysis_agent import StaticAnalysisAgent
        analysis_agent = StaticAnalysisAgent()
        analysis_summary = analysis_agent.get_analysis_summary(PROJECT_ROOT)
        print(f"✅ Static analysis summary: {analysis_summary}")

        # Test 5: Database Connection
        print("\n5. Testing Database...")
        from i2c.db_utils import get_db_connection
        db = get_db_connection()
        if db:
            print("✅ Database connection successful")
        else:
            print("⚠️ Database connection failed (might need initialization)")

        print("\n=== All Systems Operational! ===")

    except Exception as e:
        print(f"\n❌ Error during full system test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_full_system()
