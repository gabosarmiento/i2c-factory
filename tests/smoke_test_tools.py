from i2c.bootstrap import initialize_environment
initialize_environment()

import os
from dotenv import load_dotenv
load_dotenv()

print("=== Testing Groq-Compatible Tools ===")

# Test 1: Manual tool calling (bypassing Agno's tool system)
print("\n1. Testing manual tool calls...")

try:
    from i2c.agents.modification_team.groq_compatible_tools import call_tool_manually
    
    # Test vector search manually
    result = call_tool_manually("vector_retrieve", query="Agent usage", source="knowledge", limit=2)
    print(f"Manual vector search result: {result[:200]}...")
    
    # Test project context manually  
    result = call_tool_manually("get_project_context", project_path=".", focus="agent")
    print(f"Manual project context result: {result[:200]}...")
    
    # Test GitHub fetch manually
    result = call_tool_manually("github_fetch", repo_path="agno-agi/agno", file_path="README.md")
    print(f"Manual GitHub fetch result: {result[:200]}...")
    
except Exception as e:
    print(f"Error in manual tool testing: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Agent with Groq-compatible tools
print("\n2. Testing Agent with Groq-compatible tools...")

try:
    from agno.agent import Agent
    from i2c.llm_providers import llm_middle
    from i2c.agents.modification_team.groq_compatible_tools import create_groq_compatible_tools
    
    # Create Groq-compatible tools
    tools = create_groq_compatible_tools()
    print(f"Created {len(tools)} Groq-compatible tools")
    
    # Create agent with tools
    agent = Agent(
        name="GroqCompatibleAgent",
        model=llm_middle,
        tools=tools,
        instructions="""
You are a helpful assistant with access to retrieval tools.
Use the tools to answer questions accurately.
Always return the information you find from the tools.
"""
    )
    
    # Test vector search through agent
    print("\n3. Testing vector search through Groq-compatible agent...")
    try:
        response = agent.run("Search for 'Agent' in the knowledge base using vector_retrieve with limit 1")
        print(f"Agent vector response: {response.content if hasattr(response, 'content') else str(response)}")
    except Exception as e:
        print(f"Agent vector test failed: {e}")
        import traceback
        traceback.print_exc()

except Exception as e:
    print(f"Error setting up Groq-compatible agent: {e}")
    import traceback  
    traceback.print_exc()

# Test 3: Alternative approach using OpenAI-style manual handling
print("\n4. Testing OpenAI-style manual tool handling...")

try:
    from agno.agent import Agent
    from i2c.llm_providers import llm_middle
    from i2c.agents.modification_team.groq_compatible_tools import TOOL_REGISTRY
    import json
    
    # Create agent without tools but with instructions to use JSON
    simple_agent = Agent(
        name="SimpleToolAgent",
        model=llm_middle,
        instructions="""
You are a helpful assistant. When you need to use tools, respond with JSON in this format:
{
  "tool_call": {
    "name": "tool_name",
    "parameters": {"param1": "value1", "param2": "value2"}
  }
}

Available tools:
- vector_retrieve: Search vector database (params: query, source, limit)
- github_fetch: Fetch GitHub files (params: repo_path, file_path)  
- get_project_context: Get project info (params: project_path, focus)
"""
    )
    
    # Ask the agent to make a tool call
    response = simple_agent.run("I need to search for 'Agent usage' in the knowledge base. Use vector_retrieve.")
    response_content = response.content if hasattr(response, 'content') else str(response)
    print(f"Simple agent response: {response_content}")
    
    # Try to parse and execute the tool call
    try:
        # Look for JSON in the response
        import re
        json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
        if json_match:
            tool_request = json.loads(json_match.group())
            print(f"Parsed tool request: {tool_request}")
            
            if "tool_call" in tool_request:
                tool_name = tool_request["tool_call"]["name"]
                params = tool_request["tool_call"]["parameters"]
                
                if tool_name in TOOL_REGISTRY:
                    result = call_tool_manually(tool_name, **params)
                    print(f"Tool execution result: {result[:200]}...")
                else:
                    print(f"Unknown tool: {tool_name}")
            else:
                print("No tool_call found in response")
        else:
            print("No JSON found in agent response")
    except Exception as e:
        print(f"Error parsing/executing tool call: {e}")

except Exception as e:
    print(f"Error in OpenAI-style test: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test Complete ===")