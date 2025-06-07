# test_orchestration_prompt_construction.py
"""
Unit test to analyze the compound prompt construction in orchestration team.
This will help identify where conflicting instructions about API endpoints come from.
"""
import pytest
from unittest.mock import Mock, patch
from i2c.workflow.orchestration_team import build_orchestration_team, _retrieve_knowledge_context

def test_orchestration_prompt_with_api_routes_context():
    """Test how the orchestration team prompt is built when API routes exist in session state"""
    print("🔄 Testing orchestration prompt with API routes context...")
    
    # Mock session state with API routes (the scenario that causes duplication)
    session_state = {
        "system_type": "fullstack_web_app",  # Move to top level
        "architectural_context": {           # Move to top level
            "modules": {
                "backend": {
                    "boundary_type": "api_layer",
                    "languages": ["python"],
                    "responsibilities": ["REST API endpoints", "business logic"]
                },
                "frontend": {
                    "boundary_type": "ui_layer", 
                    "languages": ["javascript"],
                    "responsibilities": ["React components", "user interface"]
                }
            }
        },
        "objective": {
            "task": "Ensure the backend has a complete FastAPI server with working endpoints that the frontend components can call",
        },
        "backend_api_routes": {
            "backend/api/endpoints.py": [
                {"method": "POST", "path": "/analyze_conflict", "description": "Analyze conflict patterns"},
                {"method": "GET", "path": "/emotional_intelligence_score", "description": "Get EI score"},
                {"method": "POST", "path": "/communication_pattern_analysis", "description": "Analyze communication"}
            ]
        },
        "api_route_summary": "POST /analyze_conflict, GET /emotional_intelligence_score, POST /communication_pattern_analysis",
        "knowledge_base": Mock()
    }
    
    # Mock knowledge retrieval to avoid external dependencies
    with patch('i2c.workflow.orchestration_team._retrieve_knowledge_context') as mock_knowledge:
        mock_knowledge.return_value = """
# FastAPI Router Patterns
Use routers to organize API endpoints:
- Define endpoints with @router.post("/endpoint") 
- Import router in main.py: from api.endpoints import router
- Include router: app.include_router(router, prefix="/api")
"""
        
        # Build the orchestration team (this constructs the compound prompt)
        team = build_orchestration_team(session_state=session_state)
        
        # Extract the instructions (compound prompt)
        instructions = team.instructions
        prompt_text = "\n".join(instructions) if isinstance(instructions, list) else str(instructions)
        
        # Test specific scenarios
        assert isinstance(instructions, list), "Instructions should be a list"
        assert len(instructions) > 10, "Should have substantial instructions"
        
        # Check for architectural context - update to match new format
        has_fullstack_rules = "FULLSTACK WEB APP" in prompt_text
        assert has_fullstack_rules, "Should include fullstack architectural rules"
        
        print("   ✅ Orchestration prompt construction test completed")

def test_orchestration_prompt_without_api_routes():
    """Test orchestration prompt when no API routes exist (should not have conflicts)"""
    print("🔄 Testing orchestration prompt without API routes...")
    
    session_state = {
        "system_type": "fullstack_web_app",
        "architectural_context": {
            "modules": {
                "frontend": {"boundary_type": "ui_layer"},
                "backend": {"boundary_type": "api_layer"}
            }
        }
    }
    
    with patch('i2c.workflow.orchestration_team._retrieve_knowledge_context') as mock_knowledge:
        mock_knowledge.return_value = "FastAPI best practices..."
        
        team = build_orchestration_team(session_state=session_state)
        instructions = team.instructions
        prompt_text = "\n".join(instructions) if isinstance(instructions, list) else str(instructions)
        
        # The test should pass with substantial content
        assert len(prompt_text) > 100, "Should have substantial prompt content"
        assert "fullstack" in prompt_text.lower(), "Should include fullstack rules"
        print("   ✅ Prompt without API routes works correctly")

def test_dynamic_architectural_rules():
    """Test that architectural rules are built dynamically from session state"""
    print("🔄 Testing dynamic architectural rules construction...")
    
    # Test with Node.js/Express system
    session_state = {
        "system_type": "api_service",
        "architectural_context": {
            "modules": {
                "api": {
                    "boundary_type": "api_layer",
                    "languages": ["javascript"],
                    "responsibilities": ["Express routes", "middleware"],
                    "folder_structure": {"base_path": "src/routes"}
                },
                "services": {
                    "boundary_type": "business_logic", 
                    "languages": ["javascript"],
                    "responsibilities": ["business logic", "data processing"],
                    "folder_structure": {"base_path": "src/services"}
                }
            },
            "constraints": [
                "Use Express.js for routing",
                "Separate concerns between routes and services"
            ],
            "file_organization_rules": {
                "api_routes": "src/routes",
                "business_logic": "src/services",
                "utilities": "src/utils"
            }
        },
        "backend_api_routes": {
            "src/routes/users.js": [
                {"method": "GET", "path": "/users", "function": "getUsers"},
                {"method": "POST", "path": "/users", "function": "createUser"}
            ]
        },
        "api_route_summary": "GET /users, POST /users"
    }
    
    with patch('i2c.workflow.orchestration_team._retrieve_knowledge_context') as mock_knowledge:
        mock_knowledge.return_value = "Express.js best practices..."
        
        team = build_orchestration_team(session_state=session_state)
        prompt_text = "\n".join(team.instructions)
        
        # Test that it uses the correct system type
        assert "API SERVICE" in prompt_text, "Should use detected system type"
        
        # Test that it includes module information
        assert "api (api_layer)" in prompt_text, "Should include api module"
        assert "services (business_logic)" in prompt_text, "Should include services module"
        assert "javascript" in prompt_text, "Should include detected languages"
        
        # Test that it includes constraints
        assert "Express.js for routing" in prompt_text, "Should include constraints"
        
        # Test that it includes existing API routes
        assert "GET /users" in prompt_text, "Should include existing API routes"
        
        # Test that it doesn't have Python/FastAPI hardcoded rules
        assert "FastAPI" not in prompt_text, "Should not contain hardcoded FastAPI references"
        
        print("   ✅ Dynamic architectural rules work correctly")

def test_multiple_language_support():
    """Test architectural rules with multiple languages"""
    session_state = {
        "system_type": "fullstack_web_app",
        "architectural_context": {
            "modules": {
                "backend": {
                    "boundary_type": "api_layer",
                    "languages": ["go", "sql"],
                    "responsibilities": ["REST API", "database operations"],
                    "folder_structure": {"base_path": "cmd/api"}
                },
                "frontend": {
                    "boundary_type": "ui_layer",
                    "languages": ["typescript", "css"],
                    "responsibilities": ["Vue.js components", "styling"],
                    "folder_structure": {"base_path": "web/src"}
                }
            }
        }
    }
    
    with patch('i2c.workflow.orchestration_team._retrieve_knowledge_context') as mock_knowledge:
        mock_knowledge.return_value = ""
        
        team = build_orchestration_team(session_state=session_state)
        prompt_text = "\n".join(team.instructions)
        
        # Test multi-language support
        assert "go, sql" in prompt_text, "Should include Go and SQL languages"
        assert "typescript, css" in prompt_text, "Should include TypeScript and CSS"
        
        print("   ✅ Multi-language support works correctly")

def test_fallback_when_no_architectural_context():
    """Test behavior when no architectural context is available"""
    session_state = {
        "system_type": "unknown"
        # No architectural_context
    }
    
    with patch('i2c.workflow.orchestration_team._retrieve_knowledge_context') as mock_knowledge:
        mock_knowledge.return_value = ""
        
        team = build_orchestration_team(session_state=session_state)
        prompt_text = "\n".join(team.instructions)
        
        # Should still have basic instructions
        assert "Code Evolution Team" in prompt_text, "Should have core instructions"
        assert "valid JSON" in prompt_text, "Should have format requirements"
        
        # Should not have architectural rules section
        assert "ARCHITECTURAL RULES" not in prompt_text, "Should not have arch rules without context"
        
        print("   ✅ Fallback behavior works correctly")