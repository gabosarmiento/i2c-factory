#!/usr/bin/env python3
from src.i2c.bootstrap import initialize_environment
initialize_environment()

"""
Test lean SRE agents individually to verify they work
"""

import asyncio
import tempfile
import sys
from pathlib import Path

# Add path for direct imports
sys.path.append('src/i2c/agents/sre_team')

def test_docker_agent():
    """Test DockerConfigAgent"""
    print("Testing DockerConfigAgent...")
    
    try:
        from docker import DockerConfigAgent
        
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)
        
        # Create some project files
        (project_path / "backend").mkdir()
        (project_path / "frontend").mkdir()
        (project_path / "backend" / "main.py").write_text("# FastAPI app")
        (project_path / "frontend" / "App.jsx").write_text("// React app")
        
        agent = DockerConfigAgent(project_path=project_path)
        result = asyncio.run(agent.run())
        
        print(f"   ✅ Docker agent passed: {result['passed']}")
        print(f"   Files created: {result['files_created']}")
        print(f"   System type: {result['system_type']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Docker agent failed: {e}")
        return False

def test_sandbox_agent():
    """Test SandboxExecutorAgent"""
    print("Testing SandboxExecutorAgent...")
    
    try:
        from sandbox import SandboxExecutorAgent
        
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)
        (project_path / "test.py").write_text("def test(): return True")
        
        agent = SandboxExecutorAgent(project_path=project_path)
        result = asyncio.run(agent.run())
        
        print(f"   ✅ Sandbox agent passed: {result['passed']}")
        print(f"   Container based: {result['container_based']}")
        print(f"   Language: {result['language']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Sandbox agent failed: {e}")
        return False

def test_dependency_agent():
    """Test DependencyVerifierAgent"""
    print("Testing DependencyVerifierAgent...")
    
    try:
        from dependency import DependencyVerifierAgent
        
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)
        (project_path / "main.py").write_text("import requests")
        
        agent = DependencyVerifierAgent(project_path=project_path)
        result = asyncio.run(agent.run())
        
        print(f"   ✅ Dependency agent passed: {result['passed']}")
        print(f"   Issues found: {len(result['issues'])}")
        print(f"   Container based: {result['container_based']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Dependency agent failed: {e}")
        return False

def test_all_agents_together():
    """Test all agents working together"""
    print("Testing all agents together...")
    
    try:
        from docker import DockerConfigAgent
        from sandbox import SandboxExecutorAgent
        from dependency import DependencyVerifierAgent
        
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)
        
        # Create fullstack project
        (project_path / "backend").mkdir()
        (project_path / "frontend").mkdir()
        (project_path / "backend" / "main.py").write_text("""
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
""")
        (project_path / "frontend" / "App.jsx").write_text("""
import React from 'react';
function App() {
    return <div>Hello World</div>;
}
export default App;
""")
        
        # Test all agents
        agents = [
            DockerConfigAgent(project_path=project_path),
            SandboxExecutorAgent(project_path=project_path),
            DependencyVerifierAgent(project_path=project_path)
        ]
        
        async def run_all():
            results = []
            for agent in agents:
                result = await agent.run()
                results.append(result)
            return results
        
        results = asyncio.run(run_all())
        
        all_passed = all(r['passed'] for r in results)
        print(f"   ✅ All agents completed. Overall passed: {all_passed}")
        
        for i, result in enumerate(results):
            print(f"   Agent {i+1}: passed={result['passed']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Combined test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing lean SRE agents...")
    
    results = []
    results.append(test_docker_agent())
    results.append(test_sandbox_agent())
    results.append(test_dependency_agent())
    results.append(test_all_agents_together())
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All SRE agents work correctly!")
    else:
        print("❌ Some agents need fixes")