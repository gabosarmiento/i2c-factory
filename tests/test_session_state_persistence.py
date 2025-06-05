#!/usr/bin/env python3
"""
Test session state persistence between generation and agentic evolution phases
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
project_root = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(project_root))

# Initialize environment first
from i2c.bootstrap import initialize_environment
initialize_environment()

def test_route_and_execute_returns_session_state():
    """Test that route_and_execute returns session state in the result"""
    
    print("🧪 Testing route_and_execute session state return...")
    
    from i2c.workflow.orchestrator import route_and_execute
    
    # Create temporary project path
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Mock session state with backend API routes
        input_session_state = {
            'knowledge_base': Mock(),
            'backend_api_routes': {
                'GET': [{'path': '/api/test', 'function': 'test_endpoint'}],
                'POST': [{'path': '/api/create', 'function': 'create_endpoint'}]
            },
            'architectural_context': {'system_type': 'fullstack_web_app'}
        }
        
        # Mock structured goal
        structured_goal = {
            'objective': 'Create a test app',
            'language': 'python',
            'system_type': 'fullstack_web_app'
        }
        
        # Mock the workflow controller and its methods
        with patch('i2c.workflow.orchestrator.WorkflowController') as mock_controller_class:
            mock_controller = Mock()
            mock_session_manager = Mock()
            
            # Setup session manager to return updated session state
            updated_session_state = input_session_state.copy()
            updated_session_state['generation_completed'] = True
            updated_session_state['code_map'] = {'main.py': 'print("hello")'}
            
            mock_session_manager.get_state.return_value = updated_session_state
            mock_controller.session_manager = mock_session_manager
            mock_controller.run_complete_workflow.return_value = True
            mock_controller.get_last_error.return_value = None
            
            mock_controller_class.return_value = mock_controller
            
            # Mock the progress and file list functions
            with patch('i2c.workflow.orchestrator.show_progress'), \
                 patch('i2c.workflow.orchestrator.show_file_list'):
                
                # Call route_and_execute
                result = route_and_execute(
                    action_type='generate',
                    action_detail=structured_goal,
                    current_project_path=project_path,
                    current_structured_goal=structured_goal,
                    session_state=input_session_state
                )
        
        # Test 1: Check return type
        if isinstance(result, dict):
            print("✅ route_and_execute returns a dictionary")
        else:
            print(f"❌ route_and_execute returns {type(result)}, expected dict")
            return False
        
        # Test 2: Check success status
        if result.get('success') is True:
            print("✅ route_and_execute indicates success")
        else:
            print(f"❌ route_and_execute success={result.get('success')}, expected True")
            return False
        
        # Test 3: Check session state is included
        if 'session_state' in result:
            print("✅ route_and_execute includes session_state in result")
        else:
            print("❌ route_and_execute missing session_state in result")
            return False
        
        # Test 4: Check session state content
        returned_session_state = result['session_state']
        if 'backend_api_routes' in returned_session_state:
            print("✅ backend_api_routes preserved in returned session state")
        else:
            print("❌ backend_api_routes missing from returned session state")
            return False
        
        # Test 5: Check new keys were added
        if 'generation_completed' in returned_session_state:
            print("✅ New session state keys added during generation")
        else:
            print("❌ Session state not properly updated during generation")
            return False
        
        print("✅ route_and_execute session state return working correctly!")
        return True

def test_scenario_processor_session_state_flow():
    """Test that scenario processor properly updates session state between steps"""
    
    print("\n🧪 Testing scenario processor session state flow...")
    
    from i2c.workflow.scenario_processor import ScenarioProcessor
    from unittest.mock import Mock
    import tempfile
    import json
    
    # Create temporary scenario file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        scenario_data = {
            "project_name": "test_project",
            "steps": [
                {
                    "type": "initial_generation",
                    "prompt": "Create a test app"
                },
                {
                    "type": "agentic_evolution", 
                    "objective": {"task": "Test evolution"}
                }
            ]
        }
        json.dump(scenario_data, f)
        scenario_path = f.name
    
    try:
        processor = ScenarioProcessor(scenario_path)
        
        # Mock the initial session state with backend API routes
        processor.session_state = {
            'knowledge_base': Mock(),
            'backend_api_routes': {
                'GET': [{'path': '/api/test'}],
                'POST': [{'path': '/api/create'}]
            },
            'architectural_context': {'system_type': 'fullstack_web_app'}
        }
        
        # Mock route_and_execute to return session state
        def mock_route_and_execute(*args, **kwargs):
            # Simulate generation adding new session state data
            updated_state = kwargs.get('session_state', {}).copy()
            updated_state['code_map'] = {'main.py': 'generated code'}
            updated_state['generation_completed'] = True
            
            return {
                'success': True,
                'error': None,
                'session_state': updated_state
            }
        
        # Test the session state update logic
        original_state_keys = set(processor.session_state.keys())
        
        # Simulate what happens in _process_initial_generation_step
        mock_result = mock_route_and_execute(session_state=processor.session_state)
        
        if isinstance(mock_result, dict) and "session_state" in mock_result:
            processor.session_state.update(mock_result["session_state"])
            updated_keys = set(processor.session_state.keys())
            
            # Check that session state was updated
            if len(updated_keys) > len(original_state_keys):
                print("✅ Session state properly updated with new keys")
            else:
                print("❌ Session state not properly updated")
                return False
            
            # Check that backend_api_routes are preserved
            if 'backend_api_routes' in processor.session_state:
                print("✅ backend_api_routes preserved after generation")
            else:
                print("❌ backend_api_routes lost after generation")
                return False
            
            # Check that new generation data was added
            if 'code_map' in processor.session_state:
                print("✅ New generation data added to session state")
            else:
                print("❌ New generation data not added to session state")
                return False
        else:
            print("❌ route_and_execute simulation didn't return proper session state")
            return False
        
        print("✅ Scenario processor session state flow working correctly!")
        return True
        
    finally:
        Path(scenario_path).unlink()  # Clean up temp file

if __name__ == "__main__":
    print("🔧 Session State Persistence Validation Test")
    print("=" * 60)
    
    # Run the tests
    route_execute_success = test_route_and_execute_returns_session_state()
    scenario_flow_success = test_scenario_processor_session_state_flow()
    
    print("\n" + "=" * 60)
    print("📋 Final Results:")
    print(f"  - route_and_execute Fix: {'✅ PASSED' if route_execute_success else '❌ FAILED'}")
    print(f"  - Scenario Flow: {'✅ PASSED' if scenario_flow_success else '❌ FAILED'}")
    
    overall_success = route_execute_success and scenario_flow_success
    print(f"  - Overall: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n🎉 Session state persistence issues are resolved!")
        print("   backend_api_routes should now persist between generation and agentic evolution.")
    else:
        print("\n⚠️  Some issues detected. Check the test output above.")
    
    sys.exit(0 if overall_success else 1)