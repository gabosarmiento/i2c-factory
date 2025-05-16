# Create a new test file tests/test_direct_modification.py:

import unittest
from pathlib import Path
import tempfile
import shutil
import os

class TestDirectModification(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary project directory
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir)
        
        # Create a simple Python file
        test_file = self.project_path / "test_module.py"
        test_file.write_text("""
def hello():
    print('Hello World')

if __name__ == "__main__":
    hello()
""")
        
    def tearDown(self):
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_execute_modification_cycle(self):
        from i2c.workflow.modification.execute_cycle import execute_modification_cycle
        from i2c.db_utils import get_db_connection
        from i2c.workflow.modification.rag_config import get_embed_model
        from i2c.cli.controller import canvas
        
        # Execute the modification cycle
        result = execute_modification_cycle(
            user_request="Add a goodbye function that prints Goodbye World and call it in main",
            project_path=self.project_path,
            language="python",
            db=get_db_connection(),
            embed_model=get_embed_model()
        )
        
        # Check result
        self.assertTrue(result["success"], "Modification should succeed")
        
        # Check files modified
        code_map = result["code_map"]
        self.assertTrue(len(code_map) > 0, "At least one file should be modified")
        
        # Print content of modified files
        for file_path, content in code_map.items():
            print(f"\nModified file {file_path}:\n{content}\n")
        
        # Check if specific file was modified
        modified_file = self.project_path / "test_module.py"
        self.assertTrue(modified_file.exists(), "test_module.py should exist")
        
        # Check content
        content = modified_file.read_text()
        self.assertIn("def goodbye", content, "Should add goodbye function")
        self.assertIn("Goodbye World", content, "Should print Goodbye World")
        self.assertIn("goodbye()", content, "Should call goodbye function")

if __name__ == "__main__":
    unittest.main()