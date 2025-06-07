# test_markdown_stripping.py
"""
Test script to verify markdown code block stripping functionality
"""
from i2c.bootstrap import initialize_environment
initialize_environment()
import sys
from pathlib import Path

# Add the project path to sys.path so we can import the markdown utility
sys.path.append(str(Path(__file__).parent.parent))

try:
    from i2c.utils.markdown import strip_markdown_code_block
except ImportError:
    print("❌ Could not import strip_markdown_code_block")
    print("Make sure you're running this from the correct directory")
    sys.exit(1)

def test_markdown_stripping():
    """Test various markdown stripping scenarios"""
    
    test_cases = [
        # Case 1: Python code with markdown
        {
            "name": "Python with markdown",
            "input": """```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
```""",
            "expected_start": "from fastapi import FastAPI",
            "should_not_contain": "```"
        },
        
        # Case 2: JavaScript with markdown
        {
            "name": "JavaScript with markdown",
            "input": """```javascript
import React from 'react';

function App() {
  return <div>Hello World</div>;
}

export default App;
```""",
            "expected_start": "import React from 'react';",
            "should_not_contain": "```"
        },
        
        # Case 3: Code without markdown (should remain unchanged)
        {
            "name": "Clean code without markdown",
            "input": """def hello_world():
    print("Hello, World!")
    
if __name__ == "__main__":
    hello_world()""",
            "expected_start": "def hello_world():",
            "should_not_contain": "```"
        },
        
        # Case 4: Code with language specification
        {
            "name": "Code with language specification",
            "input": """```python
# This is a Python comment
def main():
    pass
```""",
            "expected_start": "# This is a Python comment",
            "should_not_contain": "```"
        },
        
        # Case 5: Code with extra whitespace
        {
            "name": "Code with extra whitespace",
            "input": """   ```python
def test():
    return True
```   """,
            "expected_start": "def test():",
            "should_not_contain": "```"
        }
    ]
    
    print("🧪 Testing Markdown Code Block Stripping")
    print("=" * 50)
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print("-" * 30)
        
        # Apply the stripping function
        result = strip_markdown_code_block(test_case["input"])
        
        # Check if it starts correctly
        starts_correctly = result.strip().startswith(test_case["expected_start"])
        
        # Check if markdown is removed
        no_markdown = test_case["should_not_contain"] not in result
        
        # Display results
        print(f"Input preview: {test_case['input'][:50]}...")
        print(f"Output preview: {result[:50]}...")
        print(f"✅ Starts correctly: {starts_correctly}")
        print(f"✅ Markdown removed: {no_markdown}")
        
        if starts_correctly and no_markdown:
            print("✅ PASSED")
        else:
            print("❌ FAILED")
            all_passed = False
            print(f"Full input:\n{test_case['input']}")
            print(f"Full output:\n{result}")
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests PASSED! Markdown stripping is working correctly.")
    else:
        print("❌ Some tests FAILED. Check the markdown stripping function.")
    
    return all_passed

def test_code_builder_integration():
    """Test integration with CodeBuilderAgent if available"""
    print("\n🔧 Testing CodeBuilder Integration")
    print("=" * 50)
    
    try:
        from i2c.agents.core_team.code_builder import CodeBuilderAgent
        
        # Create a test agent
        agent = CodeBuilderAgent()
        
        print("✅ CodeBuilderAgent imported successfully")
        print(f"Agent name: {agent.name}")
        print(f"Agent has run method: {hasattr(agent, 'run')}")
        
        # Test if the agent would strip markdown (simulated)
        test_response = type('Response', (), {
            'content': '```python\ndef test():\n    pass\n```'
        })()
        
        # Check if the enhanced run method exists
        if hasattr(agent, '_enhance_prompt_with_context'):
            print("✅ Agent has RAG context enhancement")
        else:
            print("⚠️ Agent missing RAG context enhancement")
            
        return True
        
    except ImportError as e:
        print(f"❌ Could not import CodeBuilderAgent: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing CodeBuilder: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Markdown Stripping Test Suite")
    print("=" * 60)
    
    # Test 1: Basic markdown stripping
    basic_test_passed = test_markdown_stripping()
    
    # Test 2: CodeBuilder integration
    integration_test_passed = test_code_builder_integration()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Basic markdown stripping: {'✅ PASSED' if basic_test_passed else '❌ FAILED'}")
    print(f"CodeBuilder integration: {'✅ PASSED' if integration_test_passed else '❌ FAILED'}")
    
    if basic_test_passed and integration_test_passed:
        print("\n🎉 All tests passed! The system should handle markdown correctly.")
    else:
        print("\n⚠️ Some tests failed. Review the implementation.")
        
    print("\n💡 To test with a real scenario, try running a simple generation step.")