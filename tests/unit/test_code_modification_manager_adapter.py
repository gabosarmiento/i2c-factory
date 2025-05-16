import os
import shutil
import tempfile
from pathlib import Path
import sys
import json
import unittest
import pytest
from unittest.mock import MagicMock, patch
from i2c.agents.modification_team.code_modification_manager import ModifierAdapter

# Import necessary components (adjust imports as needed for your project structure)
from i2c.agents.modification_team.code_modification_manager import (
    ModificationRequest, 
    AnalysisResult, 
    ModificationPlan,
    ModifierAdapter,
    Patch, 
    ValidationReport
)

class DummyEmptyModifierAgent:
    def predict(self, messages):
        # Simulate a valid response with empty modified content
        return json.dumps({
            "file_path": "dummy.py",
            "modified": ""
        })

def test_modifier_adapter_empty_llm_output_fallbacks_to_original():
    adapter = ModifierAdapter(agent=DummyEmptyModifierAgent())
    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_path = Path(tmpdir) / "dummy.py"
        dummy_path.write_text("def hello():\n    pass\n")

        request = ModificationRequest(
            project_root=str(tmpdir),
            user_prompt=json.dumps({
                "file": "dummy.py",
                "what": "simulate",
                "how": "empty response"
            })
        )
        analysis = AnalysisResult(details="{}")

        result = adapter.modify(request, analysis)
        diff_hints = json.loads(result.diff_hints)

        # Should fallback to the original file contents
        assert diff_hints["modified"] == "def hello():\n    pass\n"
        assert diff_hints["file_path"] == "dummy.py"

# ---------- For the "real change" test, you likely have a test class: ----------

class DummyModifierAgent:
    def __init__(self, response):
        self._response = response
    def predict(self, messages):
        return self._response

       
class TestModifierAdapter(unittest.TestCase):
    """
    Test suite for ModifierAdapter to ensure it correctly handles
    various file types and edge cases.
    """
    
    def setUp(self):
        """Set up test environment with a temporary directory."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.mock_agent = MagicMock()
        self.adapter = ModifierAdapter(self.mock_agent)
        
        # Create a base project structure
        self.setup_test_project()
        
        # Save the original directory
        self.original_dir = os.getcwd()
        
        # Change to the test directory
        os.chdir(self.test_dir)
        
        print(f"Test setup complete. Using temporary directory: {self.test_dir}")

    def tearDown(self):
        """Clean up the test environment."""
        # Change back to the original directory
        os.chdir(self.original_dir)
        
        # Clean up the test directory
        try:
            shutil.rmtree(self.test_dir)
            print(f"Cleaned up test directory: {self.test_dir}")
        except Exception as e:
            print(f"Warning: Failed to clean up test directory: {e}")
    
    def setup_test_project(self):
        """Set up a test project with various file types to test modification."""
        # Create Python test file
        python_file = self.test_dir / "test_module.py"
        python_file.write_text("""
# A simple test module
def greet(name):
    return f"Hello, {name}!"
        
# TODO: Add more functions
""")
        
        # Create CSS file
        css_file = self.test_dir / "styles.css"
        css_file.write_text("""
/* Base styles */
body {
    font-family: Arial, sans-serif;
    color: #333;
    background-color: #f4f4f4;
    margin: 0;
    padding: 20px;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
}

h1 {
    color: #444;
}
""")
        
        # Create requirements.txt
        req_file = self.test_dir / "requirements.txt"
        req_file.write_text("""
# Project dependencies
flask==2.0.1
numpy==1.21.0
pandas==1.3.0
requests==2.26.0
""")
        
        # Create test file with duplicate methods
        duplicate_test = self.test_dir / "test_app.py"
        duplicate_test.write_text("""
import unittest

class TestCreateEpub(unittest.TestCase):
    def test_create_basic(self):
        self.assertTrue(True)
        
    def test_create_advanced(self):
        self.assertTrue(True)

class TestMainFunction(unittest.TestCase):
    def test_main_success(self):
        self.assertTrue(True)
        
# Duplicate class definitions (problematic)
class TestCreateEpub(unittest.TestCase):
    def test_create_basic(self):
        # This is a duplicate!
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
    
if __name__ == '__main__':
    # Duplicate unittest.main call
    unittest.main()
""")

    def mock_ask_response(self, response_content):
        """Helper to set up mock responses from the agent."""
        self.mock_agent.predict.return_value = response_content
        
    def test_python_function_modification(self):
        """Test that Python function signatures are correctly modified."""
        # Setup mock to return empty response (testing our fallback)
        self.mock_ask_response(json.dumps({
            "file_path": "test_module.py",
            "original": "",
            "modified": ""
        }))
        
        # Create request
        request = ModificationRequest(
            project_root=self.test_dir,
            user_prompt=json.dumps({
                "file": "test_module.py",
                "what": "Change function signature",
                "how": "Replace 'def greet(name):' with 'def greet(name, title=None):' and update return statement"
            })
        )
        
        # Create empty analysis
        analysis = AnalysisResult(details="{}")
        
        # Execute modification
        result = self.adapter.modify(request, analysis)
        
        # Parse the result
        diff_hints = json.loads(result.diff_hints)
        
        # Verify correct function signature was applied
        self.assertIn("def greet(name, title=None):", diff_hints["modified"])
        self.assertIn("return f\"Hello, {title} {name}!\" if title else f\"Hello, {name}!\"", diff_hints["modified"])
        
        print("✅ Python function modification test passed")

    def test_css_file_modification(self):
        """Test handling of CSS file modifications."""
        # Setup mock to return actual modified content
        modified_css = """
/* Base styles */
body {
    font-family: 'Roboto', sans-serif;
    color: #333;
    background-color: #f8f9fa;
    margin: 0;
    padding: 20px;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
}

h1 {
    color: #0066cc;
    font-weight: bold;
}

/* New button styles */
.button {
    background-color: #0066cc;
    color: white;
    padding: 10px 15px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}
"""
        self.mock_ask_response(json.dumps({
            "file_path": "styles.css",
            "original": "",
            "modified": modified_css
        }))
        
        # Create request
        request = ModificationRequest(
            project_root=self.test_dir,
            user_prompt=json.dumps({
                "file": "styles.css",
                "what": "Update styles",
                "how": "Change font to Roboto, update colors, and add button styles"
            })
        )
        
        # Create empty analysis
        analysis = AnalysisResult(details="{}")
        
        # Execute modification
        result = self.adapter.modify(request, analysis)
        
        # Parse the result
        diff_hints = json.loads(result.diff_hints)
        
        # Verify CSS was properly modified
        self.assertIn("font-family: 'Roboto', sans-serif", diff_hints["modified"])
        self.assertIn("/* New button styles */", diff_hints["modified"])
        self.assertIn(".button", diff_hints["modified"])
        
        print("✅ CSS modification test passed")

    def test_requirements_txt_modification(self):
        """Test handling of requirements.txt modifications."""
        # Setup mock to return empty response (testing direct manipulation)
        self.mock_ask_response(json.dumps({
            "file_path": "requirements.txt",
            "original": "",
            "modified": """
        # Project dependencies
        flask==2.2.0
        numpy==1.21.0
        pandas==1.3.0
        requests==2.26.0
        matplotlib==3.5.0
        """
        }))

        # Create request
        request = ModificationRequest(
            project_root=self.test_dir,
            user_prompt=json.dumps({
                "file": "requirements.txt",
                "what": "Update dependencies",
                "how": "Upgrade Flask to 2.2.0 and add matplotlib==3.5.0"
            })
        )
        
        # Create empty analysis
        analysis = AnalysisResult(details="{}")
        
        # Execute modification
        result = self.adapter.modify(request, analysis)
        
        # Parse the result
        diff_hints = json.loads(result.diff_hints)
        
        # Verify requirements were properly modified
        # If direct manipulation for requirements is implemented, the version should be updated
        self.assertIn("flask==2.2.0", diff_hints["modified"].lower())
        self.assertIn("matplotlib==3.5.0", diff_hints["modified"].lower())
        
        # Verify original dependencies are still there
        self.assertIn("numpy==1.21.0", diff_hints["modified"])
        self.assertIn("pandas==1.3.0", diff_hints["modified"])
        
        print("✅ Requirements.txt modification test passed")

    def test_duplicate_test_cleanup(self):
        """Test handling of duplicate test methods and unittest.main() calls."""
        # Setup mock to return empty response (testing direct manipulation)
        self.mock_ask_response(json.dumps({
            "file_path": "test_app.py",
            "original": "",
            "modified": """
        import unittest

        class TestCreateEpub(unittest.TestCase):
            def test_example(self):
                self.assertTrue(True)

        if __name__ == "__main__":
            unittest.main()
        """
        }))
        
        # Create request
        request = ModificationRequest(
            project_root=self.test_dir,
            user_prompt=json.dumps({
                "file": "test_app.py",
                "what": "Clean up test file",
                "how": "Fix duplicate TestCreateEpub class and unittest.main() calls"
            })
        )
        
        # Create empty analysis
        analysis = AnalysisResult(details="{}")
        
        # Execute modification
        result = self.adapter.modify(request, analysis)
        
        # Parse the result
        diff_hints = json.loads(result.diff_hints)
        
        # Count occurrences in modified content
        test_class_count = diff_hints["modified"].count("class TestCreateEpub")
        unittest_main_count = diff_hints["modified"].count("unittest.main()")
        
        # Verify duplicates were removed
        self.assertEqual(test_class_count, 1, "TestCreateEpub class should appear exactly once")
        self.assertEqual(unittest_main_count, 1, "unittest.main() should appear exactly once")
        
        print("✅ Duplicate test cleanup test passed")

    def test_empty_response_handling(self):
        """Test handling of completely empty responses from the agent."""
        # Setup mock to return completely empty response
        self.mock_ask_response("")
        
        # Create request for a file
        request = ModificationRequest(
            project_root=self.test_dir,
            user_prompt=json.dumps({
                "file": "test_module.py",
                "what": "Some change",
                "how": "That should trigger fallback"
            })
        )
        
        # Create empty analysis
        analysis = AnalysisResult(details="{}")
        
        # Execute modification - should not raise an exception
        result = self.adapter.modify(request, analysis)
        
        # Verify we got a valid result
        self.assertIsNotNone(result)
        self.assertIsInstance(result, ModificationPlan)
        
        # Parse the diff hints - should contain original content at minimum
        diff_hints = json.loads(result.diff_hints)
        self.assertIn("file_path", diff_hints)
        self.assertIn("original", diff_hints)
        self.assertIn("modified", diff_hints)
        
        print("✅ Empty response handling test passed")

    def test_nonexistent_file_handling(self):
        """Test handling of nonexistent files."""
        # Setup mock to return empty response
        self.mock_ask_response(json.dumps({
            "file_path": "nonexistent.py",
            "original": "",
            "modified": "# New content for a previously nonexistent file\n\nprint('Hello world!')"
        }))
        
        # Create request for a nonexistent file
        request = ModificationRequest(
            project_root=self.test_dir,
            user_prompt=json.dumps({
                "file": "nonexistent.py",
                "what": "Create new file",
                "how": "Add a simple hello world program"
            })
        )
        
        # Create empty analysis
        analysis = AnalysisResult(details="{}")
        
        # Execute modification
        result = self.adapter.modify(request, analysis)
        
        # Parse the result
        diff_hints = json.loads(result.diff_hints)
        
        # Verify empty original content
        self.assertEqual(diff_hints["original"], "")
        
        # Verify modified content contains something
        self.assertNotEqual(diff_hints["modified"], "")
        self.assertIn("Hello world", diff_hints["modified"])
        
        print("✅ Nonexistent file handling test passed")

    def test_file_reading_error_handling(self):
        """Test handling of file reading errors."""
        # Create a directory where a file is expected (to cause an error)
        bad_path = self.test_dir / "not_a_file"
        bad_path.mkdir(exist_ok=True)
        
        # Setup mock to return empty response
        self.mock_ask_response(json.dumps({
            "file_path": "test_app.py",
            "original": "",
            "modified": """
        import unittest

        class TestCreateEpub(unittest.TestCase):
            def test_example(self):
                self.assertTrue(True)

        if __name__ == "__main__":
            unittest.main()
        """
        }))
        
        # Create request for the problematic path
        request = ModificationRequest(
            project_root=self.test_dir,
            user_prompt=json.dumps({
                "file": "not_a_file",
                "what": "Update file",
                "how": "This should cause a handled error"
            })
        )
        
        # Create empty analysis
        analysis = AnalysisResult(details="{}")
        
        # Execute modification - should not raise an exception
        result = self.adapter.modify(request, analysis)
        
        # Verify we got a valid result
        self.assertIsNotNone(result)
        self.assertIsInstance(result, ModificationPlan)
        
        print("✅ File reading error handling test passed")

    # Additional tests for ModifierAdapter

    def test_modifieragent_malformed_response(self):
        """Test handling of malformed ModifierAgent response (invalid JSON)."""
        # Simulate invalid JSON response from ModifierAgent
        self.mock_ask_response("{ this is not valid json }")

        request = ModificationRequest(
            project_root=self.test_dir,
            user_prompt=json.dumps({
                "file": "test_app.py",
                "what": "Cleanup",
                "how": "Fix duplicate TestCreateEpub class"
            })
        )

        analysis = AnalysisResult(details="{}")

        # ✅ No esperamos ValueError, solo verificamos que el adapter hace fallback
        result = self.adapter.modify(request, analysis)
        diff_hints = json.loads(result.diff_hints)

        # ✅ El contenido modificado debe ser el raw_reply (aunque sea basura JSON)
        self.assertIn("{ this is not valid json }", diff_hints["modified"])


    def test_modifieragent_unexpected_file_path(self):
        """Test handling when ModifierAgent returns unexpected file_path."""
        self.mock_ask_response(json.dumps({
            "file_path": "unexpected_file.py",
            "original": "",
            "modified": "print('Unexpected file')"
        }))

        request = ModificationRequest(
            project_root=self.test_dir,
            user_prompt=json.dumps({
                "file": "test_app.py",
                "what": "Cleanup",
                "how": "Fix duplicate TestCreateEpub class"
            })
        )

        analysis = AnalysisResult(details="{}")

        result = self.adapter.modify(request, analysis)

        diff_hints = json.loads(result.diff_hints)
        # Verify it falls back to original content for correct file
        self.assertIn("TestCreateEpub", diff_hints["modified"])


    def test_file_outside_project_root(self):
        """Test behavior when file is outside project_root."""
        request = ModificationRequest(
            project_root=self.test_dir,
            user_prompt=json.dumps({
                "file": "../outside_project/test_app.py",
                "what": "Cleanup",
                "how": "Fix duplicate TestCreateEpub class"
            })
        )

        analysis = AnalysisResult(details="{}")

        with self.assertRaises(PermissionError) as context:
            self.mock_ask_response(json.dumps({
                "file_path": "test_app.py",
                "original": "",
                "modified": ""
            }))
            self.adapter.modify(request, analysis)

        self.assertIn("outside of project root", str(context.exception))


    def test_diff_generation_with_real_change(self):
        """Test that diff_hints correctly reflect real code changes."""
        self.mock_ask_response(json.dumps({
            "file_path": "test_app.py",
            "original": "",
            "modified": (
                "import unittest\n\n"
                "class TestCreateEpub(unittest.TestCase):\n"
                "    def test_example(self):\n"
                "        self.assertTrue(True)\n\n"
                "if __name__ == '__main__':\n"
                "    unittest.main()\n"
            )
        }))

        request = ModificationRequest(
            project_root=self.test_dir,
            user_prompt=json.dumps({
                "file": "test_app.py",
                "what": "Cleanup",
                "how": "Fix duplicate TestCreateEpub class"
            })
        )

        analysis = AnalysisResult(details="{}")

        result = self.adapter.modify(request, analysis)

        diff_hints = json.loads(result.diff_hints)

        assert "class TestCreateEpub" in diff_hints["modified"]
        assert diff_hints["modified"].count("class TestCreateEpub") == 1
        assert diff_hints["file_path"] == "test_app.py"


    def test_multiple_files_modification(self):
        """Test handling of ModifierAgent modifying multiple files."""
        self.mock_ask_response(json.dumps([
            {
                "file_path": "file1.py",
                "original": "",
                "modified": "print('File 1 modified')"
            },
            {
                "file_path": "file2.py",
                "original": "",
                "modified": "print('File 2 modified')"
            }
        ]))

        request = ModificationRequest(
            project_root=self.test_dir,
            user_prompt=json.dumps({
                "file": "file1.py",
                "what": "Update",
                "how": "Apply changes to multiple files"
            })
        )

        analysis = AnalysisResult(details="{}")

        result = self.adapter.modify(request, analysis)

        diff_hints = json.loads(result.diff_hints)

        # Only file1.py should be processed in this context
        self.assertIn("file1.py", diff_hints["file_path"])
        self.assertIn("File 1 modified", diff_hints["modified"])



# If running directly, execute all tests
if __name__ == "__main__":
    unittest.main()