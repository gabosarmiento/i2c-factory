#!/usr/bin/env python3
"""
Test Docker build fixes for npm and pip-audit issues
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

def test_docker_build_fixes():
    """Test the Docker build configuration improvements"""
    
    print("🧪 Testing Docker build fixes...")
    
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
                "backend": {"languages": ["python"], "framework": "fastapi"},
                "frontend": {"languages": ["javascript"], "framework": "react"}
            }
        }
        
        # Create Docker config agent
        docker_agent = DockerConfigAgent(project_path)
        
        # Generate Docker configs
        result = docker_agent.generate_docker_configs(project_path, architectural_context)
        
        print(f"✅ Generated {len(result['configs_created'])} Docker config files")
        
        # Test 1: Check frontend Dockerfile npm command
        frontend_dockerfile = frontend_dir / "Dockerfile"
        if frontend_dockerfile.exists():
            dockerfile_content = frontend_dockerfile.read_text()
            
            # Should use 'npm ci' instead of 'npm ci --only=production'
            if "npm ci --only=production" in dockerfile_content:
                print("❌ Frontend Dockerfile still uses --only=production (will fail build)")
                return False
            elif "RUN npm ci" in dockerfile_content and "npm ci --only=production" not in dockerfile_content:
                print("✅ Frontend Dockerfile uses 'npm ci' without --only=production")
            else:
                print("❌ Frontend Dockerfile npm command not found")
                return False
            
            # Should have build step after dependencies
            if "RUN npm run build" in dockerfile_content:
                print("✅ Frontend Dockerfile includes build step")
            else:
                print("❌ Frontend Dockerfile missing build step")
                return False
        else:
            print("❌ Frontend Dockerfile not generated")
            return False
        
        # Test 2: Check backend Dockerfile for pip-audit and curl
        backend_dockerfile = backend_dir / "Dockerfile"
        if backend_dockerfile.exists():
            dockerfile_content = backend_dockerfile.read_text()
            
            # Should install pip-audit
            if "pip install --no-cache-dir pip-audit" in dockerfile_content:
                print("✅ Backend Dockerfile installs pip-audit for security scanning")
            else:
                print("❌ Backend Dockerfile missing pip-audit installation")
                return False
            
            # Should install curl for health checks
            if "curl" in dockerfile_content and "apt-get install" in dockerfile_content:
                print("✅ Backend Dockerfile installs curl for health checks")
            else:
                print("❌ Backend Dockerfile missing curl installation")
                return False
            
            # Should have health check
            if "HEALTHCHECK" in dockerfile_content and "curl -f" in dockerfile_content:
                print("✅ Backend Dockerfile includes proper health check")
            else:
                print("❌ Backend Dockerfile missing or invalid health check")
                return False
        else:
            print("❌ Backend Dockerfile not generated")
            return False
        
        # Test 3: Check docker-compose structure
        compose_file = project_path / "docker-compose.yml"
        if compose_file.exists():
            compose_content = compose_file.read_text()
            
            # Should not have version (fixed in previous iteration)
            if "version:" not in compose_content:
                print("✅ docker-compose.yml has no obsolete version attribute")
            else:
                print("❌ docker-compose.yml still has obsolete version attribute")
                return False
            
            # Should use dynamic port allocation for database
            if '"0:5432"' in compose_content:
                print("✅ docker-compose.yml uses dynamic port allocation for database")
            else:
                print("⚠️ docker-compose.yml may not use dynamic port allocation")
        
        print("✅ All Docker build fixes are working correctly!")
        return True

def test_dockerfile_logical_flow():
    """Test that Dockerfiles have logical build flow"""
    
    print("\n🧪 Testing Dockerfile logical flow...")
    
    from i2c.agents.sre_team.docker import DockerConfigAgent
    
    docker_agent = DockerConfigAgent()
    
    # Test frontend Dockerfile flow
    frontend_dockerfile = docker_agent._generate_frontend_dockerfile(
        Path("."), {"languages": ["javascript"]}
    )
    
    lines = frontend_dockerfile.split('\n')
    dockerfile_steps = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
    
    # Check logical order
    copy_package_idx = -1
    npm_ci_idx = -1
    copy_source_idx = -1
    npm_build_idx = -1
    
    for i, step in enumerate(dockerfile_steps):
        if "COPY package" in step:
            copy_package_idx = i
        elif "RUN npm ci" in step:
            npm_ci_idx = i
        elif "COPY . ." in step:
            copy_source_idx = i
        elif "RUN npm run build" in step:
            npm_build_idx = i
    
    # Validate order
    if copy_package_idx < npm_ci_idx < copy_source_idx < npm_build_idx:
        print("✅ Frontend Dockerfile has correct build order: package.json → npm ci → source → build")
    else:
        print("❌ Frontend Dockerfile has incorrect build order")
        print(f"   Order: copy_package({copy_package_idx}) → npm_ci({npm_ci_idx}) → copy_source({copy_source_idx}) → npm_build({npm_build_idx})")
        return False
    
    # Test backend Dockerfile flow
    backend_dockerfile = docker_agent._generate_backend_dockerfile(
        Path("."), {"languages": ["python"]}
    )
    
    lines = backend_dockerfile.split('\n')
    dockerfile_steps = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
    
    # Check for security tools after main dependencies
    pip_install_idx = -1
    pip_audit_idx = -1
    
    for i, step in enumerate(dockerfile_steps):
        if "pip install --no-cache-dir -r requirements.txt" in step:
            pip_install_idx = i
        elif "pip install --no-cache-dir pip-audit" in step:
            pip_audit_idx = i
    
    if pip_install_idx < pip_audit_idx:
        print("✅ Backend Dockerfile installs pip-audit after main dependencies")
    else:
        print("❌ Backend Dockerfile pip-audit installation order incorrect")
        return False
    
    print("✅ Dockerfile logical flows are correct!")
    return True

if __name__ == "__main__":
    print("🔧 Docker Build Fixes Validation Test")
    print("=" * 50)
    
    # Run the tests
    build_fixes_success = test_docker_build_fixes()
    logical_flow_success = test_dockerfile_logical_flow()
    
    print("\n" + "=" * 50)
    print("📋 Final Results:")
    print(f"  - Docker Build Fixes: {'✅ PASSED' if build_fixes_success else '❌ FAILED'}")
    print(f"  - Dockerfile Flow: {'✅ PASSED' if logical_flow_success else '❌ FAILED'}")
    
    overall_success = build_fixes_success and logical_flow_success
    print(f"  - Overall: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n🎉 Docker build issues are resolved!")
        print("   Frontend npm builds should work and security scanning should succeed.")
    else:
        print("\n⚠️  Some issues detected. Check the test output above.")
    
    sys.exit(0 if overall_success else 1)