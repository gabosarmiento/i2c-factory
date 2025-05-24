import pytest
from pathlib import Path

def test_unit_test_generator_direct():
    """Test the unit test generator directly to see what it actually produces"""
    
    try:
        from i2c.agents.sre_team.unit_test import unit_test_generator
        
        # Test with simple Python code
        test_code_map = {
            "calculator.py": """def add(a, b):
    '''Add two numbers together.'''
    return a + b

def multiply(x, y):
    '''Multiply two numbers.'''
    return x * y

def divide(numerator, denominator):
    '''Divide two numbers with error handling.'''
    if denominator == 0:
        raise ValueError("Cannot divide by zero")
    return numerator / denominator
"""
        }
        
        print("🧪 Testing unit test generator directly...")
        print(f"Input code map: {list(test_code_map.keys())}")
        
        # Generate tests
        result = unit_test_generator.generate_tests(test_code_map)
        
        print(f"📊 Result type: {type(result)}")
        print(f"📁 Files returned: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        # Examine generated test content
        if isinstance(result, dict):
            for file_path, content in result.items():
                print(f"\n📄 File: {file_path}")
                print(f"📏 Content length: {len(content)} characters")
                print("📝 Content preview:")
                print("-" * 40)
                print(content[:500] + "..." if len(content) > 500 else content)
                print("-" * 40)
                
                # Check test structure
                if "import unittest" in content:
                    print("✅ Has unittest import")
                if "class Test" in content:
                    print("✅ Has test class")
                if "def test_" in content:
                    print("✅ Has test methods")
                if "unittest.main()" in content:
                    print("✅ Has unittest.main()")
        
        return result
        
    except ImportError as e:
        print(f"❌ Could not import unit_test_generator: {e}")
        return None
    except Exception as e:
        print(f"❌ Error testing unit test generator: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_unit_test_quality_check():
    """Test if generated unit tests actually work"""
    
    try:
        from i2c.agents.sre_team.unit_test import unit_test_generator
        
        # Simple function to test
        simple_code = {
            "math_utils.py": """def square(n):
    return n * n

def is_even(number):
    return number % 2 == 0
"""
        }
        
        # Generate tests
        result = unit_test_generator.generate_tests(simple_code)
        
        if isinstance(result, dict):
            for file_path, test_content in result.items():
                if file_path.startswith("test_"):
                    print(f"\n🧪 Analyzing test quality for {file_path}")
                    
                    # Check for common issues
                    issues = []
                    
                    if "unittest.main()" in test_content:
                        main_count = test_content.count("unittest.main()")
                        if main_count > 1:
                            issues.append(f"Multiple unittest.main() calls: {main_count}")
                    
                    if "import unittest" not in test_content:
                        issues.append("Missing unittest import")
                    
                    if "def test_" not in test_content:
                        issues.append("No test methods found")
                    
                    if issues:
                        print("❌ Quality issues found:")
                        for issue in issues:
                            print(f"   - {issue}")
                    else:
                        print("✅ Basic quality checks passed")
        
    except Exception as e:
        print(f"❌ Quality check failed: {e}")


if __name__ == "__main__":
    print("Testing unit test generation directly...")
    test_unit_test_generator_direct()
    test_unit_test_quality_check()