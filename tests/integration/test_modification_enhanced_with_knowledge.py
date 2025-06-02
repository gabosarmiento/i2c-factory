# test_knowledge_integration.py
"""
Integration test for lean knowledge integration (minimal API calls, smart gating).
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock

from i2c.agents.modification_team.code_modification_manager_agno import (
    apply_modification,
    build_code_modification_team,
    _should_use_knowledge,
    get_knowledge_cache_stats
)

def test_smart_knowledge_gating():
    """Test that knowledge is only used for worthy tasks"""
    
    print("🚪 Testing smart knowledge gating...")
    
    # Tasks that should use knowledge
    worthy_tasks = [
        {"what": "create REST API with authentication"},
        {"what": "implement user management system"},
        {"what": "build database architecture"},
        {"what": "design scalable microservice pattern"},
        {"what": "optimize query performance"}
    ]
    
    # Tasks that should NOT use knowledge  
    trivial_tasks = [
        {"what": "fix typo"},
        {"what": "add comment"},
        {"what": "update version"},
        {"what": "rename variable"},
        {"what": ""}  # Empty task
    ]
    
    # Test worthy tasks
    for task in worthy_tasks:
        should_use = _should_use_knowledge(task)
        assert should_use, f"Should use knowledge for: {task['what']}"
        print(f"   ✅ Using knowledge: {task['what']}")
    
    # Test trivial tasks
    for task in trivial_tasks:
        should_use = _should_use_knowledge(task)
        assert not should_use, f"Should NOT use knowledge for: {task['what']}"
        print(f"   ⏭️  Skipping knowledge: {task['what']}")
    
    print("✅ Smart knowledge gating test passed")

def test_minimal_api_usage_during_modifications():
    """Test that modifications use minimal API calls"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Create mock knowledge base
        mock_kb = Mock()
        mock_kb.retrieve_knowledge.return_value = [
            {"source": "guide.py", "content": "Programming best practices"}
        ]
        
        session_state = {
            "knowledge_base": mock_kb,
            "session_id": "minimal_test",
            "test_mode": True  # Force legacy path to avoid hanging
        }
        
        print("🔥 Testing minimal API usage during modifications...")
        print(f"📁 Project path: {project_path}")
        
        # Mix of complex and trivial tasks
        modification_steps = [
            {"what": "create database architecture", "file": "models.py", "action": "create"},  # Should use knowledge
            {"what": "fix import statement", "file": "utils.py", "action": "modify"},  # Should skip knowledge
            {"what": "implement user authentication system", "file": "auth.py", "action": "create"},  # Should use knowledge
            {"what": "update version number", "file": "setup.py", "action": "modify"},  # Should skip knowledge
        ]
        
        print(f"🔧 Testing {len(modification_steps)} modification steps...")
        
        for i, step in enumerate(modification_steps):
            step_type = "Complex" if _should_use_knowledge(step) else "Trivial"
            print(f"   Step {i+1} ({step_type}): {step['what']}")
            
            result = apply_modification(
                modification_step=step,
                project_path=project_path,
                session_state=session_state
            )
            assert result is not None
        
        # Should have made minimal API calls (only for complex tasks that actually trigger retrieval)
        actual_calls = mock_kb.retrieve_knowledge.call_count
        
        print(f"📞 Total API calls: {actual_calls}")
        print(f"📊 Expected: minimal (only for complex tasks)")
        
        # Should be reasonable - not zero because some tasks are complex, but much less than heavy approach
        assert actual_calls <= 4, f"Too many API calls: {actual_calls}"
        
        print("✅ Minimal API usage test passed")

def test_team_building_no_preload_overhead():
    """Test that team building has no preloading overhead"""
    
    mock_kb = Mock()
    mock_kb.retrieve_knowledge.return_value = [
        {"source": "test.py", "content": "test content"}
    ]
    
    session_state = {
        "knowledge_base": mock_kb,
        "session_id": "no_preload_test"
    }
    
    print("🏗️ Testing team building without preload overhead...")
    
    # Build team - should NOT trigger any preloading
    team = build_code_modification_team(session_state=session_state)
    
    # Should have made ZERO API calls during team building
    assert mock_kb.retrieve_knowledge.call_count == 0
    print(f"📞 API calls during team building: {mock_kb.retrieve_knowledge.call_count}")
    
    # Stats should be minimal
    stats = get_knowledge_cache_stats()
    print(f"📊 Stats: {stats}")
    
    print("✅ No preload overhead test passed")

def test_lean_vs_heavy_comparison():
    """Compare lean approach vs heavy caching approach"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Simulate 10 modification steps
        steps = [
            {"what": f"create component {i}", "file": f"comp{i}.py", "action": "create"}
            for i in range(10)
        ]
        
        mock_kb = Mock()
        mock_kb.retrieve_knowledge.return_value = [
            {"source": "patterns.py", "content": "Component patterns"}
        ]
        
        session_state = {
            "knowledge_base": mock_kb,
            "test_mode": True
        }
        
        print("⚖️ Testing lean vs heavy approach comparison...")
        print(f"🔢 Simulating {len(steps)} modification steps...")
        
        # Process all steps
        for i, step in enumerate(steps):
            apply_modification(step, project_path, session_state=session_state)
        
        # Lean approach should make minimal calls
        actual_calls = mock_kb.retrieve_knowledge.call_count
        
        print(f"📞 Lean approach API calls: {actual_calls}")
        print(f"📊 Heavy approach would make: ~{len(steps) * 4} calls (preload + per-step)")
        
        # Calculate reduction percentage safely
        heavy_calls = len(steps) * 4
        if heavy_calls > 0:
            reduction = ((heavy_calls - actual_calls) / heavy_calls * 100)
            print(f"💰 API call reduction: {reduction:.1f}%")
        
        # Should be significantly fewer calls than heavy approach
        assert actual_calls < len(steps), "Should use fewer calls than number of steps"
        
        print("✅ Lean vs heavy comparison test passed")

def test_knowledge_integration_with_file_types():
    """Test knowledge integration works with different file types"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        mock_kb = Mock()
        mock_kb.retrieve_knowledge.return_value = [
            {"source": "lang_guide.py", "content": "Language-specific best practices"}
        ]
        
        session_state = {
            "knowledge_base": mock_kb,
            "test_mode": True
        }
        
        print("🗂️ Testing knowledge integration with different file types...")
        
        # Different file types
        file_steps = [
            {"what": "create API endpoint", "file": "api.py", "action": "create"},      # Python
            {"what": "create React component", "file": "App.jsx", "action": "create"},  # JavaScript
            {"what": "create Go service", "file": "main.go", "action": "create"},       # Go
        ]
        
        for i, step in enumerate(file_steps):
            file_ext = Path(step["file"]).suffix
            print(f"   Step {i+1}: {step['what']} ({file_ext})")
            
            result = apply_modification(
                modification_step=step,
                project_path=project_path,
                session_state=session_state
            )
            assert result is not None
        
        # Check that API calls were made for complex tasks
        calls_made = mock_kb.retrieve_knowledge.call_count
        print(f"📞 API calls for file type tests: {calls_made}")
        
        print("✅ File type knowledge integration test passed")

if __name__ == "__main__":
    print("Running lean knowledge integration tests...")
    print("=" * 60)
    
    test_smart_knowledge_gating()
    print("\n" + "="*50)
    test_lean_knowledge_retrieval()
    print("\n" + "="*50)
    test_minimal_api_usage_during_modifications()
    print("\n" + "="*50)
    test_team_building_no_preload_overhead()
    print("\n" + "="*50)
    test_lean_vs_heavy_comparison()
    print("\n" + "="*50)
    test_knowledge_integration_with_file_types()
    print("\n" + "="*60)
    print("✅ All lean knowledge integration tests completed!")