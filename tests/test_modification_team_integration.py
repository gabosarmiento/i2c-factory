# tests/test_modification_team_integration.py
from i2c.bootstrap import initialize_environment
initialize_environment()

import unittest
import json
from pathlib import Path
import shutil
from agno.agent import Message

from i2c.agents.modification_team.code_modification_manager import (
    build_code_modification_team,
    ManagerAgent
)

class TestModificationTeamIntegration(unittest.TestCase):
    
    def setUp(self):
        # Create test project directory
        self.project_path = Path("test_project_mod")
        if self.project_path.exists():
            shutil.rmtree(self.project_path)
        self.project_path.mkdir()
        
        # Create a simple test file
        test_file = self.project_path / "simple.py"
        test_file.write_text("""
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

def main():
    result = add(5, 10)
    print(f"The result is {result}")

if __name__ == "__main__":
    main()
""")
    
    def tearDown(self):
        # Clean up test files
        if self.project_path.exists():
            shutil.rmtree(self.project_path)
    
    def test_direct_modification_team(self):
        """Test the modification team directly without the orchestration layer"""
        # Build the modification team
        mod_team = build_code_modification_team(project_path=self.project_path)
        
        # Access the manager agent directly 
        manager = None
        for member in mod_team.members:
            if isinstance(member, ManagerAgent):
                manager = member
                break
        
        self.assertIsNotNone(manager, "ManagerAgent not found in the team")
        
        # Create a simple modification request
        request_data = {
            "modification_step": {
                "action": "modify",
                "file": "simple.py",
                "what": "Add type hints to functions",
                "how": "Add proper Python type hints to all functions"
            },
            "project_path": str(self.project_path),
            "retrieved_context": ""
        }
        
        # Create a Message object with the request
        message = Message(role="user", content=json.dumps(request_data))
        
        # Execute the request using the manager's predict method
        response = manager.predict([message])
        
        # Parse the JSON response
        result = json.loads(response)
        
        # Verify the response structure
        self.assertIn("file_path", result)
        self.assertIn("unified_diff", result)
        self.assertIn("validation", result)
        
        # Verify the unified diff contains modifications
        unified_diff = result.get("unified_diff", "")
        self.assertIn("diff for simple.py", unified_diff)
        
        # Check that the modification involves type hints imports
        self.assertIn("typing", unified_diff.lower())
        
        print(f"Test passed! Response: {response[:200]}...")
if __name__ == "__main__":
    unittest.main()