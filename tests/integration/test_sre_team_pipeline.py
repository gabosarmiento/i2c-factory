import pytest
from pathlib import Path
import asyncio
import json

@pytest.mark.integration
def test_sre_validation_pipeline(tmp_path):
    """
    Test the SRE validation pipeline concepts with original components
    """
    # --- Setup a Python file ---
    file_name = tmp_path / "app.py"
    file_name.write_text("""
def add(a, b):
    # This function adds two numbers
    return a + b

def main():
    print("Hello World")
    result = add(5, 3)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
""")

    # Create required directories for Docker config generation
    (tmp_path / "backend").mkdir(exist_ok=True)
    (tmp_path / "frontend").mkdir(exist_ok=True)

    # Test Docker config generation with original implementation
    from i2c.agents.sre_team.docker import DockerConfigAgent
    
    docker_agent = DockerConfigAgent()
    architectural_context = {
        "system_type": "fullstack_web_app",  # Changed to trigger backend/frontend generation
        "modules": {"backend": {"languages": ["python"]}, "frontend": {"languages": ["javascript"]}}
    }
    
    result = docker_agent.generate_docker_configs(tmp_path, architectural_context)
    
    # Verify results
    assert "configs_created" in result
    assert "system_type" in result
    
    print("\n✅ SRE Docker config generation test completed successfully")


@pytest.mark.integration
def test_sre_team_direct_validation(tmp_path):
    """
    Test SRE team components directly with original implementations
    """
    # --- Setup files ---
    file_path = tmp_path / "simple.py"
    file_path.write_text("""def hello():
    return "Hello, World!"
""")
    
    # Test dependency verification
    from i2c.agents.sre_team.dependency import DependencyVerifierAgent
    
    dependency_agent = DependencyVerifierAgent(project_path=tmp_path)
    issues = dependency_agent.check_dependencies(tmp_path)
    
    # Verify results
    assert isinstance(issues, list)
    
    print("\n✅ SRE dependency verification test completed successfully")


@pytest.mark.integration 
def test_sre_components_individually(tmp_path):
    """Test individual SRE components that work with original implementation"""
    
    file_path = tmp_path / "test.py"
    file_path.write_text("def test_function():\n    return True\n")

    # Test Docker config agent
    from i2c.agents.sre_team.docker import DockerConfigAgent
    docker_agent = DockerConfigAgent()
    
    architectural_context = {"system_type": "unknown", "modules": {}}
    docker_result = docker_agent.generate_docker_configs(tmp_path, architectural_context)
    
    assert "configs_created" in docker_result
    
    # Test dependency agent  
    from i2c.agents.sre_team.dependency import DependencyVerifierAgent
    dep_agent = DependencyVerifierAgent(project_path=tmp_path)
    dep_issues = dep_agent.check_dependencies(tmp_path)
    
    assert isinstance(dep_issues, list)
    
    print("✅ Individual SRE components work correctly")


if __name__ == "__main__":
    print("Running SRE validation pipeline tests...")
    pytest.main(["-xvs", __file__])