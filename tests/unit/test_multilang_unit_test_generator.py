import pytest
from pathlib import Path

def test_multilang_unit_test_generator():
    """Test the enhanced multi-language unit test generator"""
    
    try:
        from i2c.agents.sre_team.multilang_unit_test import unit_test_generator
        
        # Test code for different languages
        multilang_code_map = {
            # Python
            "calculator.py": """def add(a, b):
    '''Add two numbers.'''
    return a + b

def multiply(x, y):
    '''Multiply two numbers.'''
    return x * y
""",
            
            # JavaScript
            "utils.js": """function formatName(first, last) {
    return `${first} ${last}`;
}

export function calculateTax(amount, rate) {
    return amount * rate;
}

const processData = (data) => {
    return data.filter(item => item.active);
};
""",
            
            # TypeScript
            "api.ts": """interface User {
    id: number;
    name: string;
}

export function createUser(name: string): User {
    return { id: Math.random(), name };
}

function validateEmail(email: string): boolean {
    return email.includes('@');
}
""",
            
            # Go
            "math.go": """package main

func Add(a, b int) int {
    return a + b
}

func Multiply(x, y float64) float64 {
    return x * y
}
""",
            
            # Java
            "Calculator.java": """public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
    
    private double divide(double numerator, double denominator) {
        return numerator / denominator;
    }
    
    public static String formatResult(int result) {
        return "Result: " + result;
    }
}
"""
        }
        
        print("🧪 Testing enhanced multi-language unit test generator...")
        print(f"📁 Input files: {list(multilang_code_map.keys())}")
        
        # Generate tests for all languages
        result = unit_test_generator.generate_tests(multilang_code_map)
        
        print(f"\n📊 Result type: {type(result)}")
        print(f"📁 Total files returned: {len(result) if isinstance(result, dict) else 'Not a dict'}")
        
        if isinstance(result, dict):
            # Separate original files from generated test files
            original_files = set(multilang_code_map.keys())
            test_files = {k: v for k, v in result.items() if k not in original_files}
            
            print(f"🧪 Generated test files: {len(test_files)}")
            
            # Analyze each generated test file
            for test_file_path, test_content in test_files.items():
                print(f"\n" + "="*50)
                print(f"📄 Test File: {test_file_path}")
                print(f"📏 Content length: {len(test_content)} characters")
                
                # Detect language of test file
                if test_file_path.endswith('.py'):
                    language = 'Python'
                    expected_patterns = ['import unittest', 'class Test', 'def test_', 'unittest.main()']
                elif test_file_path.endswith('.js'):
                    language = 'JavaScript'
                    expected_patterns = ['describe(', 'it(', 'expect(', 'require(']
                elif test_file_path.endswith('.ts'):
                    language = 'TypeScript'
                    expected_patterns = ['describe(', 'it(', 'expect(', 'import']
                elif test_file_path.endswith('_test.go'):
                    language = 'Go'
                    expected_patterns = ['package', 'import "testing"', 'func Test']
                elif test_file_path.endswith('Test.java'):
                    language = 'Java'
                    expected_patterns = ['import org.junit', '@Test', 'public void test']
                else:
                    language = 'Unknown'
                    expected_patterns = []
                
                print(f"🔤 Language: {language}")
                
                # Check for expected patterns
                patterns_found = []
                for pattern in expected_patterns:
                    if pattern in test_content:
                        patterns_found.append(pattern)
                
                print(f"✅ Patterns found: {patterns_found}")
                print(f"📋 Coverage: {len(patterns_found)}/{len(expected_patterns)}")
                
                # Show content preview
                print("📝 Content preview:")
                print("-" * 40)
                preview = test_content[:400] + "..." if len(test_content) > 400 else test_content
                print(preview)
                print("-" * 40)
        
        return result
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return None
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_language_detection():
    """Test language detection functionality"""
    
    try:
        from i2c.agents.sre_team.multilang_unit_test import unit_test_generator
        
        test_cases = [
            ("app.py", "python"),
            ("utils.js", "javascript"), 
            ("api.ts", "typescript"),
            ("main.go", "go"),
            ("Calculator.java", "java"),
            ("readme.txt", "unknown")
        ]
        
        print("\n🔍 Testing language detection:")
        
        for file_path, expected_lang in test_cases:
            detected = unit_test_generator._detect_language_from_extension(file_path)
            status = "✅" if detected == expected_lang else "❌"
            print(f"   {status} {file_path} -> {detected} (expected: {expected_lang})")
        
    except Exception as e:
        print(f"❌ Language detection test failed: {e}")


def test_test_file_naming():
    """Test test file naming conventions"""
    
    try:
        from i2c.agents.sre_team.multilang_unit_test import unit_test_generator
        
        test_cases = [
            ("calculator.py", "python", "test_calculator.py"),
            ("utils.js", "javascript", "utils.test.js"),
            ("api.ts", "typescript", "api.test.ts"), 
            ("math.go", "go", "math_test.go"),
            ("Calculator.java", "java", "CalculatorTest.java")
        ]
        
        print("\n📝 Testing test file naming:")
        
        for original_file, language, expected_test_file in test_cases:
            generated = unit_test_generator._get_test_file_name(original_file, language)
            status = "✅" if generated == expected_test_file else "❌"
            print(f"   {status} {original_file} ({language}) -> {generated}")
        
    except Exception as e:
        print(f"❌ Test file naming test failed: {e}")


if __name__ == "__main__":
    print("Testing enhanced multi-language unit test generator...")
    test_multilang_unit_test_generator()
    test_language_detection()
    test_test_file_naming()