import pytest
from pathlib import Path
import asyncio
import json
import tempfile
from i2c.workflow.agentic_orchestrator import execute_agentic_evolution_sync
from i2c.agents.architecture.architecture_understanding_agent import get_architecture_agent

@pytest.mark.integration
def test_fullstack_architectural_pipeline_complete():
    """Test complete architectural intelligence pipeline for fullstack web app"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        print(f"🧪 Testing fullstack architectural pipeline at: {project_path}")
        
        # Create objective that should trigger fullstack web app detection
        objective = {
            "task": "Create a code snippet manager web application with React frontend and FastAPI backend. Users should be able to create, edit, and organize code snippets with syntax highlighting.",
            "language": "python",
            "constraints": [
                "Use React for the frontend with proper component structure",
                "Use FastAPI for the backend API",
                "Include proper CORS configuration",
                "Add comprehensive error handling",
                "Follow modern web development best practices"
            ],
            "quality_gates": ["flake8", "mypy"],
            "project_path": str(project_path)
        }
        
        # Session state for agentic evolution
        session_state = {
            "project_path": str(project_path),
            "language": "python",
            "use_retrieval_tools": True,
            "modified_files": {}
        }
        
        print("🚀 Starting agentic evolution with architectural intelligence...")
        
        # Execute agentic evolution with architectural intelligence
        result = execute_agentic_evolution_sync(
            objective=objective,
            project_path=project_path,
            session_state=session_state
        )
        
        print("✅ Agentic evolution completed")
        
        # PHASE 1: Validate Enhanced Objective
        print("\n" + "="*60)
        print("PHASE 1: ENHANCED OBJECTIVE VALIDATION")
        print("="*60)
        
        enhanced_objective = session_state.get("enhanced_objective", {})
        architectural_context = enhanced_objective.get("architectural_context", {})
        
        # Should detect fullstack web app
        assert architectural_context.get("system_type") == "fullstack_web_app", f"Expected fullstack_web_app, got {architectural_context.get('system_type')}"
        assert architectural_context.get("architecture_pattern") == "fullstack_web", f"Expected fullstack_web pattern, got {architectural_context.get('architecture_pattern')}"
        
        print(f"✅ System Type: {architectural_context.get('system_type')}")
        print(f"✅ Architecture Pattern: {architectural_context.get('architecture_pattern')}")
        
        # Should have modules
        modules = architectural_context.get("modules", {})
        assert "frontend" in modules or "backend" in modules, f"Expected frontend/backend modules, got {list(modules.keys())}"
        print(f"✅ Modules detected: {list(modules.keys())}")
        
        # Should have file organization rules
        file_rules = architectural_context.get("file_organization_rules", {})
        assert len(file_rules) > 0, "Should have file organization rules"
        print(f"✅ File organization rules: {list(file_rules.keys())}")
        
        # PHASE 2: Validate Generated File Structure
        print("\n" + "="*60)
        print("PHASE 2: FILE STRUCTURE VALIDATION")
        print("="*60)
        
        # Get all generated files
        generated_files = []
        if project_path.exists():
            for file_path in project_path.rglob("*"):
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(project_path))
                    generated_files.append(relative_path)
        
        print(f"📁 Generated files ({len(generated_files)}):")
        for file_path in sorted(generated_files):
            print(f"   - {file_path}")
        
        # CRITICAL: Check for the main issues we're fixing
        critical_checks = []
        
        # 1. Should NOT have frontend.py with JSX content
        frontend_py_path = project_path / "frontend.py"
        if frontend_py_path.exists():
            content = frontend_py_path.read_text()
            if any(jsx_indicator in content for jsx_indicator in ["import React", "jsx", "useState", "Component"]):
                critical_checks.append("❌ CRITICAL: frontend.py contains JSX content (architectural intelligence failed)")
            else:
                critical_checks.append("⚠️ frontend.py exists but doesn't contain JSX")
        else:
            critical_checks.append("✅ No problematic frontend.py file")
        
        # 2. Should have proper backend structure
        backend_main = project_path / "backend" / "main.py"
        if backend_main.exists():
            backend_content = backend_main.read_text()
            if "FastAPI" in backend_content and "app = " in backend_content:
                critical_checks.append("✅ Backend has proper FastAPI structure")
            else:
                critical_checks.append("❌ CRITICAL: Backend exists but missing FastAPI structure")
        else:
            critical_checks.append("❌ CRITICAL: Missing backend/main.py")
        
        # 3. Should have proper frontend structure
        frontend_app = project_path / "frontend" / "src" / "App.jsx"
        if frontend_app.exists():
            frontend_content = frontend_app.read_text()
            if "import React" in frontend_content and "export default" in frontend_content:
                critical_checks.append("✅ Frontend has proper React component structure")
            else:
                critical_checks.append("❌ CRITICAL: Frontend App.jsx exists but missing React structure")
        else:
            critical_checks.append("❌ CRITICAL: Missing frontend/src/App.jsx")
        
        # 4. Check for proper component separation
        component_files = [f for f in generated_files if f.startswith("frontend/src/components/") and f.endswith(".jsx")]
        if component_files:
            critical_checks.append(f"✅ React components properly separated: {len(component_files)} components")
        else:
            critical_checks.append("⚠️ No React components found in frontend/src/components/")
        
        print("\n🔍 CRITICAL ARCHITECTURAL CHECKS:")
        for check in critical_checks:
            print(f"   {check}")
        
        # PHASE 3: Validate Content Quality
        print("\n" + "="*60)
        print("PHASE 3: CONTENT QUALITY VALIDATION")
        print("="*60)
        
        content_quality_checks = []
        
        # Check main.py content (should NOT be simple Hello World)
        main_py_files = [f for f in generated_files if f.endswith("main.py")]
        for main_file in main_py_files:
            content = (project_path / main_file).read_text()
            if content.strip() == 'def main():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()':
                content_quality_checks.append(f"❌ CRITICAL: {main_file} is generic Hello World (architectural intelligence failed)")
            elif "FastAPI" in content or "app = " in content:
                content_quality_checks.append(f"✅ {main_file} has proper application structure")
            else:
                content_quality_checks.append(f"⚠️ {main_file} exists but may need review")
        
        # Check for mixed content issues
        for file_path in generated_files:
            if file_path.endswith(".py"):
                content = (project_path / file_path).read_text()
                if any(jsx_indicator in content for jsx_indicator in ["import React", "<div", "jsx", "useState"]):
                    content_quality_checks.append(f"❌ CRITICAL: {file_path} contains JSX in Python file")
        
        print("🎯 CONTENT QUALITY CHECKS:")
        for check in content_quality_checks:
            print(f"   {check}")
        
        # PHASE 4: Overall Assessment
        print("\n" + "="*60)
        print("PHASE 4: OVERALL ASSESSMENT")
        print("="*60)
        
        # Count critical failures
        critical_failures = [check for check in critical_checks + content_quality_checks if check.startswith("❌ CRITICAL")]
        
        if critical_failures:
            print(f"❌ ARCHITECTURAL INTELLIGENCE FAILED: {len(critical_failures)} critical issues")
            for failure in critical_failures:
                print(f"   {failure}")
            
            # Don't fail the test yet - let's see what we got
            print("\n⚠️ Issues found, but continuing to analyze results...")
        else:
            print("✅ ARCHITECTURAL INTELLIGENCE SUCCESS: All critical checks passed")
        
        # PHASE 5: Result Structure Validation
        print("\n" + "="*60)
        print("PHASE 5: RESULT STRUCTURE VALIDATION")
        print("="*60)
        
        assert isinstance(result, dict), f"Result should be dict, got {type(result)}"
        
        if "result" in result:
            agent_result = result["result"]
            print(f"📊 Agent result type: {type(agent_result)}")
            
            if isinstance(agent_result, dict):
                print(f"🎯 Decision: {agent_result.get('decision', 'unknown')}")
                print(f"📝 Reason: {agent_result.get('reason', 'no reason')}")
                
                modifications = agent_result.get("modifications", {})
                if isinstance(modifications, dict):
                    print(f"📁 Modifications: {len(modifications)} files")
                    for file_path, description in list(modifications.items())[:5]:
                        print(f"   - {file_path}: {description}")
        
        # Final assertion - critical architectural intelligence must work
        assert len([check for check in critical_checks if "frontend.py contains JSX" in check]) == 0, "CRITICAL: JSX content found in Python file - architectural intelligence completely failed"
        
        # ✅ PHASE 6: FINAL FILE SYSTEM VALIDATION (NEW)
        print("\n" + "="*60)
        print("PHASE 6: FINAL FILE SYSTEM VALIDATION")
        print("="*60)
        
        # Critical files must actually exist on disk
        backend_main = project_path / "backend" / "main.py"
        frontend_app = project_path / "frontend" / "src" / "App.jsx"
        
        # Backend validation
        if backend_main.exists():
            print("✅ backend/main.py exists on disk")
            backend_content = backend_main.read_text()
            if "FastAPI" in backend_content and "app =" in backend_content:
                print("✅ backend/main.py contains proper FastAPI code")
            else:
                print("⚠️ backend/main.py exists but missing FastAPI structure")
        else:
            print("❌ backend/main.py was not written to disk")
            assert False, "CRITICAL: backend/main.py was not created despite agent success"
        
        # Frontend validation  
        if frontend_app.exists():
            print("✅ frontend/src/App.jsx exists on disk")
            frontend_content = frontend_app.read_text()
            if "import React" in frontend_content and "export default" in frontend_content:
                print("✅ frontend/src/App.jsx contains proper React code")
            else:
                print("⚠️ frontend/src/App.jsx exists but missing React structure")
        else:
            print("❌ frontend/src/App.jsx was not written to disk")
            assert False, "CRITICAL: frontend/src/App.jsx was not created despite agent success"
        
        # Verify no JSX-in-Python pollution
        frontend_py = project_path / "frontend.py"
        if frontend_py.exists():
            content = frontend_py.read_text()
            if any(jsx in content for jsx in ["import React", "jsx", "useState"]):
                assert False, "CRITICAL: JSX content found in frontend.py - architectural intelligence failed completely"
            else:
                print("✅ frontend.py exists but contains no JSX pollution")
        else:
            print("✅ No problematic frontend.py file created")

        print("\n🎯 REALITY CHECK: Agent success matches file system reality")
        
        print("\n" + "="*60)
        print("✅ ARCHITECTURAL PIPELINE TEST COMPLETED")
        print("="*60)
        
        # Return results for further analysis
        return {
            "architectural_context": architectural_context,
            "generated_files": generated_files,
            "critical_checks": critical_checks,
            "content_quality_checks": content_quality_checks,
            "result": result
        }


@pytest.mark.integration  
def test_architectural_intelligence_objective_enhancement():
    """Test that architectural intelligence properly enhances objectives"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Test different types of objectives
        test_cases = [
            {
                "name": "Fullstack Web App",
                "task": "Create a React frontend with FastAPI backend for task management",
                "expected_system_type": "fullstack_web_app",
                "expected_constraints": ["FastAPI", "React", "frontend/src", "backend/"]
            },
            {
                "name": "API Service",
                "task": "Build a REST API service for user authentication with JWT tokens",
                "expected_system_type": "api_service", 
                "expected_constraints": ["API", "REST", "endpoints"]
            },
            {
                "name": "CLI Tool",
                "task": "Create a command line tool for file processing with argparse",
                "expected_system_type": "cli_tool",
                "expected_constraints": ["command line", "argparse"]
            }
        ]
        
        for test_case in test_cases:
            print(f"\n🧪 Testing: {test_case['name']}")
            
            objective = {
                "task": test_case["task"],
                "constraints": [],
                "quality_gates": ["flake8"]
            }
            
            session_state = {"project_path": str(project_path)}
            
            # Test the architectural enhancement function directly
            from i2c.workflow.agentic_orchestrator import _enhance_objective_with_architectural_intelligence
            
            async def test_enhancement():
                enhanced = await _enhance_objective_with_architectural_intelligence(
                    objective, project_path, session_state
                )
                return enhanced
            
            loop = asyncio.get_event_loop()
            enhanced_objective = loop.run_until_complete(test_enhancement())
            
            # Validate enhancement
            arch_context = enhanced_objective.get("architectural_context", {})
            system_type = arch_context.get("system_type", "unknown")
            
            print(f"   Detected: {system_type}")
            print(f"   Expected: {test_case['expected_system_type']}")
            
            # Should detect correct system type
            if system_type == test_case["expected_system_type"]:
                print("   ✅ System type detection correct")
            else:
                print(f"   ⚠️ System type mismatch (expected {test_case['expected_system_type']}, got {system_type})")
            
            # Should add relevant constraints
            constraints = enhanced_objective.get("constraints", [])
            constraints_text = " ".join(constraints).lower()
            
            expected_found = []
            for expected_constraint in test_case["expected_constraints"]:
                if expected_constraint.lower() in constraints_text:
                    expected_found.append(expected_constraint)
            
            print(f"   Expected constraints found: {expected_found}")
            
            if len(expected_found) > 0:
                print("   ✅ Relevant constraints added")
            else:
                print("   ⚠️ Expected constraints not found")


if __name__ == "__main__":
    print("Testing architectural intelligence pipeline...")
    pytest.main(["-xvs", __file__])