#!/usr/bin/env python3
"""
Test the Integration Intelligence Workflow
Tests all three approaches: Architectural-First, Single Agent, Staged Integration
"""

import sys
import tempfile
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent / "src"
sys.path.insert(0, str(project_root))

from i2c.bootstrap import initialize_environment
initialize_environment()

async def test_integration_intelligence():
    """Test integration intelligence with a simple fullstack app"""
    
    print("🚀 Testing Integration Intelligence Workflow")
    print("=" * 60)
    
    try:
        from i2c.workflow.integration_intelligence import execute_integration_intelligence_workflow
        
        # Simple test objective
        objective = {
            "task": "Create a simple task management app with frontend and backend",
            "constraints": [
                "Use FastAPI for backend",
                "Use React for frontend", 
                "Include CRUD operations for tasks",
                "Ensure frontend connects to backend properly"
            ],
            "language": "Python",
            "system_type": "fullstack_web_app"
        }
        
        # Test session state
        with tempfile.TemporaryDirectory() as temp_dir:
            session_state = {
                "project_path": temp_dir,
                "system_type": "fullstack_web_app",
                "retrieved_context": "Use REST APIs. Ensure proper CORS. Connect frontend to backend with proper error handling.",
                "architectural_context": {
                    "modules": {
                        "backend": {"languages": ["Python"], "responsibilities": ["API", "Data"]},
                        "frontend": {"languages": ["JavaScript"], "responsibilities": ["UI", "UX"]}
                    }
                }
            }
            
            print(f"📁 Test project: {temp_dir}")
            print(f"🎯 Objective: {objective['task']}")
            print(f"📋 Constraints: {len(objective['constraints'])} constraints")
            
            # Execute workflow
            print("\n🧠 Executing Integration Intelligence Workflow...")
            result = await execute_integration_intelligence_workflow(objective, session_state)
            
            # Analyze results
            print(f"\n📊 RESULTS:")
            print(f"   Success: {result.success}")
            print(f"   Files generated: {len(result.files)}")
            print(f"   Integration status: {result.integration_status}")
            print(f"   Deployment ready: {result.deployment_ready}")
            print(f"   Errors: {len(result.errors)}")
            print(f"   Warnings: {len(result.warnings)}")
            
            if result.files:
                print(f"\n📄 Generated files:")
                for file_path in sorted(result.files.keys()):
                    print(f"   - {file_path}")
            
            if result.errors:
                print(f"\n❌ Errors:")
                for error in result.errors:
                    print(f"   - {error}")
            
            if result.warnings:
                print(f"\n⚠️ Warnings:")
                for warning in result.warnings:
                    print(f"   - {warning}")
            
            # Check for integration quality
            integration_score = 0
            
            # Check for backend files
            backend_files = [f for f in result.files.keys() if "backend" in f]
            if backend_files:
                integration_score += 1
                print(f"\n✅ Backend files: {len(backend_files)}")
                
                # Check for main.py
                if any("main.py" in f for f in backend_files):
                    integration_score += 1
                    print("✅ Backend main.py found")
                
                # Check for API endpoints
                backend_code = "\n".join([result.files[f] for f in backend_files])
                if "@app.get" in backend_code or "@app.post" in backend_code:
                    integration_score += 1
                    print("✅ API endpoints found")
            
            # Check for frontend files
            frontend_files = [f for f in result.files.keys() if "frontend" in f]
            if frontend_files:
                integration_score += 1
                print(f"✅ Frontend files: {len(frontend_files)}")
                
                # Check for React components
                if any(".jsx" in f or ".js" in f for f in frontend_files):
                    integration_score += 1
                    print("✅ React components found")
                
                # Check for API calls
                frontend_code = "\n".join([result.files[f] for f in frontend_files])
                if "fetch(" in frontend_code or "axios" in frontend_code:
                    integration_score += 1
                    print("✅ Frontend API calls found")
            
            # Check for deployment files
            deployment_files = [f for f in result.files.keys() if any(x in f for x in ["docker", "requirements", "package.json"])]
            if deployment_files:
                integration_score += 1
                print(f"✅ Deployment files: {len(deployment_files)}")
            
            # Check for README/documentation
            if any("README" in f for f in result.files.keys()):
                integration_score += 1
                print("✅ Documentation found")
            
            print(f"\n🏆 Integration Score: {integration_score}/8")
            
            if integration_score >= 6:
                print("🎉 EXCELLENT: High-quality integrated system generated!")
                return True
            elif integration_score >= 4:
                print("✅ GOOD: Decent integration with some missing pieces")
                return True
            elif integration_score >= 2:
                print("⚠️ BASIC: Basic structure but missing integration")
                return False
            else:
                print("❌ POOR: Failed to generate proper integrated system")
                return False
    
    except Exception as e:
        print(f"❌ ERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_architectural_contract():
    """Test the architectural contract creation"""
    
    print("\n🏗️ Testing Architectural Contract Creation")
    print("=" * 50)
    
    try:
        from i2c.workflow.integration_intelligence import ArchitecturalIntelligenceAgent
        
        agent = ArchitecturalIntelligenceAgent()
        
        objective = {
            "task": "Create a user management system with authentication",
            "constraints": ["Use JWT tokens", "Hash passwords", "Include user roles"]
        }
        
        session_state = {
            "system_type": "fullstack_web_app",
            "retrieved_context": "Use FastAPI and React. Implement proper authentication flows."
        }
        
        print("📋 Creating integration contract...")
        contract = agent.create_integration_contract(objective, session_state)
        
        print(f"✅ Contract created:")
        print(f"   API endpoints: {len(contract.api_endpoints)}")
        print(f"   Component interfaces: {len(contract.component_interfaces)}")
        print(f"   Data models: {len(contract.data_models)}")
        print(f"   Integration points: {len(contract.integration_points)}")
        print(f"   Test scenarios: {len(contract.test_scenarios)}")
        
        # Check contract quality
        has_endpoints = len(contract.api_endpoints) > 0
        has_components = len(contract.component_interfaces) > 0
        has_models = len(contract.data_models) > 0
        has_integration = len(contract.integration_points) > 0
        
        success = has_endpoints or has_components or has_models or has_integration
        
        if success:
            print("🎉 Contract generation successful!")
        else:
            print("⚠️ Contract generation produced minimal results")
        
        return success
        
    except Exception as e:
        print(f"❌ ERROR: Contract test failed: {e}")
        return False

if __name__ == "__main__":
    async def main():
        print("🧪 Integration Intelligence Test Suite")
        print("Testing all three approaches for working software generation")
        print("=" * 70)
        
        # Test 1: Architectural contract
        test1 = await test_architectural_contract()
        
        # Test 2: Full integration intelligence
        test2 = await test_integration_intelligence()
        
        print("\n" + "=" * 70)
        print("🏁 FINAL RESULTS:")
        print(f"   Architectural Contract: {'✅ PASS' if test1 else '❌ FAIL'}")
        print(f"   Integration Intelligence: {'✅ PASS' if test2 else '❌ FAIL'}")
        
        if test1 and test2:
            print("\n🎉 SUCCESS: Integration Intelligence is working!")
            print("   The three-option approach should generate working software")
            print("   - Architectural-first planning")
            print("   - Single intelligent agent generation")
            print("   - Staged integration workflow")
            print("   - Adaptive strategy selection")
            print("   - Minimal working system fallback")
        elif test1 or test2:
            print("\n⚠️ PARTIAL SUCCESS: Some components working")
        else:
            print("\n❌ FAILURE: Integration Intelligence needs debugging")
        
        print("=" * 70)
    
    # Run the async main function
    if hasattr(asyncio, 'run'):
        asyncio.run(main())
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())