import unittest
from pathlib import Path
import tempfile
import os
from typing import Dict

# Import from our updated tools module
from i2c.agents.quality_team.tools.tool_utils import run_flake8, run_black
from i2c.agents.quality_team.hooks.validation_tool_hook import validation_tool_hook

class TestToolFunctions(unittest.TestCase):
    """Test that our tool functions work properly without the decorator issue"""
    
    def setUp(self):
        """Create a test file"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = Path(self.temp_dir.name)
        
        # Create a test Python file with intentional issues
        self.python_file_path = self.project_path / "test.py"
        with open(self.python_file_path, 'w') as f:
            f.write("""
import os, sys, math  # multiple imports on one line
def hello():
  print("world")  # incorrect indentation
x = "test"  # missing type annotation
            """)
    
    def tearDown(self):
        """Clean up test files"""
        self.temp_dir.cleanup()
    
    def test_direct_function_call(self):
        """Test that we can call the tool functions directly"""
        # Call flake8 directly
        result = run_flake8(str(self.python_file_path))
        
        # Verify it's a dict with the expected keys
        self.assertIsInstance(result, dict)
        self.assertIn("passed", result)
        self.assertIn("issues", result)
        self.assertIn("command", result)
        
        # We expect flake8 to find issues
        self.assertFalse(result["passed"])
        self.assertGreater(len(result["issues"]), 0)
    
    def test_validation_hook(self):
        """Test that the validation hook works properly"""
        # Call through the validation hook
        result = validation_tool_hook("run_flake8", run_flake8, {"file_path": str(self.python_file_path)})
        
        # Verify it's a dict with the expected keys
        self.assertIsInstance(result, dict)
        self.assertIn("passed", result)
        self.assertIn("issues", result)
        
        # Call again to test caching
        cached_result = validation_tool_hook("run_flake8", run_flake8, {"file_path": str(self.python_file_path)})
        
        # Verify we get the same result
        self.assertEqual(result, cached_result)

if __name__ == "__main__":
    unittest.main()