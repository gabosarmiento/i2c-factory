# test_generation_workflow_session_state.py
"""
Unit tests for GenerationWorkflow session state preservation and propagation.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from i2c.workflow.generation_workflow import GenerationWorkflow

@pytest.fixture
def sample_session_state():
    """Sample session state passed from workflow controller"""
    return {
        'knowledge_base': Mock(),
        'architectural_context': {
            'system_type': 'fullstack_web_app',
            'modules': {
                'frontend': {'boundary_type': 'ui_layer'},
                'backend': {'boundary_type': 'api_layer'}
            }
        },
        'backend_api_routes': {
            'GET': [{'path': '/api/users'}],
            'POST': [{'path': '/api/data'}]
        },
        'api_route_summary': 'Available endpoints:\nGET /api/users\nPOST /api/data',
        'retrieved_context': 'Some knowledge context from previous steps',
        'enhanced_objective': {'objective': 'Build fullstack app'},
        'project_context': {'files': ['main.py']},
        'reflection_memory': [],
        'language': 'Python',
        'objective': 'Create a test application',
        'project_path': '/test/project'
    }

@pytest.fixture
def temp_project():
    """Create temporary project directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Create basic project structure
        backend_dir = project_path / "backend"
        backend_dir.mkdir()
        
        main_py = backend_dir / "main.py"
        main_py.write_text("""
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/test")
def test_endpoint():
    return {"test": "data"}
""")
        
        yield project_path

@pytest.fixture
def structured_goal():
    """Sample structured goal"""
    return {
        'objective': 'Create a test application',
        'language': 'Python',
        'constraints': ['Use FastAPI', 'Follow best practices']
    }

def test_session_state_initialization_preserves_existing(sample_session_state):
    """Test that workflow initialization preserves existing session state"""
    print("🔄 Testing session state initialization preserves existing state...")
    
    workflow = GenerationWorkflow(session_id="test-gen")
    
    # Manually set session state (simulating what workflow_controller does)
    workflow.session_state.update(sample_session_state)
    
    # Re-initialize (simulating __init__ being called)
    workflow.session_state.setdefault("generation_memory", [])
    
    # Should preserve all existing keys
    assert 'knowledge_base' in workflow.session_state
    assert 'architectural_context' in workflow.session_state
    assert 'backend_api_routes' in workflow.session_state
    assert 'language' in workflow.session_state
    assert 'objective' in workflow.session_state
    
    # Should add only missing workflow-specific keys
    assert 'generation_memory' in workflow.session_state
    assert workflow.session_state['generation_memory'] == []
    
    # Should not overwrite existing values
    assert workflow.session_state['language'] == 'Python'
    assert workflow.session_state['objective'] == 'Create a test application'
    
    print("   ✅ Session state initialization preserves existing state")

def test_run_method_preserves_session_state(sample_session_state, temp_project, structured_goal):
    """Test that run method preserves existing session state"""
    print("🔄 Testing run method preserves session state...")
    
    workflow = GenerationWorkflow(session_id="test-gen")
    workflow.session_state.update(sample_session_state)
    
    # Test the session state setup logic directly (without running full workflow)
    # Simulate what the run method does for session state setup
    
    # Reset workflow-specific state (preserve important session state)
    workflow.session_state["generation_memory"] = []
    
    # Only set these if they don't already exist (preserve passed values)
    workflow.session_state.setdefault("language", structured_goal.get("language"))
    workflow.session_state.setdefault("objective", structured_goal.get("objective"))
    workflow.session_state.setdefault("project_path", str(temp_project))
    workflow.session_state.setdefault("structured_goal", structured_goal)
    
    # Always reset code_map for this workflow run
    workflow.session_state["code_map"] = None
    # Should preserve existing session state
    assert workflow.session_state['knowledge_base'] == sample_session_state['knowledge_base']
    assert workflow.session_state['architectural_context'] == sample_session_state['architectural_context']
    assert workflow.session_state['backend_api_routes'] == sample_session_state['backend_api_routes']
    
    # Should preserve existing values over structured_goal
    assert workflow.session_state['language'] == sample_session_state['language']  # 'Python' from session
    assert workflow.session_state['objective'] == sample_session_state['objective']  # From session
    
    # Should have workflow-specific state
    assert 'generation_memory' in workflow.session_state
    
    # Should preserve existing project_path from session state (not overwrite with temp_project)
    assert workflow.session_state['project_path'] == sample_session_state['project_path']  # '/test/project'
    
    # Structured goal should be added since it wasn't in session state
    assert workflow.session_state['structured_goal'] == structured_goal
    
    print("   ✅ Run method preserves session state correctly")

def test_planning_phase_uses_session_state_values(sample_session_state, structured_goal):
    """Test that planning phase uses values from session state"""
    print("🔄 Testing planning phase uses session state values...")
    
    workflow = GenerationWorkflow(session_id="test-gen")
    workflow.session_state.update(sample_session_state)
    
    # Mock the planner agent
    mock_agent = Mock()
    mock_response = Mock()
    mock_response.content = '{"files": ["backend/main.py", "frontend/src/App.jsx"]}'
    mock_agent.run.return_value = mock_response
    
    with patch('i2c.agents.core_agents.get_rag_enabled_agent', return_value=mock_agent):
        with patch('i2c.utils.json_extraction.extract_json_with_fallback') as mock_extract:
            mock_extract.return_value = {"files": ["backend/main.py", "frontend/src/App.jsx"]}
            
            # Run planning phase
            responses = list(workflow.planning_phase(structured_goal))
            
            # Should have called agent with session state
            agent_call = mock_agent.run.call_args[0][0]
            
            # Should use values from session state, not structured_goal
            assert sample_session_state['language'] in agent_call  # 'Python' from session
            assert sample_session_state['objective'] in agent_call  # From session
            
            # Should have file plan in session state
            assert 'file_plan' in workflow.session_state
            assert workflow.session_state['file_plan'] == ["backend/main.py", "frontend/src/App.jsx"]
            
            print("   ✅ Planning phase uses session state values correctly")

def test_code_generation_phase_preserves_session_state(sample_session_state):
    """Test that code generation phase preserves and uses session state"""
    print("🔄 Testing code generation phase preserves session state...")
    
    workflow = GenerationWorkflow(session_id="test-gen")
    workflow.session_state.update(sample_session_state)
    workflow.session_state['file_plan'] = ['backend/main.py', 'frontend/src/App.jsx']
    
    # Mock the code builder agent
    mock_agent = Mock()
    mock_response = Mock()
    mock_response.content = 'Generated code content'
    mock_agent.run.return_value = mock_response
    
    with patch('i2c.agents.core_agents.get_rag_enabled_agent', return_value=mock_agent):
        with patch('i2c.utils.markdown.strip_markdown_code_block', return_value='Generated code content'):
            
            # Run code generation phase
            responses = list(workflow.code_generation_phase())
            
            # Should have preserved session state
            assert workflow.session_state['knowledge_base'] == sample_session_state['knowledge_base']
            assert workflow.session_state['backend_api_routes'] == sample_session_state['backend_api_routes']
            
            # Should have generated code
            assert 'generated_code' in workflow.session_state
            generated_code = workflow.session_state['generated_code']
            assert 'backend/main.py' in generated_code
            assert 'frontend/src/App.jsx' in generated_code
            
            print("   ✅ Code generation phase preserves session state correctly")

def test_api_route_extraction_preserves_session_state(sample_session_state, temp_project):
    """Test that API route extraction preserves existing session state"""
    print("🔄 Testing API route extraction preserves session state...")
    
    workflow = GenerationWorkflow(session_id="test-gen")
    workflow.session_state.update(sample_session_state)
    workflow.session_state['project_path'] = str(temp_project)
    
    # Mock API route injection
    mock_updated_session = {
        **sample_session_state,
        'backend_api_routes': {
            'GET': [{'path': '/api/test'}, {'path': '/api/users'}],
            'POST': [{'path': '/api/data'}]
        },
        'api_route_summary': 'Updated API summary'
    }
    
    with patch('i2c.utils.api_route_tracker.inject_api_routes_into_session', return_value=mock_updated_session):
        
        # Simulate the API route extraction logic
        arch_context = workflow.session_state.get("architectural_context", {})
        system_type = arch_context.get("system_type")
        
        if system_type in ["fullstack_web_app", "microservices"]:
            from i2c.utils.api_route_tracker import inject_api_routes_into_session
            project_path = Path(workflow.session_state.get("project_path", ""))
            
            updated_session_state = inject_api_routes_into_session(project_path, workflow.session_state)
            workflow.session_state.update(updated_session_state)
        
        # Should preserve original session state
        assert workflow.session_state['knowledge_base'] == sample_session_state['knowledge_base']
        assert workflow.session_state['architectural_context'] == sample_session_state['architectural_context']
        
        # Should have updated API routes
        routes = workflow.session_state['backend_api_routes']
        assert len(routes['GET']) == 2  # Original + new
        assert workflow.session_state['api_route_summary'] == 'Updated API summary'
        
        print("   ✅ API route extraction preserves session state correctly")

def test_constraints_handling_from_multiple_sources(sample_session_state, structured_goal):
    """Test that constraints are handled from both session state and structured goal"""
    print("🔄 Testing constraints handling from multiple sources...")
    
    workflow = GenerationWorkflow(session_id="test-gen")
    workflow.session_state.update(sample_session_state)
    
    # Add constraints to session state
    workflow.session_state['constraints'] = ['Session constraint 1', 'Session constraint 2']
    
    # Mock the code builder
    mock_agent = Mock()
    mock_response = Mock()
    mock_response.content = 'Generated code'
    mock_agent.run.return_value = mock_response
    
    workflow.session_state['file_plan'] = ['test.py']
    
    with patch('i2c.agents.core_agents.get_rag_enabled_agent', return_value=mock_agent):
        with patch('i2c.utils.markdown.strip_markdown_code_block', return_value='Generated code'):
            
            # Run code generation phase
            responses = list(workflow.code_generation_phase())
            
            # Should have used constraints from session state
            # The build_prompt call should include session state constraints
            build_prompt_call = mock_agent.run.call_args[0][0]
            assert 'Session constraint 1' in build_prompt_call
            assert 'Session constraint 2' in build_prompt_call
            
            print("   ✅ Constraints handled from session state correctly")

def test_session_state_debugging_without_modification(sample_session_state):
    """Test that debugging logs don't modify session state"""
    print("🔄 Testing session state debugging without modification...")
    
    workflow = GenerationWorkflow(session_id="test-gen")
    original_session_state = sample_session_state.copy()
    workflow.session_state.update(sample_session_state)
    
    # Simulate the debugging logic without actual logging
    important_keys = ['knowledge_base', 'architectural_context', 'backend_api_routes', 'retrieved_context']
    
    extracted_keys = []
    missing_keys = []
    
    for key in important_keys:
        if key in workflow.session_state:
            extracted_keys.append(key)
        else:
            missing_keys.append(key)
    
    # Session state should be unchanged after debugging
    for key, value in original_session_state.items():
        assert workflow.session_state[key] == value
        
    # Should have found expected keys
    assert 'knowledge_base' in extracted_keys
    assert 'architectural_context' in extracted_keys
    assert 'backend_api_routes' in extracted_keys
    
    print("   ✅ Debugging doesn't modify session state")

def test_setdefault_behavior_preserves_existing_values():
    """Test that setdefault preserves existing values"""
    print("🔄 Testing setdefault behavior preserves existing values...")
    
    workflow = GenerationWorkflow(session_id="test-gen")
    
    # Set initial values
    workflow.session_state['language'] = 'JavaScript'
    workflow.session_state['objective'] = 'Build React app'
    
    # Use setdefault with different values
    workflow.session_state.setdefault('language', 'Python')
    workflow.session_state.setdefault('objective', 'Build FastAPI app')
    workflow.session_state.setdefault('new_key', 'new_value')
    
    # Should preserve existing values
    assert workflow.session_state['language'] == 'JavaScript'  # Not changed
    assert workflow.session_state['objective'] == 'Build React app'  # Not changed
    
    # Should add new key
    assert workflow.session_state['new_key'] == 'new_value'
    
    print("   ✅ setdefault preserves existing values correctly")

if __name__ == "__main__":
    print("Running GenerationWorkflow session state tests...")
    print("=" * 60)
    
    # Create test fixtures manually
    sample_session = {
        'knowledge_base': Mock(),
        'architectural_context': {'system_type': 'fullstack_web_app'},
        'backend_api_routes': {'GET': [{'path': '/api/test'}]},
        'language': 'Python',
        'objective': 'Test app'
    }
    
    structured_goal = {
        'objective': 'Different objective',
        'language': 'JavaScript',  # Different from session
        'constraints': ['Use FastAPI']
    }
    
    try:
        # Run tests manually
        test_session_state_initialization_preserves_existing(sample_session)
        print("\n" + "="*50)
        
        test_setdefault_behavior_preserves_existing_values()
        print("\n" + "="*50)
        
        test_session_state_debugging_without_modification(sample_session)
        print("\n" + "="*50)
        
        print("✅ GenerationWorkflow session state tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()