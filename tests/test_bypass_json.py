# test_bypass_json.py
from i2c.bootstrap import initialize_environment
initialize_environment()
from i2c.agents.core_agents import get_rag_enabled_agent

def test_direct_agent_response():
    agent = get_rag_enabled_agent("code_builder", session_state=None)
    
    # Simple request
    response = agent.run("Create a Python class called TaskPlannerAgent with one method")
    
    # Print raw response (don't parse as JSON)
    print("=== RAW RESPONSE ===")
    print(response)
    print("=== END RAW ===")
    
    # Check if it contains actual code
    response_str = str(response)
    if "class TaskPlannerAgent" in response_str and "def " in response_str:
        print("✅ Agent generated real code")
        return True
    else:
        print("❌ Agent didn't generate code")
        return False

if __name__ == "__main__":
    test_direct_agent_response()