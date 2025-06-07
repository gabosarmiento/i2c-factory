#!/usr/bin/env python3
"""
Test the new diagnostic logging without running a full scenario
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from i2c.bootstrap import initialize_environment
initialize_environment()

from i2c.agents.core_agents import get_rag_enabled_agent

def test_diagnostic_logging():
    """Test our new logging with different session state sizes"""
    
    print("🧪 Testing diagnostic logging functionality...")
    
    # Test 1: No session state
    print("\n" + "="*50)
    print("TEST 1: No session state")
    print("="*50)
    
    agent = get_rag_enabled_agent("code_builder", session_state=None)
    print(f"Result: {type(agent).__name__ if agent else 'None'}")
    
    # Test 2: Minimal session state
    print("\n" + "="*50)
    print("TEST 2: Minimal session state")
    print("="*50)
    
    minimal_state = {
        "knowledge_base": "mock_kb",
        "project_path": "/test/path"
    }
    
    agent = get_rag_enabled_agent("code_builder", session_state=minimal_state)
    print(f"Result: {type(agent).__name__ if agent else 'None'}")
    
    # Test 3: Large session state (simulating what we saw in logs)
    print("\n" + "="*50)
    print("TEST 3: Large session state (similar to scenario)")
    print("="*50)
    
    large_state = {
        "knowledge_base": "mock_kb",
        "db": "mock_db", 
        "embed_model": "mock_embed",
        "db_path": "./data/lancedb",
        "architectural_context": {"system_type": "fullstack_web_app", "modules": {"backend": {}, "frontend": {}}},
        "system_type": "fullstack_web_app",
        "current_structured_goal": {"objective": "Build emotional intelligence system", "constraints": []},
        "project_path": "/test/project",
        "file_plan": ["backend/main.py", "frontend/src/App.jsx"],
        "code_map": {"backend/main.py": "# FastAPI app\n" * 50, "frontend/src/App.jsx": "// React app\n" * 50},
        "retrieved_context": "This is retrieved context from knowledge base. " * 100,  # ~4,000 chars
        "knowledge_context": {"project_analysis": "Detailed analysis of project structure and requirements. " * 50},  # ~3,000 chars
        "generation_memory": ["step1", "step2", "step3"],
        "backend_api_routes": {"/api/health": "GET", "/api/users": "POST", "/api/analyze": "POST"},
        "api_route_summary": "Summary of API routes for frontend integration. " * 50,  # ~2,500 chars
        "reflection_memory": [{"step": i, "success": True, "details": "Detailed reflection data. " * 20} for i in range(3)],
        "reasoning_trajectory": ["reason1", "reason2", "reason3"],
        "modified_files": {"file1": "changes", "file2": "more changes"},
    }
    
    agent = get_rag_enabled_agent("code_builder", session_state=large_state)
    print(f"Result: {type(agent).__name__ if agent else 'None'}")
    
    print("\n✅ Diagnostic logging test complete!")
    print("The logs above show the session state and instruction metrics.")

if __name__ == "__main__":
    test_diagnostic_logging()