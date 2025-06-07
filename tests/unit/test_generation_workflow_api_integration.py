# test_generation_workflow_api_integration.py
"""
Unit test to verify API route extraction and architectural rules during generation.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from i2c.workflow.generation_workflow import GenerationWorkflow

def test_api_route_extraction_during_generation():
    """Test that API routes are extracted from backend code during generation"""
    print("🔄 Testing API route extraction during generation...")
    
    # Mock session state with architectural context
    session_state = {
        "system_type": "fullstack_web_app",
        "architectural_context": {
            "modules": {
                "backend": {
                    "boundary_type": "api_layer",
                    "languages": ["python"],
                    "responsibilities": ["API endpoints"]
                },
                "frontend": {
                    "boundary_type": "ui_layer",
                    "languages": ["javascript"],
                    "responsibilities": ["UI components"]
                }
            }
        },
        "objective": "Create a test API system",
        "language": "Python"
    }
    
    # Create workflow
    workflow = GenerationWorkflow(session_state=session_state)
    
    # Mock generated backend code with API routes
    mock_backend_code = """
from fastapi import APIRouter

router = APIRouter()

@router.post("/test-endpoint")
async def test_endpoint():
    return {"message": "test"}

@router.get("/health")
async def health_check():
    return {"status": "healthy"}
"""
    
    mock_generated_code = {
        "backend/api/endpoints.py": mock_backend_code,
        "backend/main.py": "from api.endpoints import router\napp.include_router(router)"
    }
    
    backend_files = ["backend/api/endpoints.py", "backend/main.py"]
    
    # Test the API route extraction method
    workflow._extract_api_routes_from_memory(mock_generated_code, backend_files)
    
    # Verify routes were extracted
    assert "backend_api_routes" in workflow.session_state, "Should extract API routes"
    
    routes = workflow.session_state["backend_api_routes"]
    assert len(routes) > 0, "Should find routes in generated code"
    
    # Check for specific routes
    found_endpoints = []
    for file_routes in routes.values():
        for route in file_routes:
            found_endpoints.append(f"{route['method']} {route['path']}")
    
    assert "POST /test-endpoint" in found_endpoints, "Should find test endpoint"
    assert "GET /health" in found_endpoints, "Should find health endpoint"
    
    print(f"   ✅ Extracted {len(found_endpoints)} API routes successfully")

def test_architectural_rules_in_generation_prompt():
    """Test that architectural rules are included in generation prompts"""
    print("🔄 Testing architectural rules in generation prompts...")
    
    # Mock session state with API routes and architectural context
    session_state = {
        "system_type": "fullstack_web_app",
        "architectural_context": {
            "modules": {
                "backend": {
                    "boundary_type": "api_layer",
                    "languages": ["python"],
                    "responsibilities": ["API endpoints", "business logic"]
                }
            }
        },
        "backend_api_routes": {
            "backend/api/endpoints.py": [
                {"method": "POST", "path": "/existing-endpoint", "function": "test_func"},
                {"method": "GET", "path": "/health", "function": "health_check"}
            ]
        },
        "objective": "Test system",
        "language": "Python"
    }
    
    workflow = GenerationWorkflow(session_state=session_state)
    
    # Mock the code builder agent
    mock_code_builder = Mock()
    mock_response = Mock()
    mock_response.content = "# Generated code content"
    mock_code_builder.run.return_value = mock_response
    
    with patch('i2c.agents.core_agents.get_rag_enabled_agent') as mock_get_agent:
        mock_get_agent.return_value = mock_code_builder
        
        # Generate a backend file
        result = workflow._generate_single_file(
            file_path="backend/new_endpoints.py",
            objective="Create new API endpoints",
            language="Python",
            constraints_text="",
            generated_code={},
            enhance_with_api=False
        )
        
        # Verify the prompt included architectural rules
        call_args = mock_code_builder.run.call_args[0][0]
        
        assert "ARCHITECTURAL RULES FOR FULLSTACK WEB APP" in call_args, "Should include architectural rules"
        assert "EXISTING API ENDPOINTS - DO NOT DUPLICATE" in call_args, "Should warn about existing endpoints"
        assert "POST /existing-endpoint" in call_args, "Should list existing endpoints"
        assert "GET /health" in call_args, "Should list all existing endpoints"
        assert "Do not create duplicate endpoints" in call_args, "Should include duplication warning"
        
        print("   ✅ Architectural rules properly included in generation prompt")

def test_frontend_generation_with_api_context():
    """Test that frontend files get API context for integration"""
    print("🔄 Testing frontend generation with API context...")
    
    session_state = {
        "system_type": "fullstack_web_app",
        "architectural_context": {
            "modules": {
                "frontend": {
                    "boundary_type": "ui_layer",
                    "languages": ["javascript"],
                    "responsibilities": ["UI components"]
                }
            }
        },
        "backend_api_routes": {
            "backend/api/endpoints.py": [
                {"method": "POST", "path": "/analyze", "function": "analyze_data"},
                {"method": "GET", "path": "/users", "function": "get_users"}
            ]
        },
        "objective": "Create frontend components",
        "language": "JavaScript"
    }
    
    workflow = GenerationWorkflow(session_state=session_state)
    
    # Mock the code builder
    mock_code_builder = Mock()
    mock_response = Mock()
    mock_response.content = "// Generated React component"
    mock_code_builder.run.return_value = mock_response
    
    with patch('i2c.agents.core_agents.get_rag_enabled_agent') as mock_get_agent:
        mock_get_agent.return_value = mock_code_builder
        
        # Generate a frontend file with API enhancement
        result = workflow._generate_single_file(
            file_path="frontend/src/components/DataAnalyzer.jsx",
            objective="Create data analyzer component",
            language="JavaScript", 
            constraints_text="",
            generated_code={},
            enhance_with_api=True
        )
        
        # Check the prompt included API integration context
        call_args = mock_code_builder.run.call_args[0][0]
        
        assert "AVAILABLE API ENDPOINTS FOR INTEGRATION" in call_args, "Should include API integration context"
        assert "POST /analyze" in call_args, "Should list available endpoints"
        assert "GET /users" in call_args, "Should list all available endpoints"
        assert "integrate these existing API endpoints" in call_args, "Should encourage integration"
        
        print("   ✅ Frontend generation includes API integration context")

def test_duplicate_route_detection():
    """Test that duplicate routes are properly identified and warned about"""
    print("🔄 Testing duplicate route detection...")
    
    session_state = {
        "system_type": "fullstack_web_app",
        "architectural_context": {"modules": {}},
        "backend_api_routes": {
            "backend/main.py": [
                {"method": "POST", "path": "/analyze", "function": "analyze_main"},
                {"method": "GET", "path": "/health", "function": "health_main"}
            ],
            "backend/api/endpoints.py": [
                {"method": "POST", "path": "/analyze", "function": "analyze_router"},  # Duplicate!
                {"method": "GET", "path": "/health", "function": "health_router"},    # Duplicate!
                {"method": "GET", "path": "/users", "function": "get_users"}         # Unique
            ]
        }
    }
    
    workflow = GenerationWorkflow(session_state=session_state)
    
    mock_code_builder = Mock()
    mock_response = Mock()
    mock_response.content = "# Generated code"
    mock_code_builder.run.return_value = mock_response
    
    with patch('i2c.agents.core_agents.get_rag_enabled_agent') as mock_get_agent:
        mock_get_agent.return_value = mock_code_builder
        
        # Generate a file that should get duplication warnings
        workflow._generate_single_file(
            file_path="backend/new_file.py",
            objective="Create new endpoints",
            language="Python",
            constraints_text="",
            generated_code={},
            enhance_with_api=False
        )
        
        call_args = mock_code_builder.run.call_args[0][0]
        
        # Should detect and warn about duplicates
        assert "POST /analyze" in call_args, "Should list duplicate endpoint"
        assert "GET /health" in call_args, "Should list duplicate endpoint"
        assert "GET /users" in call_args, "Should list unique endpoint"
        
        # Should have duplication warning
        assert "DO NOT DUPLICATE" in call_args, "Should warn about duplicates"
        
        print("   ✅ Duplicate route detection working correctly")

def test_code_generation_phase_integration():
    """Test the full code generation phase with API extraction"""
    print("🔄 Testing full code generation phase...")
    
    session_state = {
        "system_type": "fullstack_web_app",
        "architectural_context": {
            "modules": {
                "backend": {"boundary_type": "api_layer", "languages": ["python"]},
                "frontend": {"boundary_type": "ui_layer", "languages": ["javascript"]}
            }
        },
        "file_plan": [
            "backend/main.py",
            "backend/api/endpoints.py", 
            "frontend/src/App.jsx"
        ],
        "objective": "Create a test application",
        "language": "Python"
    }
    
    workflow = GenerationWorkflow(session_state=session_state)
    
    # Mock the code builder to return realistic API code
    mock_code_builder = Mock()
    
    def mock_code_response(prompt):
        if "backend/api/endpoints.py" in prompt:
            mock_response = Mock()
            mock_response.content = """
from fastapi import APIRouter

router = APIRouter()

@router.post("/test")
async def test_endpoint():
    return {"test": "data"}
"""
            return mock_response
        elif "frontend/src/App.jsx" in prompt:
            mock_response = Mock()
            # Should reference API endpoints if enhancement worked
            content = "// React App component\n"
            if "POST /test" in prompt:
                content += "// Uses API: POST /test\n"
            mock_response.content = content
            return mock_response
        else:
            mock_response = Mock()
            mock_response.content = "# Generated code"
            return mock_response
    
    mock_code_builder.run.side_effect = mock_code_response
    
    with patch('i2c.agents.core_agents.get_rag_enabled_agent') as mock_get_agent:
        mock_get_agent.return_value = mock_code_builder
        
        # Run the code generation phase
        responses = list(workflow.code_generation_phase())
        
        # Verify the workflow completed
        assert len(responses) > 0, "Should generate responses"
        
        # Verify API routes were extracted and stored
        assert "backend_api_routes" in workflow.session_state, "Should extract API routes during generation"
        
        # Verify generated code was stored
        assert "code_map" in workflow.session_state, "Should store generated code"
        
        code_map = workflow.session_state["code_map"]
        assert "backend/api/endpoints.py" in code_map, "Should generate backend files"
        assert "frontend/src/App.jsx" in code_map, "Should generate frontend files"
        
        print("   ✅ Full code generation phase integration working")

if __name__ == "__main__":
    print("Testing Generation Workflow API Integration...")
    print("="*60)
    
    try:
        test_api_route_extraction_during_generation()
        test_architectural_rules_in_generation_prompt()
        test_frontend_generation_with_api_context()
        test_duplicate_route_detection()
        test_code_generation_phase_integration()
        
        print("\n✅ All generation workflow API integration tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()