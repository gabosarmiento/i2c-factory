#!/usr/bin/env python3
"""
Quick test for frontend file detection
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent / "src"
sys.path.insert(0, str(project_root))

# Initialize environment first
from i2c.bootstrap import initialize_environment
initialize_environment()

def test_frontend_detection():
    """Test the frontend file detection"""
    
    from i2c.workflow.generation_workflow import GenerationWorkflow
    
    # Create a workflow instance to test the methods
    workflow = GenerationWorkflow()
    
    # Test cases for frontend file detection
    test_cases = [
        # Frontend files (should return True)
        ("frontend/src/App.jsx", True),
        ("frontend/src/components/Dashboard.jsx", True),
        ("client/pages/Home.tsx", True),
        ("src/components/Header.vue", True),
        ("ui/styles/main.css", True),
        ("package.json", True),
        ("index.html", True),
        
        # Backend files (should return False)
        ("backend/main.py", False),
        ("api/routes.py", False),
        ("models/user.py", False),
        ("requirements.txt", False),
        ("Dockerfile", False),
    ]
    
    print("🧪 Testing frontend file detection...")
    
    all_passed = True
    for file_path, expected in test_cases:
        result = workflow._is_frontend_file(file_path)
        status = "✅" if result == expected else "❌"
        print(f"{status} {file_path}: {result} (expected: {expected})")
        
        if result != expected:
            all_passed = False
    
    # Test component type detection
    print("\n🧪 Testing component type detection...")
    
    component_tests = [
        ("frontend/src/App.jsx", "app"),
        ("src/components/Header.jsx", "component"),  
        ("src/pages/Dashboard.jsx", "page"),
        ("ui/forms/LoginForm.tsx", "form"),
        ("other/file.jsx", "general"),
    ]
    
    for file_path, expected in component_tests:
        result = workflow._get_component_type(file_path)
        status = "✅" if result == expected else "❌"
        print(f"{status} {file_path}: '{result}' (expected: '{expected}')")
        
        if result != expected:
            all_passed = False
    
    print(f"\n🎯 Overall Result: {'✅ PASSED' if all_passed else '❌ FAILED'}")
    return all_passed

if __name__ == "__main__":
    test_frontend_detection()