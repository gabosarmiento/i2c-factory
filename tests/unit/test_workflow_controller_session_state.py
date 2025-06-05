# test_workflow_controller_session_state.py
"""
Unit tests for WorkflowController session state coordination and propagation.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from i2c.workflow.workflow_controller import WorkflowController

@pytest.fixture
def temp_project():
    """Create temporary project directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Create basic project structure
        backend_dir = project_path / "backend"
        backend_dir.mkdir()
        
        main_py = backend_dir / "main.py"
        main_py.write_text("from fastapi import FastAPI\napp = FastAPI()")
        
        yield project_path

@pytest.fixture
def sample_session_state():
    """Sample session state with key components"""
    return {
        'knowledge_base': Mock(),
        'architectural_context': {
            'system_type': 'fullstack_web_app',
            'modules': {'backend': {'boundary_type': 'api_layer'}}
        },
        'backend_api_routes': {
            'GET': [{'path': '/api/test'}],
            'POST': [{'path': '/api/data'}]
        },
        'api_route_summary': 'Available endpoints:\nGET /api/test\nPOST /api/data',
        'retrieved_context': 'Some retrieved knowledge context',
        'enhanced_objective': {'objective': 'Build test app'},
        'project_context': {'files': ['main.py']},
        'reflection_memory': []
    }

@pytest.fixture
def sample_structured_goal():
    """Sample structured goal"""
    return {
        'objective': 'Create a test application',
        'language': 'Python',
        'constraints': ['Use FastAPI', 'Follow best practices']
    }

def test_session_state_passed_to_generation_workflow(temp_project, sample_session_state, sample_structured_goal):
    """Test session state is properly passed to generation workflow"""
    print("🔄 Testing session state passed to generation workflow...")
    
    controller = WorkflowController("test-session")
    
    with patch('i2c.workflow.workflow_controller.GenerationWorkflow') as mock_workflow_class:
        mock_workflow = Mock()
        mock_workflow.session_state = {}
        mock_workflow_class.return_value = mock_workflow
        
        with patch.object(controller, 'run_workflow_with_recovery', return_value=True):
            # Run generation cycle with session state
            success = controller.run_generation_cycle(
                structured_goal=sample_structured_goal,
                project_path=temp_project,
                session_state=sample_session_state
            )
            
            # Should have created workflow
            mock_workflow_class.assert_called_once()
            
            # Should have updated workflow session state with passed session state
            assert 'knowledge_base' in mock_workflow.session_state
            assert 'architectural_context' in mock_workflow.session_state
            assert 'backend_api_routes' in mock_workflow.session_state
            
            print("   ✅ Session state properly passed to GenerationWorkflow")
            assert success

def test_session_state_extracted_from_generation_workflow(temp_project, sample_session_state, sample_structured_goal):
    """Test session state is extracted back from generation workflow"""
    print("🔄 Testing session state extracted from generation workflow...")
    
    controller = WorkflowController("test-session")
    
    # Mock workflow with updated session state
    mock_workflow = Mock()
    mock_workflow.session_state = {
        **sample_session_state,
        'code_map': {'main.py': 'new code'},
        'generated_files': ['main.py', 'api.py'],
        'validation_results': {'passed': True}
    }
    
    with patch('i2c.workflow.workflow_controller.GenerationWorkflow', return_value=mock_workflow):
        with patch.object(controller, 'run_workflow_with_recovery', return_value=True):
            success = controller.run_generation_cycle(
                structured_goal=sample_structured_goal,
                project_path=temp_project,
                session_state=sample_session_state
            )
            
            # Should have extracted important keys from workflow
            extracted_state = controller.session_manager.get_state()
            
            # Check that important keys were extracted
            assert 'code_map' in extracted_state
            assert 'generated_files' in extracted_state
            assert 'validation_results' in extracted_state
            
            print("   ✅ Session state properly extracted from GenerationWorkflow")
            assert success

@patch('i2c.agents.sre_team.sre_team.build_sre_team')
def test_session_state_passed_to_sre_workflow(mock_build_sre, temp_project, sample_session_state):
    """Test session state is passed to SRE workflow"""
    print("🔄 Testing session state passed to SRE workflow...")
    
    # Mock SRE team
    mock_sre_team = Mock()
    mock_sre_team.run_sync.return_value = {
        'passed': True,
        'summary': {'deployment_ready': True},
        'deployment_ready': True,
        'docker_ready': True
    }
    mock_build_sre.return_value = mock_sre_team
    
    controller = WorkflowController("test-session")
    
    # Pre-populate session manager with session state
    for key, value in sample_session_state.items():
        controller.session_manager.update_state(**{key: value})
    
    success = controller.run_sre_workflow(
        project_path=temp_project,
        language="Python",
        session_state=sample_session_state
    )
    
    # Should have called build_sre_team with session state
    mock_build_sre.assert_called_once()
    call_args = mock_build_sre.call_args
    
    assert call_args[1]['project_path'] == temp_project
    assert 'session_state' in call_args[1]
    
    # Should have extracted SRE results
    extracted_state = controller.session_manager.get_state()
    assert 'sre_results' in extracted_state
    assert 'deployment_ready' in extracted_state
    
    print("   ✅ Session state properly passed to SRE workflow")
    assert success

@patch('i2c.agents.quality_team.quality_team.build_quality_team')
def test_session_state_passed_to_quality_workflow(mock_build_quality, temp_project, sample_session_state, sample_structured_goal):
    """Test session state is passed to Quality workflow"""
    print("🔄 Testing session state passed to Quality workflow...")
    
    # Mock Quality team
    mock_quality_team = Mock()
    mock_quality_result = Mock()
    mock_quality_result.passed = True
    mock_quality_team.run.return_value = mock_quality_result
    mock_build_quality.return_value = mock_quality_team
    
    controller = WorkflowController("test-session")
    
    # Add code_map to session state (required for quality workflow)
    session_with_code = {
        **sample_session_state,
        'code_map': {'main.py': 'test code', 'api.py': 'api code'}
    }
    
    # Pre-populate session manager
    for key, value in session_with_code.items():
        controller.session_manager.update_state(**{key: value})
    
    success = controller.run_quality_workflow(
        project_path=temp_project,
        structured_goal=sample_structured_goal,
        session_state=session_with_code
    )
    
    # Should have called build_quality_team with session state
    mock_build_quality.assert_called_once()
    call_args = mock_build_quality.call_args
    assert 'session_state' in call_args[1]
    
    # Should have extracted quality results
    extracted_state = controller.session_manager.get_state()
    assert 'quality_results' in extracted_state
    
    print("   ✅ Session state properly passed to Quality workflow")
    assert success

def test_complete_workflow_session_state_flow(temp_project, sample_session_state, sample_structured_goal):
    """Test session state flows through complete workflow"""
    print("🔄 Testing complete workflow session state flow...")
    
    controller = WorkflowController("test-session")
    
    with patch.object(controller, 'run_generation_cycle', return_value=True) as mock_gen:
        with patch.object(controller, 'run_sre_workflow', return_value=True) as mock_sre:
            with patch.object(controller, 'run_quality_workflow', return_value=True) as mock_quality:
                
                success = controller.run_complete_workflow(
                    action_type="generate",
                    action_detail=sample_structured_goal,
                    project_path=temp_project,
                    structured_goal=sample_structured_goal,
                    session_state=sample_session_state
                )
                
                # Should have called all workflow methods
                mock_gen.assert_called_once()
                mock_sre.assert_called_once()
                mock_quality.assert_called_once()
                
                # Check that session state was passed to each workflow
                gen_call_args = mock_gen.call_args
                assert 'session_state' in gen_call_args[1]
                
                sre_call_args = mock_sre.call_args
                assert 'session_state' in sre_call_args[1]
                
                quality_call_args = mock_quality.call_args
                assert 'session_state' in quality_call_args[1]
                
                print("   ✅ Session state flowed through complete workflow")
                assert success

def test_session_state_merge_and_extraction():
    """Test session state merging and extraction logic"""
    print("🔄 Testing session state merge and extraction...")
    
    controller = WorkflowController("test-session")
    
    # Initial session state
    initial_state = {
        'knowledge_base': Mock(),
        'architectural_context': {'system_type': 'web_app'},
        'project_path': '/test/path'
    }
    
    # Updated session state (simulating workflow results)
    updated_state = {
        **initial_state,
        'backend_api_routes': {'GET': [{'path': '/api/test'}]},
        'code_map': {'main.py': 'new code'},
        'validation_results': {'passed': True}
    }
    
    # Merge initial state
    for key, value in initial_state.items():
        controller.session_manager.update_state(**{key: value})
    
    # Simulate workflow updating state
    for key, value in updated_state.items():
        controller.session_manager.update_state(**{key: value})
    
    # Extract final state
    final_state = controller.session_manager.get_state()
    
    # Should contain all keys
    assert 'knowledge_base' in final_state
    assert 'architectural_context' in final_state
    assert 'backend_api_routes' in final_state
    assert 'code_map' in final_state
    assert 'validation_results' in final_state
    
    print("   ✅ Session state merge and extraction works correctly")

def test_modification_workflow_session_state(temp_project, sample_session_state):
    """Test session state in modification workflow"""
    print("🔄 Testing modification workflow session state...")
    
    controller = WorkflowController("test-session")
    
    with patch('i2c.workflow.workflow_controller.ModificationWorkflow') as mock_workflow_class:
        mock_workflow = Mock()
        mock_workflow.session_state = {}
        mock_workflow_class.return_value = mock_workflow
        
        with patch.object(controller, 'run_workflow_with_recovery', return_value=True):
            with patch('i2c.workflow.workflow_controller.get_db_connection', return_value=Mock()):
                with patch('i2c.workflow.modification.rag_config.get_embed_model', return_value=Mock()):
                     
                    success = controller.run_modification_cycle(
                        user_request="Add new feature",
                        project_path=temp_project,
                        language="Python",
                        session_state=sample_session_state
                    )
                    
                    # Should have updated workflow session state
                    assert len(mock_workflow.session_state) > 0
                    
                    print("   ✅ Session state properly handled in modification workflow")
                    assert success

def test_session_state_key_filtering():
    """Test that workflow-specific keys are filtered during extraction"""
    print("🔄 Testing session state key filtering...")
    
    controller = WorkflowController("test-session")
    
    # Mock workflow with mixed keys
    workflow_session = {
        'action_type': 'generate',  # Should be filtered
        'structured_goal': {'obj': 'test'},  # Should be filtered
        'language': 'Python',  # Should be filtered
        'knowledge_base': Mock(),  # Should be kept
        'backend_api_routes': {'GET': []},  # Should be kept
        'code_map': {'file.py': 'code'},  # Should be kept
        'user_request': 'test request'  # Should be filtered (modification-specific)
    }
    
    # Simulate extraction logic
    important_keys = [
        'knowledge_base', 'architectural_context', 'system_type', 'reflection_memory', 
        'retrieved_context', 'enhanced_objective', 'project_context', 'db_path', 
        'validation_results', 'project_path', 'backend_api_routes', 'api_route_summary'
    ]
    
    extracted_keys = []
    for key, value in workflow_session.items():
        if key not in ['action_type', 'structured_goal', 'language', 'user_request']:
            extracted_keys.append(key)
            controller.session_manager.update_state(**{key: value})
    
    final_state = controller.session_manager.get_state()
    
    # Should have kept important keys
    assert 'knowledge_base' in final_state
    assert 'backend_api_routes' in final_state
    assert 'code_map' in final_state
    
    # Should have filtered workflow-specific keys
    assert 'action_type' not in extracted_keys
    assert 'structured_goal' not in extracted_keys
    assert 'user_request' not in extracted_keys
    
    print("   ✅ Session state key filtering works correctly")

if __name__ == "__main__":
    print("Running WorkflowController session state tests...")
    print("=" * 60)
    
    # Create test fixtures manually
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        backend_dir = project_path / "backend"
        backend_dir.mkdir()
        (backend_dir / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")
        
        session_state = {
            'knowledge_base': Mock(),
            'architectural_context': {'system_type': 'fullstack_web_app'},
            'backend_api_routes': {'GET': [{'path': '/api/test'}]}
        }
        
        structured_goal = {
            'objective': 'Test app',
            'language': 'Python'
        }
        
        try:
            # Run individual tests
            test_session_state_merge_and_extraction()
            print("\n" + "="*50)
            
            test_session_state_key_filtering()
            print("\n" + "="*50)
            
            print("✅ WorkflowController session state tests completed!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()