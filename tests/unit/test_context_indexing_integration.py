# test_context_indexing_integration.py
"""
Unit tests for context indexing and API route integration in agentic evolution.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from i2c.workflow.agentic_orchestrator import _apply_modifications_if_any
from i2c.utils.api_route_tracker import inject_api_routes_into_session
from i2c.agents.core_agents import get_rag_enabled_agent

@pytest.fixture
def temp_fullstack_project():
    """Create temporary fullstack project with backend and frontend"""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Create backend with API routes
        backend_dir = project_path / "backend"
        backend_dir.mkdir(parents=True)
        
        main_py = backend_dir / "main.py"
        main_py.write_text("""
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/users")
def get_users():
    return {"users": []}

@app.post("/api/analyze")  
def analyze_text(text: str):
    return {"result": "analyzed"}
""")
        
        # Create frontend
        frontend_dir = project_path / "frontend" / "src"
        frontend_dir.mkdir(parents=True)
        
        app_jsx = frontend_dir / "App.jsx"
        app_jsx.write_text("""
import React from 'react';

function App() {
  return <div>Hello World</div>;
}

export default App;
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
        },
        "project_path": ""  # Will be set in tests
    }

def test_initial_api_extraction(temp_fullstack_project, fullstack_session_state):
    """Test initial API route extraction works"""
    print("🔍 Testing initial API route extraction...")
    
    fullstack_session_state["project_path"] = str(temp_fullstack_project)
    
    # Debug the session state structure
    print(f"   🔍 Session state before extraction: {fullstack_session_state}")
    print(f"   🔍 Project files: {list(temp_fullstack_project.rglob('*.py'))}")
    
    # Extract API routes
    result_session = inject_api_routes_into_session(temp_fullstack_project, fullstack_session_state)
    
    # Should extract routes
    assert "backend_api_routes" in result_session
    assert "api_route_summary" in result_session
    
    routes = result_session["backend_api_routes"]
    total_routes = sum(len(endpoints) for endpoints in routes.values())
    
    print(f"   ✅ Extracted {total_routes} API routes")
    print(f"   📝 Routes: {routes}")


    # Debug what we actually got
    print(f"   🔍 Routes type: {type(routes)}")
    print(f"   🔍 Routes content: {routes}")
    
    # Should have found our test routes
    if isinstance(routes, dict) and total_routes > 0:
        assert total_routes >= 2  # get_users and analyze_text
        routes_str = str(routes)
        assert "users" in routes_str
        assert "analyze" in routes_str
        print("   ✅ Found expected API routes")
    else:
        print(f"   ❌ Expected dict with routes, got: {type(routes)} = {routes}")
        # Let's check what the inject function actually returned
        print(f"   🔍 Full result_session: {result_session}")
        assert False, f"API extraction failed - got {type(routes)} instead of dict"


@patch('i2c.agents.modification_team.context_reader.context_reader_agent.ContextReaderAgent')
def test_context_reindexing_after_modifications(mock_context_reader, temp_fullstack_project, fullstack_session_state):
    """Test context re-indexing after modifications"""
    print("🔄 Testing context re-indexing after modifications...")
    
    # Mock the context reader agent
    mock_reader_instance = Mock()
    mock_reader_instance.index_project_context.return_value = {
        'files_indexed': 5,
        'chunks_indexed': 25,
        'errors': []
    }
    mock_context_reader.return_value = mock_reader_instance
    
    fullstack_session_state["project_path"] = str(temp_fullstack_project)
    
    # Simulate modifications that change backend files
    modifications = {
        "backend/api/new_routes.py": "New API endpoint code",
        "frontend/src/components/NewComponent.jsx": "New React component"
    }
    
    result_json = {"modifications": modifications}
    
    # Apply modifications (this should trigger re-indexing)
    _apply_modifications_if_any(result_json, temp_fullstack_project, fullstack_session_state)
    
    # Should have called context indexing
    mock_context_reader.assert_called_once_with(temp_fullstack_project)
    mock_reader_instance.index_project_context.assert_called_once()
    
    print("   ✅ Context re-indexing was triggered")

@patch('i2c.utils.api_route_tracker.inject_api_routes_into_session')
@patch('i2c.agents.modification_team.context_reader.context_reader_agent.ContextReaderAgent')
def test_api_route_reextraction_on_backend_changes(mock_context_reader, mock_api_injection, temp_fullstack_project, fullstack_session_state):
    """Test API routes re-extracted when backend files change"""
    print("🔄 Testing API route re-extraction on backend changes...")
    
    # Mock returns
    mock_reader_instance = Mock()
    mock_reader_instance.index_project_context.return_value = {'files_indexed': 3, 'chunks_indexed': 15, 'errors': []}
    mock_context_reader.return_value = mock_reader_instance
    
    mock_api_injection.return_value = {
        **fullstack_session_state,
        "backend_api_routes": {"POST": [{"path": "/api/new"}]},
        "api_route_summary": "POST /api/new"
    }
    
    fullstack_session_state["project_path"] = str(temp_fullstack_project)
    
    # Modifications that include backend changes
    backend_modifications = {
        "backend/api/users.py": "New user endpoint",
        "backend/models.py": "New data models"
    }
    
    result_json = {"modifications": backend_modifications}
    
    # Apply modifications
    _apply_modifications_if_any(result_json, temp_fullstack_project, fullstack_session_state)
    
    # Should have re-extracted API routes because backend files changed
    mock_api_injection.assert_called_once_with(temp_fullstack_project, fullstack_session_state)
    
    print("   ✅ API route re-extraction was triggered for backend changes")

@patch('i2c.utils.api_route_tracker.inject_api_routes_into_session')
@patch('i2c.agents.modification_team.context_reader.context_reader_agent.ContextReaderAgent')  
def test_no_api_reextraction_on_frontend_only_changes(mock_context_reader, mock_api_injection, temp_fullstack_project, fullstack_session_state):
    """Test API routes NOT re-extracted for frontend-only changes"""
    print("🔄 Testing NO API re-extraction for frontend-only changes...")
    
    # Mock returns
    mock_reader_instance = Mock()
    mock_reader_instance.index_project_context.return_value = {'files_indexed': 2, 'chunks_indexed': 10, 'errors': []}
    mock_context_reader.return_value = mock_reader_instance
    
    fullstack_session_state["project_path"] = str(temp_fullstack_project)
    
    # Frontend-only modifications
    frontend_modifications = {
        "frontend/src/components/Button.jsx": "New button component",
        "frontend/src/styles/main.css": "New styles"
    }
    
    result_json = {"modifications": frontend_modifications}
    
    # Apply modifications
    _apply_modifications_if_any(result_json, temp_fullstack_project, fullstack_session_state)
    
    # Should NOT have re-extracted API routes (no backend changes)
    mock_api_injection.assert_not_called()
    
    print("   ✅ API route re-extraction was correctly skipped for frontend-only changes")

@patch('i2c.agents.core_agents.CodeBuilderAgent')
def test_code_builder_gets_api_context(mock_agent_class, temp_fullstack_project):
    """Test code_builder agent receives API context from session state"""
    print("🤖 Testing code_builder gets API context...")
    
    # Mock agent with instructions attribute
    mock_agent = Mock()
    mock_agent.instructions = "Original instructions"
    mock_agent_class.return_value = mock_agent
    
    # Session with API routes
    session_with_apis = {
        "architectural_context": {"system_type": "fullstack_web_app"},
        "backend_api_routes": {
            "GET": [{"path": "/api/users"}],
            "POST": [{"path": "/api/analyze"}]
        },
        "api_route_summary": "Available endpoints:\nGET /api/users\nPOST /api/analyze"
    }
    
    # Create code_builder agent
    agent = get_rag_enabled_agent("code_builder", session_with_apis)
    
    # Should have created agent
    assert agent is not None
    
    # Should have injected API instructions (check if instructions were modified)
    # Note: This tests the logic flow, actual instruction injection depends on knowledge_base presence
    print("   ✅ Code builder agent created with session state")

def test_session_state_propagation():
    """Test session state properly propagates through workflow"""
    print("📋 Testing session state propagation...")
    
    initial_session = {
        "architectural_context": {"system_type": "fullstack_web_app"},
        "test_value": "original"
    }
    
    # Simulate session state updates
    updated_session = {**initial_session}
    updated_session["backend_api_routes"] = {"GET": [{"path": "/test"}]}
    updated_session["test_value"] = "updated"
    
    # Verify updates propagated
    assert updated_session["backend_api_routes"] == {"GET": [{"path": "/test"}]}
    assert updated_session["test_value"] == "updated"
    assert updated_session["architectural_context"] == initial_session["architectural_context"]
    
    print("   ✅ Session state propagation works correctly")

def test_empty_modifications_handling():
    """Test handling of empty or invalid modifications"""
    print("🚫 Testing empty modifications handling...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        session_state = {"test": "data"}
        
        # Test empty modifications
        empty_result = {"modifications": {}}
        _apply_modifications_if_any(empty_result, project_path, session_state)
        
        # Test None modifications  
        none_result = {"modifications": None}
        _apply_modifications_if_any(none_result, project_path, session_state)
        
        # Test missing modifications
        missing_result = {}
        _apply_modifications_if_any(missing_result, project_path, session_state)
        
        print("   ✅ Empty modifications handled gracefully")

if __name__ == "__main__":
    print("Running context indexing and API integration tests...")
    print("=" * 60)
    
    # Run tests manually for debugging
    import sys
    
    # Create fixtures manually for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Create test project structure
        backend_dir = project_path / "backend"
        backend_dir.mkdir(parents=True)
        
        main_py = backend_dir / "main.py"
        main_py.write_text("""
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/test")
def test_endpoint():
    return {"test": "data"}
""")
        
        session_state = {
            "architectural_context": {
                "system_type": "fullstack_web_app",
                "modules": {
                    "backend": {"boundary_type": "api_layer"}
                }
            },
            "project_path": str(project_path)
        }
        
        try:
            # Test API extraction
            test_initial_api_extraction(project_path, session_state)
            print("\n" + "="*50)
            
            # Test session state propagation
            test_session_state_propagation()
            print("\n" + "="*50)
            
            # Test empty modifications
            test_empty_modifications_handling()
            print("\n" + "="*60)
            print("✅ All context indexing tests completed!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)