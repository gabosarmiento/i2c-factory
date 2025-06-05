#!/usr/bin/env python3
from src.i2c.bootstrap import initialize_environment
initialize_environment()

"""
Quick test to isolate SRE team hanging issue
"""

import asyncio
import tempfile
from pathlib import Path
import time

try:
    from src.i2c.agents.sre_team.docker import DockerConfigAgent
    from src.i2c.agents.sre_team.sandbox import SandboxExecutorAgent
    from src.i2c.agents.sre_team.dependency import DependencyVerifierAgent
    
    def test_individual_agents():
        """Test each agent individually"""
        
        # Create temp project
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)
        (project_path / "main.py").write_text("print('hello')")
        
        print("Testing individual agents...")
        
        # Test Docker agent
        print("1. Testing DockerConfigAgent...")
        start = time.time()
        docker_agent = DockerConfigAgent(project_path=project_path)
        
        async def test_docker():
            return await docker_agent.run()
        
        try:
            result = asyncio.run(test_docker())
            print(f"   ✅ Docker agent completed in {time.time() - start:.2f}s")
            print(f"   Result: {result}")
        except Exception as e:
            print(f"   ❌ Docker agent failed: {e}")
        
        # Test Sandbox agent
        print("2. Testing SandboxExecutorAgent...")
        start = time.time()
        sandbox_agent = SandboxExecutorAgent(project_path=project_path)
        
        async def test_sandbox():
            return await sandbox_agent.run()
        
        try:
            result = asyncio.run(test_sandbox())
            print(f"   ✅ Sandbox agent completed in {time.time() - start:.2f}s")
            print(f"   Result: {result}")
        except Exception as e:
            print(f"   ❌ Sandbox agent failed: {e}")
        
        # Test Dependency agent
        print("3. Testing DependencyVerifierAgent...")
        start = time.time()
        dependency_agent = DependencyVerifierAgent(project_path=project_path, session_state={})
        
        async def test_dependency():
            return await dependency_agent.run()
        
        try:
            result = asyncio.run(test_dependency())
            print(f"   ✅ Dependency agent completed in {time.time() - start:.2f}s")
            print(f"   Result: {result}")
        except Exception as e:
            print(f"   ❌ Dependency agent failed: {e}")
        
        print("All individual agent tests completed!")
    
    if __name__ == "__main__":
        test_individual_agents()
        
except ImportError as e:
    print(f"Import failed: {e}")
    print("Run from project root: python test_sre_quick.py")