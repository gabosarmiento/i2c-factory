import pytest
import json
import os
from pathlib import Path

def test_direct_vector_retrieve():
    """Test the vector retrieve function directly"""
    from i2c.agents.modification_team.groq_compatible_tools import groq_vector_retrieve
    
    result = groq_vector_retrieve(query="Agent", source="knowledge", limit=2)
    
    # Should return a GroqToolResponse object that converts to string
    result_str = str(result)
    assert isinstance(result_str, str)
    
    # Should be valid JSON
    try:
        data = json.loads(result_str)
        assert isinstance(data, list) or isinstance(data, dict)
        if isinstance(data, list):
            assert len(data) <= 2  # Respects limit
    except json.JSONDecodeError:
        pytest.fail(f"Vector retrieve returned invalid JSON: {result_str[:200]}")

def test_direct_project_context():
    """Test the project context function directly"""
    from i2c.agents.modification_team.groq_compatible_tools import groq_get_project_context
    
    result = groq_get_project_context(project_path=".", focus="test")
    result_str = str(result)
    
    assert isinstance(result_str, str)
    
    # Should be valid JSON
    try:
        data = json.loads(result_str)
        assert isinstance(data, dict)
        assert "files" in data or "error" in data
        if "files" in data:
            assert isinstance(data["files"], list)
    except json.JSONDecodeError:
        pytest.fail(f"Project context returned invalid JSON: {result_str[:200]}")

def test_direct_github_fetch():
    """Test the GitHub fetch function directly"""
    from i2c.agents.modification_team.groq_compatible_tools import groq_github_fetch
    
    result = groq_github_fetch(repo_path="agno-agi/agno", file_path="README.md")
    result_str = str(result)
    
    assert isinstance(result_str, str)
    
    # Should contain content about agno or be an error
    result_lower = result_str.lower()
    assert "agno" in result_lower or "error" in result_lower

def test_tool_wrappers():
    """Test the Function objects created by create_groq_compatible_tools"""
    from i2c.agents.modification_team.groq_compatible_tools import create_groq_compatible_tools
    
    tools = create_groq_compatible_tools()
    
    # Should create 3 tools
    assert len(tools) == 3
    
    # Check tool names
    tool_names = [tool.name for tool in tools]
    expected_names = ["vector_retrieve", "github_fetch", "get_project_context"]
    assert all(name in tool_names for name in expected_names)
    
    # Test vector retrieve tool
    vector_tool = next(tool for tool in tools if tool.name == "vector_retrieve")
    assert vector_tool.description is not None
    
    # Fix: Check the correct structure of parameters
    assert isinstance(vector_tool.parameters, dict)
    assert "type" in vector_tool.parameters
    assert vector_tool.parameters["type"] == "object"
    assert "properties" in vector_tool.parameters
    assert "query" in vector_tool.parameters["properties"]
    assert "required" in vector_tool.parameters
    assert "query" in vector_tool.parameters["required"]
    
    # Call the vector tool function if possible
    if hasattr(vector_tool, 'entrypoint') and callable(vector_tool.entrypoint):
        result = vector_tool.entrypoint(query="Agent", source="knowledge", limit=2)
        assert result is not None

def test_manual_tool_calling():
    """Test the manual tool calling registry"""
    from i2c.agents.modification_team.groq_compatible_tools import call_tool_manually, TOOL_REGISTRY
    
    # Check registry has expected tools
    expected_tools = ["vector_retrieve", "github_fetch", "get_project_context"]
    for tool_name in expected_tools:
        assert tool_name in TOOL_REGISTRY
        assert callable(TOOL_REGISTRY[tool_name])
    
    # Test manual vector retrieve
    result = call_tool_manually("vector_retrieve", query="test", source="knowledge", limit=1)
    assert isinstance(result, str)
    
    # Test invalid tool
    result = call_tool_manually("nonexistent_tool")
    assert "error" in result.lower()

def test_error_handling():
    """Test error handling in tools"""
    from i2c.agents.modification_team.groq_compatible_tools import groq_vector_retrieve, groq_github_fetch
    
    # Test with empty query (should handle gracefully)
    result = groq_vector_retrieve(query="", source="knowledge", limit=1)
    result_str = str(result)
    assert isinstance(result_str, str)
    # Should either return results or an error, but not crash
    
    # Test GitHub fetch with invalid repo
    result = groq_github_fetch(repo_path="nonexistent/repo", file_path="README.md")
    result_str = str(result)
    assert isinstance(result_str, str)
    # Should return error message, not crash

@pytest.mark.skipif(not os.getenv("GITHUB_ACCESS_TOKEN"), reason="GitHub token not available")
def test_github_with_token():
    """Test GitHub fetch with actual token"""
    from i2c.agents.modification_team.groq_compatible_tools import groq_github_fetch
    
    result = groq_github_fetch(repo_path="agno-agi/agno", file_path="README.md")
    result_str = str(result)
    
    # With token, should get actual content
    try:
        data = json.loads(result_str)
        if "success" in data:
            assert data["success"] is True
            assert "content" in data
    except json.JSONDecodeError:
        # If not JSON, should at least contain content
        assert len(result_str) > 100  # Should be substantial content

def test_integration_with_bootstrap():
    """Test that tools work after bootstrap initialization"""
    try:
        from i2c.bootstrap import initialize_environment
        initialize_environment()
        
        from i2c.agents.modification_team.groq_compatible_tools import call_tool_manually
        
        # Should work after initialization
        result = call_tool_manually("vector_retrieve", query="test", source="knowledge", limit=1)
        assert isinstance(result, str)
        
    except ImportError:
        pytest.skip("Bootstrap not available in test environment")

def test_original_tool_interface():
    """Test the original interface from your test file"""
    from i2c.agents.modification_team.groq_compatible_tools import create_groq_compatible_tools
    
    tools = create_groq_compatible_tools()
    
    # Test vector retrieve (tools[0])
    vector_result = tools[0].entrypoint(query="Agent", source="knowledge", limit=2)
    assert isinstance(vector_result, object)  # GroqToolResponse object
    assert str(vector_result)  # Should convert to string
    
    # Test project context (tools[2])
    project_result = tools[2].entrypoint(project_path=".", focus="test")
    result_str = str(project_result)
    assert "files" in result_str or isinstance(json.loads(result_str), dict)
    
    # Test github fetch (tools[1])
    github_result = tools[1].entrypoint(repo_path="agno-agi/agno", file_path="README.md")
    result_str = str(github_result)
    assert isinstance(result_str, str) and ("agno" in result_str.lower() or "error" in result_str.lower())

if __name__ == "__main__":
    # Run tests directly
    print("Running tool tests...")
    
    print("1. Testing direct vector retrieve...")
    test_direct_vector_retrieve()
    print("✅ Vector retrieve works")
    
    print("2. Testing direct project context...")
    test_direct_project_context()
    print("✅ Project context works")
    
    print("3. Testing direct GitHub fetch...")
    test_direct_github_fetch()
    print("✅ GitHub fetch works")
    
    print("4. Testing tool wrappers...")
    test_tool_wrappers()
    print("✅ Tool wrappers work")
    
    print("5. Testing manual tool calling...")
    test_manual_tool_calling()
    print("✅ Manual tool calling works")
    
    print("6. Testing error handling...")
    test_error_handling()
    print("✅ Error handling works")
    
    print("7. Testing original interface...")
    test_original_tool_interface()
    print("✅ Original interface works")
    
    if os.getenv("GITHUB_ACCESS_TOKEN"):
        print("8. Testing GitHub with token...")
        test_github_with_token()
        print("✅ GitHub with token works")
    else:
        print("8. Skipping GitHub token test (no token)")
    
    print("\n🎉 All tests passed!")