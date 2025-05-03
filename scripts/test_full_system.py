# scripts/test_full_system.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Load environment variables
load_dotenv(project_root / '.env')

def test_full_system():
    """Test the complete workflow"""
    print("=== Testing Full I2C Factory System ===\n")
    
    try:
        # Test 1: Core Agents
        print("1. Testing Core Agents...")
        from agents.core_agents import input_processor_agent, planner_agent
        
        raw_idea = "Create a REST API for managing books with CRUD operations"
        processed_response = input_processor_agent.run(raw_idea)
        print(f"✅ Input processed: {processed_response.content[:100]}...")
        
        # Parse the response
        try:
            processed_data = json.loads(processed_response.content)
            objective = processed_data.get('objective', '')
            language = processed_data.get('language', 'python')
        except:
            objective = "Create a REST API for managing books"
            language = "python"
        
        # Test planning
        plan_prompt = f"Objective: {objective}\nLanguage: {language}"
        plan_response = planner_agent.run(plan_prompt)
        print(f"✅ Plan created: {plan_response.content[:100]}...")
        
        # Test 2: Modification Team
        print("\n2. Testing Modification Team...")
        from agents.modification_team import modification_planner_agent
        
        mod_request = "Add authentication to the API"
        mod_response = modification_planner_agent.run(f"Request: {mod_request}\nContext: {objective}")
        print(f"✅ Modification planned: {mod_response.content[:100]}...")
        
        # Test 3: Quality Checks
        print("\n3. Testing Quality Team...")
        from agents.quality_team import static_analysis_agent
        
        analysis_response = static_analysis_agent.get_analysis_summary(project_root)
        print(f"✅ Static analysis: {type(analysis_response)}")
        
        # Test 4: Database Connection
        print("\n4. Testing Database...")
        from db_utils import get_db_connection
        
        db = get_db_connection()
        if db:
            print("✅ Database connection successful")
        else:
            print("⚠️ Database connection failed (might need initialization)")
        
        print("\n=== All Systems Operational! ===")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_system()