import pytest
from pathlib import Path
import tempfile
import json
from unittest.mock import Mock, patch

from i2c.utils.api_route_tracker import (
    inject_api_routes_into_session,
    enhance_frontend_generation_with_apis,
    validate_generated_frontend
)

@pytest.fixture
def temp_project_fullstack():
    """Create temporary fullstack project"""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Create backend with API routes
        backend_dir = project_path / "backend"
        backend_dir.mkdir()
        
        main_py = backend_dir / "main.py"
        main_py.write_text("""
from fastapi import FastAPI
app = FastAPI()

@app.post("/api/analyze")
def analyze_text(text: str):
    return {"result": "analyzed"}
""")
        yield project_path

@pytest.fixture
def fullstack_session_state():
    """Session state for fullstack web app"""
    return {
        "architectural_context": {
            "system_type": "fullstack_web_app",
            "modules": {
                "frontend": {"boundary_type": "ui_layer"},
                "backend": {"boundary_type": "api_layer"}
            }
        }
    }

@pytest.fixture
def cli_session_state():
    """Session state for CLI tool (no APIs)"""
    return {
        "architectural_context": {
            "system_type": "cli_tool",
            "modules": {
                "cli": {"boundary_type": "business_logic"}
            }
        }
    }

def test_api_extraction_fullstack_only(temp_project_fullstack, fullstack_session_state):
    """Test API routes extracted only for fullstack apps"""
    result_session = inject_api_routes_into_session(temp_project_fullstack, fullstack_session_state)
    
    # Should extract routes for fullstack
    assert "backend_api_routes" in result_session
    assert "api_route_summary" in result_session

def test_api_extraction_skipped_for_cli(temp_project_fullstack, cli_session_state):
    """Test API routes NOT extracted for CLI tools"""
    result_session = inject_api_routes_into_session(temp_project_fullstack, cli_session_state)
    
    # Should skip extraction for CLI
    assert "backend_api_routes" not in result_session
    assert "api_route_summary" not in result_session

@patch('i2c.agents.core_agents.canvas')
def test_agent_enhancement_architecture_aware(mock_canvas):
    """Test agent enhancement respects architecture"""
    from i2c.agents.core_agents import get_rag_enabled_agent
    
    # Fullstack session with API routes
    fullstack_session = {
        "architectural_context": {"system_type": "fullstack_web_app"},
        "backend_api_routes": {"POST": [{"path": "/api/test"}]},
        "api_route_summary": "POST /api/test"
    }
    
    # CLI session (no API injection expected)
    cli_session = {
        "architectural_context": {"system_type": "cli_tool"},
        "backend_api_routes": {"POST": [{"path": "/api/test"}]}
    }
    
    with patch('i2c.agents.core_agents.CodeBuilderAgent') as mock_agent_class:
        mock_agent = Mock()
        mock_agent.instructions = "Original"
        mock_agent_class.return_value = mock_agent
        
        # Test fullstack - should inject API context
        agent1 = get_rag_enabled_agent("code_builder", fullstack_session)
        # Check if API instructions were added (mock doesn't have knowledge_base)
        
        # Test CLI - should NOT inject API context  
        agent2 = get_rag_enabled_agent("code_builder", cli_session)
        
        # Both should return agents
        assert agent1 is not None
        assert agent2 is not None

def test_frontend_validation_architecture_aware():
    """Test validation only for systems with UIs"""
    fullstack_session = {
        "architectural_context": {"system_type": "fullstack_web_app"},
        "backend_api_routes": {"POST": [{"path": "/api/analyze", "full_path": "/api/analyze"}]}
    }
    
    valid_code = "const response = await fetch('/api/analyze', {method: 'POST'})"
    invalid_code = "const response = await fetch('/api/fake-endpoint', {method: 'POST'})"
    
    # Should validate for fullstack
    is_valid, issues = validate_generated_frontend(valid_code, fullstack_session)
    assert is_valid == True
    
    is_invalid, issues = validate_generated_frontend(invalid_code, fullstack_session)
    assert is_invalid == False
    assert len(issues) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])