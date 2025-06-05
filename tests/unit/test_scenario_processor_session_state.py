# test_scenario_processor_session_state.py
"""
Unit tests for ScenarioProcessor session state preservation and propagation.
"""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from i2c.workflow.scenario_processor import ScenarioProcessor

@pytest.fixture
def temp_scenario_file():
    """Create temporary scenario file"""
    with tempfile.TemporaryDirectory() as temp_dir:
        scenario_path = Path(temp_dir) / "test_scenario.json"
        
        scenario_data = {
            "project_name": "test_project",
            "steps": [
                {
                    "type": "knowledge",
                    "doc_path": "docs/api.md",
                    "project_name": "test_project",
                    "framework": "FastAPI"
                },
                {
                    "type": "initial_generation", 
                    "prompt": "Create a FastAPI application",
                    "project_name": "test_project"
                },
                {
                    "type": "agentic_evolution",
                    "objective": {
                        "task": "Add user authentication",
                        "project_path": "/test/path"
                    }
                }
            ]
        }
        
        with open(scenario_path, 'w') as f:
            json.dump(scenario_data, f)
            
        yield scenario_path

@pytest.fixture
def temp_knowledge_doc():
    """Create temporary knowledge document"""
    with tempfile.TemporaryDirectory() as temp_dir:
        doc_path = Path(temp_dir) / "api.md"
        doc_path.write_text("""
# API Documentation

## FastAPI Best Practices

Use FastAPI for modern Python APIs.

### Authentication
Implement JWT tokens for authentication.
        """)
        yield doc_path

@pytest.fixture
def mock_budget_manager():
    """Mock budget manager"""
    mock = Mock()
    mock.request_approval.return_value = True
    mock.get_session_consumption.return_value = (1000, 0.01)
    mock.update_from_agno_metrics = Mock()
    return mock

def test_session_state_initialization():
    """Test session state is properly initialized"""
    print("🔄 Testing session state initialization...")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"project_name": "test", "steps": []}, f)
        scenario_path = f.name
    
    try:
        processor = ScenarioProcessor(scenario_path)
        
        # Should initialize session state
        assert hasattr(processor, 'session_state')
        assert processor.session_state is not None
        assert isinstance(processor.session_state, dict)
        
        print("   ✅ Session state properly initialized")
    finally:
        Path(scenario_path).unlink()

@patch('i2c.db_utils.get_db_connection')
@patch('i2c.workflow.modification.rag_config.get_embed_model')
def test_knowledge_step_creates_session_state(mock_embed_model, mock_db_connection, 
                                             temp_scenario_file, temp_knowledge_doc, mock_budget_manager):
    """Test knowledge step creates and populates session state"""
    print("🔄 Testing knowledge step creates session state...")
    
    # Mock database components
    mock_db = Mock()
    mock_embed = Mock()
    mock_db_connection.return_value = mock_db
    mock_embed_model.return_value = mock_embed
    
    # Mock the knowledge ingestor
    with patch('i2c.agents.knowledge.enhanced_knowledge_ingestor.EnhancedKnowledgeIngestorAgent') as mock_ingestor_class:
        mock_ingestor = Mock()
        mock_ingestor.execute.return_value = (True, {'successful_files': 1, 'skipped_files': 0})
        mock_ingestor_class.return_value = mock_ingestor
        
        processor = ScenarioProcessor(temp_scenario_file, mock_budget_manager)
        
        # Process knowledge step
        knowledge_step = {
            "type": "knowledge",
            "doc_path": str(temp_knowledge_doc),
            "project_name": "test_project",
            "framework": "FastAPI"
        }
        
        processor._process_knowledge_step(knowledge_step)
        
        # Should have created session state with knowledge components
        assert 'knowledge_base' in processor.session_state
        assert 'db' in processor.session_state
        assert 'embed_model' in processor.session_state
        assert 'db_path' in processor.session_state
        
        # Should have the right values
        assert processor.session_state['db'] == mock_db
        assert processor.session_state['embed_model'] == mock_embed
        assert processor.session_state['db_path'] == "./data/lancedb"
        
        print("   ✅ Knowledge step creates session state correctly")

@patch('i2c.db_utils.get_db_connection')
@patch('i2c.workflow.modification.rag_config.get_embed_model')
def test_knowledge_folder_step_updates_session_state(mock_embed_model, mock_db_connection, 
                                                    temp_scenario_file, mock_budget_manager):
    """Test knowledge folder step updates session state"""
    print("🔄 Testing knowledge folder step updates session state...")
    
    # Mock database components
    mock_db = Mock()
    mock_embed = Mock()
    mock_db_connection.return_value = mock_db
    mock_embed_model.return_value = mock_embed
    
    # Create temporary folder with docs
    with tempfile.TemporaryDirectory() as temp_dir:
        docs_folder = Path(temp_dir) / "docs"
        docs_folder.mkdir()
        (docs_folder / "api.md").write_text("# API Docs")
        (docs_folder / "guide.md").write_text("# User Guide")
        
        # Mock the knowledge ingestor
        with patch('i2c.agents.knowledge.enhanced_knowledge_ingestor.EnhancedKnowledgeIngestorAgent') as mock_ingestor_class:
            mock_ingestor = Mock()
            mock_ingestor.execute.return_value = (True, {'successful_files': 2, 'skipped_files': 0})
            mock_ingestor_class.return_value = mock_ingestor
            
            processor = ScenarioProcessor(temp_scenario_file, mock_budget_manager)
            
            # Initialize with some existing session state
            processor.session_state = {'existing_key': 'existing_value'}
            
            # Process knowledge folder step
            knowledge_folder_step = {
                "type": "knowledge_folder",
                "folder_path": str(docs_folder),
                "project_name": "test_project",
                "framework": "FastAPI"
            }
            
            processor._process_knowledge_folder_step(knowledge_folder_step)
            
            # Should preserve existing session state
            assert processor.session_state['existing_key'] == 'existing_value'
            
            # Should add knowledge components
            assert 'knowledge_base' in processor.session_state
            assert 'db' in processor.session_state
            assert 'embed_model' in processor.session_state
            
            print("   ✅ Knowledge folder step updates session state correctly")

@patch('i2c.workflow.scenario_processor.route_and_execute')
def test_initial_generation_passes_session_state(mock_route_execute, temp_scenario_file, mock_budget_manager):
    """Test initial generation step passes session state"""
    print("🔄 Testing initial generation passes session state...")
    
    # Mock route_and_execute return
    mock_route_execute.return_value = {"success": True, "session_state": {"code_map": {"main.py": "code"}}}
    
    # Mock agent creation
    with patch('i2c.agents.core_agents.get_rag_enabled_agent') as mock_get_agent:
        mock_agent = Mock()
        mock_response = Mock()
        mock_response.content = '{"objective": "Create FastAPI app", "language": "Python"}'
        mock_agent.run.return_value = mock_response
        mock_get_agent.return_value = mock_agent
        
        with patch('i2c.utils.json_extraction.extract_json_with_fallback') as mock_extract:
            mock_extract.return_value = {"objective": "Create FastAPI app", "language": "Python"}
            
            processor = ScenarioProcessor(temp_scenario_file, mock_budget_manager)
            
            # Set up session state with knowledge
            processor.session_state = {
                'knowledge_base': Mock(),
                'architectural_context': {'system_type': 'fullstack_web_app'},
                'db': Mock(),
                'embed_model': Mock()
            }
            
            # Process initial generation step
            generation_step = {
                "type": "initial_generation",
                "prompt": "Create a FastAPI application",
                "project_name": "test_project"
            }
            
            processor._process_initial_generation_step(generation_step)
            
            # Should have called route_and_execute with session state
            mock_route_execute.assert_called_once()
            call_args = mock_route_execute.call_args
            
            assert 'session_state' in call_args[1]
            passed_session_state = call_args[1]['session_state']
            
            # Should contain original knowledge components
            assert 'knowledge_base' in passed_session_state
            assert 'architectural_context' in passed_session_state
            assert 'db' in passed_session_state
            
            # Should have updated session state from result
            assert 'code_map' in processor.session_state
            
            print("   ✅ Initial generation passes session state correctly")

@patch('i2c.workflow.agentic_orchestrator.execute_agentic_evolution_sync')
def test_agentic_evolution_passes_and_receives_session_state(mock_agentic_evolution, temp_scenario_file, mock_budget_manager):
    """Test agentic evolution step passes and receives session state"""
    print("🔄 Testing agentic evolution passes and receives session state...")
    
    # Mock agentic evolution return
    mock_evolution_result = {
        "status": "ok",
        "result": {"decision": "approve", "modifications": {"file.py": "new code"}},
        "session_state": {
            "backend_api_routes": {"GET": [{"path": "/api/test"}]},
            "api_route_summary": "GET /api/test",
            "code_map": {"file.py": "updated code"}
        }
    }
    mock_agentic_evolution.return_value = mock_evolution_result
    
    processor = ScenarioProcessor(temp_scenario_file, mock_budget_manager)
    
    # Set up initial session state
    processor.session_state = {
        'knowledge_base': Mock(),
        'architectural_context': {'system_type': 'fullstack_web_app'},
        'retrieved_context': 'Some context',
        'db': Mock()
    }
    
    # Set up current project path
    with tempfile.TemporaryDirectory() as temp_dir:
        processor.current_project_path = Path(temp_dir)
        processor.current_structured_goal = {"objective": "Test goal"}
        
        # Process agentic evolution step
        evolution_step = {
            "type": "agentic_evolution",
            "objective": {
                "task": "Add user authentication to the application"
            }
        }
        
        processor._process_agentic_evolution_step(evolution_step)
        
        # Should have called agentic evolution with session state
        mock_agentic_evolution.assert_called_once()
        call_args = mock_agentic_evolution.call_args
        
        # Check arguments
        objective = call_args[0][0]
        project_path = call_args[0][1]
        session_state = call_args[0][2]
        
        # Should have passed session state
        assert 'knowledge_base' in session_state
        assert 'architectural_context' in session_state
        assert 'retrieved_context' in session_state
        
        # Should have updated session state from result
        assert 'backend_api_routes' in processor.session_state
        assert 'api_route_summary' in processor.session_state
        assert 'code_map' in processor.session_state
        
        # Should preserve original session state
        assert 'knowledge_base' in processor.session_state
        assert 'architectural_context' in processor.session_state
        
        print("   ✅ Agentic evolution passes and receives session state correctly")

def test_session_state_progression_through_steps(temp_scenario_file, mock_budget_manager):
    """Test session state progresses correctly through multiple steps"""
    print("🔄 Testing session state progression through steps...")
    
    processor = ScenarioProcessor(temp_scenario_file, mock_budget_manager)
    
    # Start with empty session state
    assert len(processor.session_state or {}) == 0

    # Step 1: Knowledge step adds knowledge components
    with patch('i2c.db_utils.get_db_connection', return_value=Mock()):
        with patch('i2c.workflow.modification.rag_config.get_embed_model', return_value=Mock()):
            with patch('i2c.agents.knowledge.enhanced_knowledge_ingestor.EnhancedKnowledgeIngestorAgent') as mock_ingestor_class:
                mock_ingestor = Mock()
                mock_ingestor.execute.return_value = (True, {'successful_files': 1, 'skipped_files': 0})
                mock_ingestor_class.return_value = mock_ingestor
                
                # Create temp doc
                with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                    f.write("# API Docs")
                    temp_doc = f.name
                
                try:
                    knowledge_step = {
                        "doc_path": temp_doc,
                        "project_name": "test",
                        "framework": "FastAPI"
                    }
                    
                    processor._process_knowledge_step(knowledge_step)
                    
                    # Should now have knowledge components
                    assert 'knowledge_base' in processor.session_state
                    assert 'db' in processor.session_state
                    assert 'embed_model' in processor.session_state
                    step1_keys = set(processor.session_state.keys())
                    
                finally:
                    Path(temp_doc).unlink()
    
    # Step 2: Initial generation should preserve knowledge and add more
    with patch('i2c.workflow.scenario_processor.route_and_execute') as mock_route:
        mock_route.return_value = {
            "success": True,
            "session_state": {
                "code_map": {"main.py": "code"},
                "architectural_context": {"system_type": "fullstack_web_app"}
            }
        }
        
        with patch('i2c.agents.core_agents.get_rag_enabled_agent') as mock_get_agent:
            mock_agent = Mock()
            mock_response = Mock()
            mock_response.content = '{"objective": "Test", "language": "Python"}'
            mock_agent.run.return_value = mock_response
            mock_get_agent.return_value = mock_agent
            
            with patch('i2c.utils.json_extraction.extract_json_with_fallback') as mock_extract:
                mock_extract.return_value = {"objective": "Test", "language": "Python"}
                
                generation_step = {
                    "prompt": "Create FastAPI app",
                    "project_name": "test"
                }
                
                processor._process_initial_generation_step(generation_step)
                
                # Should preserve step 1 keys and add new ones
                for key in step1_keys:
                    assert key in processor.session_state
                
                assert 'code_map' in processor.session_state
                assert 'architectural_context' in processor.session_state
                step2_keys = set(processor.session_state.keys())
                
                # Should have more keys than step 1
                assert len(step2_keys) > len(step1_keys)
    
    print("   ✅ Session state progresses correctly through steps")

def test_session_state_debugging_output():
    """Test session state debugging provides useful information"""
    print("🔄 Testing session state debugging output...")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"project_name": "test", "steps": []}, f)
        scenario_path = f.name
    
    try:
        processor = ScenarioProcessor(scenario_path)
        
        # Add some session state
        processor.session_state = {
            'knowledge_base': Mock(),
            'backend_api_routes': {'GET': [{'path': '/api/test'}]},
            'architectural_context': {'system_type': 'fullstack_web_app'},
            'missing_key': 'should_not_be_here'
        }
        
        # Test debugging logic
        important_keys = ['knowledge_base', 'backend_api_routes', 'architectural_context', 'retrieved_context']
        
        found_keys = []
        missing_keys = []
        
        for key in important_keys:
            if key in processor.session_state:
                found_keys.append(key)
            else:
                missing_keys.append(key)
        
        # Should find existing keys
        assert 'knowledge_base' in found_keys
        assert 'backend_api_routes' in found_keys
        assert 'architectural_context' in found_keys
        
        # Should identify missing keys
        assert 'retrieved_context' in missing_keys
        
        print("   ✅ Session state debugging works correctly")
        
    finally:
        Path(scenario_path).unlink()

if __name__ == "__main__":
    print("Running ScenarioProcessor session state tests...")
    print("=" * 60)
    
    try:
        # Run tests manually
        test_session_state_initialization()
        print("\n" + "="*50)
        
        test_session_state_debugging_output()
        print("\n" + "="*50)
        
        print("✅ ScenarioProcessor session state tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()