# tests/integration/test_lean_sre_team_integration.py
"""
Integration tests for the lean SRE team with Docker integration fixes.
Tests that the SRE team works without hanging and produces deployment-ready results.
"""

import pytest
import tempfile
import shutil
import json
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch
import time

# Import components for testing
try:
    from i2c.agents.sre_team.sre_team import build_sre_team, SRELeadAgent
    from i2c.agents.sre_team.docker import DockerConfigAgent
    from i2c.agents.sre_team.dependency import DependencyVerifierAgent
    from i2c.agents.sre_team.sandbox import SandboxExecutorAgent
    SRE_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"SRE components not available: {e}")
    SRE_COMPONENTS_AVAILABLE = False

# Skip all tests if SRE components not available
pytestmark = pytest.mark.skipif(not SRE_COMPONENTS_AVAILABLE, reason="SRE components not available")


class TestLeanSRETeamIntegration:
    """Integration test suite for lean SRE team with Docker fixes"""
    
    @pytest.fixture
    def simple_fullstack_project(self):
        """Create a simple fullstack project for testing"""
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)
        
        # Backend structure
        backend_dir = project_path / "backend"
        backend_dir.mkdir()
        
        # Simple FastAPI backend
        (backend_dir / "main.py").write_text("""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
""")
        
        # Frontend structure
        frontend_dir = project_path / "frontend"
        frontend_src_dir = frontend_dir / "src"
        frontend_src_dir.mkdir(parents=True)
        
        # Simple React frontend
        (frontend_src_dir / "App.jsx").write_text("""
import React from 'react';

function App() {
  return (
    <div className="App">
      <h1>Hello World</h1>
      <p>Simple React App</p>
    </div>
  );
}

export default App;
""")
        
        yield project_path
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_sre_team_creation_and_basic_run(self, simple_fullstack_project):
        """Test that we can create and run the SRE team without hanging"""
        session_state = {
            "project_path": str(simple_fullstack_project)
        }
        
        # Test team creation
        start_time = time.time()
        sre_team = build_sre_team(
            project_path=simple_fullstack_project,
            session_state=session_state
        )
        creation_time = time.time() - start_time
        
        # Should be reasonably fast
        assert creation_time < 10
        assert sre_team is not None
        assert hasattr(sre_team, "run_sync")
        
        # Test basic run (with timeout to catch hangs)
        start_time = time.time()
        try:
            result = sre_team.run_sync()
            execution_time = time.time() - start_time
            
            # Should complete in reasonable time (not hang)
            assert execution_time < 30  # 30 seconds max
            
            # Should return proper structure
            assert isinstance(result, dict)
            assert "passed" in result
            assert "summary" in result
            
            print(f"✅ SRE team completed in {execution_time:.2f}s")
            print(f"Result: {result}")
            
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"❌ SRE team failed after {execution_time:.2f}s: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_docker_agent_run_method(self, simple_fullstack_project):
        """Test that DockerConfigAgent.run() method works correctly"""
        docker_agent = DockerConfigAgent(project_path=simple_fullstack_project)
        
        start_time = time.time()
        result = await docker_agent.run()
        execution_time = time.time() - start_time
        
        # Should be fast
        assert execution_time < 10
        
        # Should return proper format
        assert isinstance(result, dict)
        assert "passed" in result
        assert "files_created" in result
        assert "issues" in result
        assert "system_type" in result
        
        print(f"✅ Docker agent run() completed in {execution_time:.2f}s")
        print(f"Result: {result}")
    
    @pytest.mark.asyncio
    async def test_sandbox_agent_run_method(self, simple_fullstack_project):
        """Test that SandboxExecutorAgent.run() method works correctly"""
        sandbox_agent = SandboxExecutorAgent(project_path=simple_fullstack_project)
        
        start_time = time.time()
        result = await sandbox_agent.run()
        execution_time = time.time() - start_time
        
        # Should be reasonably fast (may take longer for actual testing)
        assert execution_time < 60
        
        # Should return proper format
        assert isinstance(result, dict)
        assert "passed" in result
        assert "issues" in result
        assert "container_based" in result
        assert "language" in result
        assert "message" in result
        
        print(f"✅ Sandbox agent run() completed in {execution_time:.2f}s")
        print(f"Result: {result}")
    
    @pytest.mark.asyncio
    async def test_dependency_agent_run_method(self, simple_fullstack_project):
        """Test that DependencyVerifierAgent.run() method works correctly"""
        dependency_agent = DependencyVerifierAgent(
            project_path=simple_fullstack_project,
            session_state={}
        )
        
        start_time = time.time()
        result = await dependency_agent.run()
        execution_time = time.time() - start_time
        
        # Should be fast
        assert execution_time < 15
        
        # Should return proper format
        assert isinstance(result, dict)
        assert "passed" in result
        assert "issues" in result
        assert "container_based" in result
        assert "audit_tools_available" in result
        
        print(f"✅ Dependency agent run() completed in {execution_time:.2f}s")
        print(f"Result: {result}")
    
    def test_sre_lead_agent_coordination(self, simple_fullstack_project):
        """Test SRELeadAgent can coordinate the validation workflow"""
        session_state = {
            "project_path": str(simple_fullstack_project)
        }
        
        sre_lead = SRELeadAgent(
            project_path=simple_fullstack_project,
            session_state=session_state
        )
        
        # Test validation method
        modified_files = {
            "backend/main.py": "FastAPI code",
            "frontend/src/App.jsx": "React code"
        }
        
        start_time = time.time()
        result = sre_lead.validate_changes(simple_fullstack_project, modified_files)
        execution_time = time.time() - start_time
        
        # Should complete reasonably fast
        assert execution_time < 45
        
        # Should return comprehensive results
        assert isinstance(result, dict)
        assert "passed" in result
        assert "issues" in result
        assert "check_results" in result
        assert "summary" in result
        assert "docker_pipeline" in result
        
        # Check specific phases
        check_results = result["check_results"]
        assert "manifest_generation" in check_results
        assert "docker_configuration" in check_results
        assert "container_testing" in check_results
        assert "container_security" in check_results
        assert "version_control" in check_results
        
        print(f"✅ SRE Lead coordination completed in {execution_time:.2f}s")
        print(f"Summary: {result['summary']}")
    
    def test_deployment_readiness_focus(self, simple_fullstack_project):
        """Test that SRE team focuses on deployment readiness"""
        session_state = {
            "project_path": str(simple_fullstack_project)
        }
        
        sre_team = build_sre_team(
            project_path=simple_fullstack_project,
            session_state=session_state
        )
        
        result = sre_team.run_sync()
        
        # Should have deployment readiness info
        assert "deployment_ready" in result
        assert "docker_ready" in result
        
        # Summary should include operational score
        summary = result.get("summary", {})
        assert "operational_score" in summary
        
        # Docker pipeline info should be present
        docker_pipeline = result.get("docker_pipeline", {})
        assert "manifests_generated" in docker_pipeline
        assert "docker_configs_created" in docker_pipeline
        assert "container_tests_run" in docker_pipeline
        
        print(f"✅ Deployment readiness check completed")
        print(f"Docker ready: {result.get('docker_ready')}")
        print(f"Deployment ready: {result.get('deployment_ready')}")
    
    def test_error_handling_no_timeout(self, simple_fullstack_project):
        """Test error handling doesn't cause timeouts"""
        # Create invalid session state to test error handling
        session_state = {
            "project_path": "/nonexistent/path"
        }
        
        start_time = time.time()
        try:
            sre_team = build_sre_team(
                project_path=Path("/nonexistent/path"),
                session_state=session_state
            )
            result = sre_team.run_sync()
            execution_time = time.time() - start_time
            
            # Even with errors, should not hang
            assert execution_time < 20
            
            # Should return error result, not crash
            assert isinstance(result, dict)
            assert "passed" in result
            # Errors should be reported, not cause hangs
            assert result["passed"] is False
            
        except Exception as e:
            execution_time = time.time() - start_time
            # Even exceptions should happen quickly
            assert execution_time < 20
            print(f"Expected error handled in {execution_time:.2f}s: {e}")
    
    def test_docker_configs_are_functional(self, simple_fullstack_project):
        """Test that generated Docker configs would actually work"""
        docker_agent = DockerConfigAgent(project_path=simple_fullstack_project)
        
        architectural_context = {
            "system_type": "fullstack_web_app",
            "modules": {
                "backend": {"languages": ["python"]},
                "frontend": {"languages": ["javascript"]}
            }
        }
        
        result = docker_agent.generate_docker_configs(
            simple_fullstack_project, 
            architectural_context
        )
        
        # Check files were created
        configs_created = result.get("configs_created", [])
        assert len(configs_created) > 0
        
        # Check docker-compose.yml was created for fullstack
        assert "docker-compose.yml" in configs_created
        
        # Verify docker-compose.yml has essential services
        compose_file = simple_fullstack_project / "docker-compose.yml"
        if compose_file.exists():
            content = compose_file.read_text()
            assert "backend:" in content
            assert "frontend:" in content
            assert "ports:" in content
            print("✅ Docker configs appear functional for deployment")


class TestSRETeamPerformance:
    """Performance-focused tests to ensure no hangs or excessive API calls"""
    
    @pytest.fixture
    def minimal_project(self):
        """Create minimal project for performance testing"""
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)
        
        # Just a simple Python file
        (project_path / "main.py").write_text("print('Hello World')")
        
        yield project_path
        shutil.rmtree(temp_dir)
    
    def test_sre_team_under_time_limit(self, minimal_project):
        """Test SRE team completes within reasonable time limits"""
        session_state = {"project_path": str(minimal_project)}
        
        # Set strict time limit to catch hangs
        MAX_EXECUTION_TIME = 30  # 30 seconds max
        
        start_time = time.time()
        sre_team = build_sre_team(
            project_path=minimal_project,
            session_state=session_state
        )
        result = sre_team.run_sync()
        execution_time = time.time() - start_time
        
        assert execution_time < MAX_EXECUTION_TIME
        assert isinstance(result, dict)
        print(f"✅ SRE team completed minimal project in {execution_time:.2f}s")
    
    def test_concurrent_agent_runs_no_deadlock(self, minimal_project):
        """Test that multiple agent runs don't cause deadlocks"""
        async def run_multiple_agents():
            docker_agent = DockerConfigAgent(project_path=minimal_project)
            sandbox_agent = SandboxExecutorAgent(project_path=minimal_project)
            dependency_agent = DependencyVerifierAgent(
                project_path=minimal_project,
                session_state={}
            )
            
            # Run agents concurrently
            results = await asyncio.gather(
                docker_agent.run(),
                sandbox_agent.run(), 
                dependency_agent.run(),
                return_exceptions=True
            )
            
            return results
        
        start_time = time.time()
        results = asyncio.run(run_multiple_agents())
        execution_time = time.time() - start_time
        
        # Should complete without deadlocks
        assert execution_time < 45
        assert len(results) == 3
        
        # All should return dict results (or exceptions, but not hangs)
        for result in results:
            assert isinstance(result, (dict, Exception))
        
        print(f"✅ Concurrent agent runs completed in {execution_time:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])