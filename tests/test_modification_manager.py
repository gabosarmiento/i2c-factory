# tests/test_modification_manager.py

import unittest
import tempfile
import shutil
from pathlib import Path
import os
import difflib
import re
# ── bootstrap built‑ins (must come BEFORE any i2c import) ────────────
from i2c.bootstrap import initialize_environment
initialize_environment()
from i2c.agents.modification_team.modification_manager import ModificationManager
from i2c.agents.modification_team.patch import Patch
from i2c.agents.modification_team.code_modification_manager_agno import apply_modification

class MockRunResponse:
    """Mock object that mimics Agent.run() response."""
    def __init__(self, content):
        self.content = content

def mock_function_modifier(prompt):
    """
    Mock function to replace the LLM call during testing.
    This simulates the response from the LLM based on the prompt content.
    """
    # Extract the original function signature to ensure we include it exactly
    import re
    
    # Find the original function signature in the prompt
    original_signature_match = re.search(r'```python\n(def\s+\w+\([^)]*\):)', prompt, re.DOTALL)
    original_signature = original_signature_match.group(1) if original_signature_match else None
    
    # For adding a title parameter to greet
    if "Add title parameter" in prompt and original_signature:
        modified_signature = original_signature.replace("(name):", "(name, title=None):")
        return MockRunResponse(f"""```python
{modified_signature}
    \"\"\"Function to greet a person with optional title.\"\"\"
    if title:
        return f"Hello, {{title}} {{name}}!"
    return f"Hello, {{name}}!"
```""")
    
    # For making greeting more enthusiastic 
    elif "enthusiastic" in prompt and original_signature:
        return MockRunResponse(f"""```python
{original_signature}
    \"\"\"Function to greet a person enthusiastically.\"\"\"
    return f"Hello, {{name}}!!"
```""")
    
    # For adding a new multiply function
    elif "multiply" in prompt:
        return MockRunResponse("""```python
def multiply(a, b):
    \"\"\"Calculate the product of two numbers.\"\"\"
    return a * b
```""")
    
    # Default response - if we can't match anything specific, just modify the return value
    # but keep the exact original signature to pass validation
    if original_signature:
        return MockRunResponse(f"""```python
{original_signature}
    \"\"\"Modified function.\"\"\"
    return f"Modified: {{name}}"
```""")
    
    # Fallback
    return MockRunResponse("def unknown_function():\n    pass")

class TestModificationManager(unittest.TestCase):
    """Test the new ModificationManager class and adapter functions."""
    
    def setUp(self):
        """Create a temporary directory with test files."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir)
        
        # Create a test Python file
        self.test_file = self.project_path / "test_module.py"
        with open(self.test_file, "w") as f:
            f.write("""
def greet(name):
    \"\"\"Function to greet a person.\"\"\"
    return f"Hello, {name}!"

def calculate_sum(a, b):
    \"\"\"Calculate the sum of two numbers.\"\"\"
    return a + b
""")
        
    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)
        
    def test_function_modification(self):
        """Test modifying a specific function."""
        manager = ModificationManager(self.project_path, mock_function_modifier=mock_function_modifier)
        
        # Create a modification step to update the greet function
        modification_step = {
            "action": "modify",
            "file": "test_module.py",
            "function": "greet",
            "what": "Add title parameter",
            "how": "Add an optional title parameter that gets added before the name"
        }
        
        # Apply the modification
        result = manager.process_modification(modification_step)
        
        # Verify result is a Patch object
        self.assertTrue(hasattr(result, "diff_text"), "Result should be a Patch object")
        self.assertTrue(hasattr(result, "file_path"), "Result should be a Patch object")
        
        # Verify the file was actually modified
        with open(self.test_file, "r") as f:
            content = f.read()
        
        # Check that the modified function has a title parameter
        self.assertIn("def greet(name, title=None):", content)
        
    def test_function_addition(self):
        """Test adding a new function to an existing file."""
        manager = ModificationManager(self.project_path, mock_function_modifier=mock_function_modifier)
        
        # Create a modification step to add a new function
        modification_step = {
            "action": "add",
            "file": "test_module.py",
            "function": "multiply",
            "what": "Add a function to multiply two numbers",
            "how": "Create a function named multiply that takes parameters a and b and returns their product"
        }
        
        # Apply the modification
        result = manager.process_modification(modification_step)
        
        # Verify result is a Patch object
        self.assertTrue(hasattr(result, "diff_text"), "Result should be a Patch object")
        
        # Verify the file was actually modified
        with open(self.test_file, "r") as f:
            content = f.read()
        
        # Check that the new function was added
        self.assertIn("def multiply(", content)
        self.assertIn("return a * b", content)
        
    def test_function_deletion(self):
        """Test deleting a function from a file."""
        manager = ModificationManager(self.project_path, mock_function_modifier=mock_function_modifier)
        
        # Create a modification step to delete a function
        modification_step = {
            "action": "delete",
            "file": "test_module.py",
            "function": "calculate_sum"
        }
        
        # Apply the modification
        result = manager.process_modification(modification_step)
        
        # Verify result is a Patch object
        self.assertTrue(hasattr(result, "diff_text"), "Result should be a Patch object")
        
        # Verify the file was actually modified
        with open(self.test_file, "r") as f:
            content = f.read()
        
        # Check that the function was deleted
        self.assertNotIn("def calculate_sum", content)
        # But the other function should still be there
        self.assertIn("def greet", content)
        
    def test_adapter_compatibility(self):
        """Test that the adapter function works with the new implementation."""
        # Override the global safe_function_modifier_agent with a mock for this test
        from i2c.agents.modification_team.safe_function_modifier import SafeFunctionModifierAgent
        import i2c.agents.modification_team.safe_function_modifier as sfm_module
        
        # Save original agent
        original_agent = sfm_module.safe_function_modifier_agent
        
        try:
            # Replace with mocked agent
            sfm_module.safe_function_modifier_agent = SafeFunctionModifierAgent(mock_run_func=mock_function_modifier)
            
            # Create a modification step to update the greet function
            modification_step = {
                "action": "modify",
                "file": "test_module.py",
                "function": "greet",
                "what": "Make greeting more enthusiastic",
                "how": "Add an exclamation mark to the greeting message"
            }
            
            # Use the adapter function
            result = apply_modification(modification_step, self.project_path)
            
            # Verify result is a Patch object
            self.assertTrue(hasattr(result, "diff_text"), "Result should be a Patch object")
            
            # Verify the file was actually modified
            with open(self.test_file, "r") as f:
                content = f.read()
            
            # Check that the modification was applied
            self.assertIn("!!", content)
        finally:
            # Restore original agent
            sfm_module.safe_function_modifier_agent = original_agent
        
    def test_error_handling(self):
        """Test that errors are properly handled and returned."""
        manager = ModificationManager(self.project_path, mock_function_modifier=mock_function_modifier)
        
        # Create a specific modification step that our special case will recognize
        modification_step = {
            "action": "modify",
            "file": "test_module.py",
            "function": "non_existent_function",
            "what": "Update function",
            "how": "This should fail because the function doesn't exist"
        }
        
        # Apply the modification
        result = manager.process_modification(modification_step)
        
        # Verify result is an error dictionary
        self.assertFalse(hasattr(result, "diff_text"), "Result should be an error dictionary")
        self.assertTrue("error" in result, "Result should contain an error key")
        self.assertIn("not found", result["error"])
    
    def test_file_creation(self):
        """Test file creation."""
        manager = ModificationManager(self.project_path, mock_function_modifier=mock_function_modifier)
        
        # Define a new file to create
        new_file_path = "new_module.py"
        
        # Create a modification step to create a file
        modification_step = {
            "action": "create",
            "file": new_file_path,
            "what": "Create a new module",
            "how": "Add a simple module with a main function"
        }
        
        # Apply the modification
        result = manager.process_modification(modification_step)
        
        # Verify result is a Patch object
        self.assertTrue(hasattr(result, "diff_text"), "Result should be a Patch object")
        
        # Verify the file was created
        new_file = self.project_path / new_file_path
        self.assertTrue(new_file.exists(), "New file should have been created")
        
        # Check the file content
        content = new_file.read_text()
        self.assertIn("def main()", content)

if __name__ == "__main__":
    unittest.main()