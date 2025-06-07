#!/usr/bin/env python3
"""
Test script to verify architectural intelligence fixes
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from i2c.bootstrap import initialize_environment
initialize_environment()

from i2c.workflow.agentic_orchestrator import _apply_modifications_if_any
from i2c.agents.core_agents import get_rag_enabled_agent

def test_language_constraint_enforcement():
    """Test that language constraints are enforced based on file extensions"""
    print("🧪 Testing language constraint enforcement...")
    
    # Create test session_state with architectural context
    session_state = {
        'language': 'python',
        'system_type': 'fullstack_web_app',
        'architectural_context': {
            'modules': {
                'backend': {
                    'responsibilities': ['REST API endpoints', 'business logic'],
                    'languages': ['python']
                },
                'frontend': {
                    'responsibilities': ['React components', 'user interface'],
                    'languages': ['javascript', 'jsx']
                }
            }
        },
        'current_structured_goal': {
            'constraints': [
                'Backend files (.py) must contain ONLY Python code',
                'Frontend files (.jsx) must contain ONLY JavaScript/React code'
            ]
        }
    }
    
    # Create temporary test directory
    test_dir = Path("/tmp/test_arch_fixes")
    test_dir.mkdir(exist_ok=True)
    
    # Create a test Python file with some content
    backend_file = test_dir / "backend" / "test_tool.py"
    backend_file.parent.mkdir(exist_ok=True)
    backend_file.write_text("""
# Original Python file
def test_function():
    return "Hello World"
""")
    
    # Test modifications that should enforce Python syntax
    test_modifications = {
        "backend/test_tool.py": "Add a new function that returns user data"
    }
    
    # Apply modifications with our enhanced function
    try:
        _apply_modifications_if_any(
            {"modifications": test_modifications}, 
            test_dir, 
            session_state
        )
        
        # Read the result
        modified_content = backend_file.read_text()
        print(f"📄 Modified content preview:\n{modified_content[:200]}...")
        
        # Check if it contains Python patterns and no JavaScript patterns
        has_python_patterns = any(pattern in modified_content.lower() for pattern in [
            'def ', 'import ', 'return', 'class ', 'python'
        ])
        
        has_javascript_patterns = any(pattern in modified_content for pattern in [
            'const ', 'require(', 'module.exports', 'function(', 'console.log'
        ])
        
        if has_python_patterns and not has_javascript_patterns:
            print("✅ Language constraint enforcement: PASSED")
            return True
        else:
            print("❌ Language constraint enforcement: FAILED")
            print(f"   Python patterns found: {has_python_patterns}")
            print(f"   JavaScript patterns found: {has_javascript_patterns}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
    finally:
        # Cleanup
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)

def test_planner_infrastructure_awareness():
    """Test that planner includes proper infrastructure files"""
    print("\n🧪 Testing planner infrastructure awareness...")
    
    # Create session state for fullstack web app
    session_state = {
        'language': 'python',
        'system_type': 'fullstack_web_app',
        'architectural_context': {
            'architecture_pattern': 'fullstack_web',
            'modules': {
                'backend': {'languages': ['python']},
                'frontend': {'languages': ['javascript', 'jsx']}
            }
        }
    }
    
    try:
        # Get enhanced planner
        planner = get_rag_enabled_agent("planner", session_state=session_state)
        
        # Test planning for fullstack app
        plan_prompt = """Objective: Create an emotional intelligence advisor web application
Language: python

CRITICAL: You must return ONLY a valid JSON object with this exact structure:
{"files": ["path/to/file1.py", "path/to/file2.py", "path/to/file3.py"]}"""

        response = planner.run(plan_prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        
        print(f"📋 Planner response preview:\n{content[:300]}...")
        
        # Check for essential infrastructure files
        essential_files = [
            'index.html',      # Vite entry point
            'vite.config.js',  # Vite config
            'main.jsx',        # React entry
            'App.jsx',         # Main component
            'main.py'          # Backend entry
        ]
        
        found_infrastructure = sum(1 for file in essential_files if file in content)
        
        if found_infrastructure >= 3:  # At least 3 essential files
            print(f"✅ Infrastructure awareness: PASSED ({found_infrastructure}/{len(essential_files)} found)")
            return True
        else:
            print(f"❌ Infrastructure awareness: FAILED ({found_infrastructure}/{len(essential_files)} found)")
            return False
            
    except Exception as e:
        print(f"❌ Planner test failed with error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing architectural intelligence fixes...\n")
    
    results = []
    
    # Test 1: Language constraint enforcement
    results.append(test_language_constraint_enforcement())
    
    # Test 2: Planner infrastructure awareness  
    results.append(test_planner_infrastructure_awareness())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The architectural fixes are working.")
        return 0
    else:
        print("❌ Some tests failed. The fixes need more work.")
        return 1

if __name__ == "__main__":
    sys.exit(main())