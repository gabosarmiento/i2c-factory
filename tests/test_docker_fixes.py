#!/usr/bin/env python3
"""
Test Docker configuration fixes
"""

import sys
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(project_root))

# Initialize environment first
from i2c.bootstrap import initialize_environment
initialize_environment()

def test_docker_config_fixes():
    """Test the Docker configuration improvements"""
    
    print("🧪 Testing Docker configuration fixes...")
    
    from i2c.agents.sre_team.docker import DockerConfigAgent
    
    # Create temporary project structure
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Create backend and frontend directories
        backend_dir = project_path / "backend"
        frontend_dir = project_path / "frontend"
        backend_dir.mkdir()
        frontend_dir.mkdir()
        
        # Create mock architectural context
        architectural_context = {
            "system_type": "fullstack_web_app",
            "modules": {
                "backend": {"language": "python", "framework": "fastapi"},
                "frontend": {"language": "javascript", "framework": "react"}
            }
        }
        
        # Create Docker config agent
        docker_agent = DockerConfigAgent(project_path)
        
        # Generate Docker configs
        result = docker_agent.generate_docker_configs(project_path, architectural_context)
        
        print(f"✅ Generated {len(result['configs_created'])} Docker config files:")
        for config in result['configs_created']:
            print(f"  - {config}")
        
        # Test 1: Check if docker-compose.yml doesn't have version
        compose_file = project_path / "docker-compose.yml"
        if compose_file.exists():
            compose_content = compose_file.read_text()
            if "version:" not in compose_content:
                print("✅ docker-compose.yml doesn't have obsolete version attribute")
            else:
                print("❌ docker-compose.yml still has obsolete version attribute")
                return False
        
        # Test 2: Check if nginx.conf was created
        nginx_file = frontend_dir / "nginx.conf"
        if nginx_file.exists():
            print("✅ nginx.conf was generated for frontend")
            
            # Check nginx config content
            nginx_content = nginx_file.read_text()
            if "proxy_pass http://backend:8000/" in nginx_content:
                print("✅ nginx.conf includes proper API proxy configuration")
            else:
                print("❌ nginx.conf missing API proxy configuration")
                return False
        else:
            print("❌ nginx.conf was not generated")
            return False
        
        # Test 3: Check if port allocation is dynamic
        if compose_file.exists():
            compose_content = compose_file.read_text()
            if '"0:5432"' in compose_content:
                print("✅ PostgreSQL uses dynamic port allocation to avoid conflicts")
            else:
                print("❌ PostgreSQL port allocation is not dynamic")
                return False
        
        # Test 4: Check if all expected files were created
        expected_files = [
            "backend/Dockerfile",
            "frontend/Dockerfile", 
            "frontend/nginx.conf",
            "docker-compose.yml",
            ".dockerignore"
        ]
        
        missing_files = []
        for expected_file in expected_files:
            if not (project_path / expected_file).exists():
                missing_files.append(expected_file)
        
        if not missing_files:
            print(f"✅ All {len(expected_files)} expected files were created")
        else:
            print(f"❌ Missing files: {missing_files}")
            return False
        
        print("✅ All Docker configuration fixes are working correctly!")
        return True

def test_session_knowledge_base_serialization():
    """Test SessionKnowledgeBase JSON serialization"""
    
    print("\n🧪 Testing SessionKnowledgeBase serialization...")
    
    from i2c.workflow.scenario_processor import SessionKnowledgeBase
    from unittest.mock import Mock
    import json
    
    # Create mock db and embed_model
    mock_db = Mock()
    mock_embed_model = Mock()
    
    # Create SessionKnowledgeBase instance
    knowledge_base = SessionKnowledgeBase(mock_db, mock_embed_model, "test_space")
    
    # Test 1: Check to_dict method
    dict_repr = knowledge_base.to_dict()
    expected_keys = ["_type", "knowledge_space", "status"]
    
    if all(key in dict_repr for key in expected_keys):
        print("✅ SessionKnowledgeBase.to_dict() includes all expected keys")
    else:
        print(f"❌ Missing keys in to_dict(): {set(expected_keys) - set(dict_repr.keys())}")
        return False
    
    # Test 2: Check JSON serialization
    try:
        json_str = json.dumps(dict_repr)
        print("✅ SessionKnowledgeBase.to_dict() is JSON serializable")
    except Exception as e:
        print(f"❌ SessionKnowledgeBase.to_dict() not JSON serializable: {e}")
        return False
    
    # Test 3: Check from_dict reconstruction
    try:
        reconstructed = SessionKnowledgeBase.from_dict(dict_repr, mock_db, mock_embed_model)
        if reconstructed.knowledge_space == "test_space":
            print("✅ SessionKnowledgeBase.from_dict() reconstructs correctly")
        else:
            print("❌ SessionKnowledgeBase.from_dict() doesn't preserve data")
            return False
    except Exception as e:
        print(f"❌ SessionKnowledgeBase.from_dict() failed: {e}")
        return False
    
    # Test 4: Test session state cleaning function
    test_session_state = {
        "knowledge_base": knowledge_base,
        "other_data": "test",
        "nested": {
            "knowledge_base": knowledge_base
        }
    }
    
    def clean_session_state(obj):
        """Serialize SessionKnowledgeBase objects recursively"""
        if isinstance(obj, SessionKnowledgeBase):
            return obj.to_dict()
        elif isinstance(obj, dict):
            cleaned = {}
            for k, v in obj.items():
                if isinstance(v, SessionKnowledgeBase):
                    cleaned[k] = v.to_dict()
                elif isinstance(v, dict):
                    cleaned[k] = clean_session_state(v)
                elif isinstance(v, list):
                    cleaned[k] = [clean_session_state(item) for item in v]
                else:
                    cleaned[k] = v
            return cleaned
        return obj
    
    try:
        cleaned_state = clean_session_state(test_session_state)
        json_str = json.dumps(cleaned_state)
        print("✅ Session state with SessionKnowledgeBase can be cleaned and serialized")
    except Exception as e:
        print(f"❌ Session state cleaning failed: {e}")
        return False
    
    print("✅ SessionKnowledgeBase serialization fixes are working correctly!")
    return True

if __name__ == "__main__":
    print("🔧 Docker and Serialization Fixes Validation Test")
    print("=" * 60)
    
    # Run the tests
    docker_success = test_docker_config_fixes()
    serialization_success = test_session_knowledge_base_serialization()
    
    print("\n" + "=" * 60)
    print("📋 Final Results:")
    print(f"  - Docker Config Fixes: {'✅ PASSED' if docker_success else '❌ FAILED'}")
    print(f"  - Serialization Fixes: {'✅ PASSED' if serialization_success else '❌ FAILED'}")
    
    overall_success = docker_success and serialization_success
    print(f"  - Overall: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n🎉 Docker and serialization issues are resolved!")
        print("   The container tests should now work correctly.")
    else:
        print("\n⚠️  Some issues detected. Check the test output above.")
    
    sys.exit(0 if overall_success else 1)