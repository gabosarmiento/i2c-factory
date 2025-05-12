# tests/test_agentic_orchestration.py
from i2c.bootstrap import initialize_environment
initialize_environment()
import asyncio
from pathlib import Path
import unittest

from i2c.workflow.agentic_orchestrator import execute_agentic_evolution

class TestAgenticOrchestration(unittest.TestCase):
    
    def setUp(self):
        self.project_path = Path("test_project")
        if not self.project_path.exists():
            self.project_path.mkdir()
        
        # Create a simple test file
        test_file = self.project_path / "test_file.py"
        test_file.write_text("""
def add(a, b):
    return a + b

def main():
    print(add(1, 2))

if __name__ == "__main__":
    main()
""")
    
    def tearDown(self):
        # Clean up test files
        for file_path in self.project_path.glob("**/*"):
            if file_path.is_file():
                file_path.unlink()
        
        # Remove test directory
        self.project_path.rmdir()
    
    def test_orchestration_execution(self):
        async def run_orchestration():
            objective = {
                "task": "Refactor the add function to include type hints",
                "constraints": ["PEP8", "Type safety"],
                "quality_gates": ["flake8", "mypy"]
            }
            
            result = await execute_agentic_evolution(objective, self.project_path)
            
            # Check that the orchestration completed
            self.assertIn("decision", result)
            self.assertIn(result["decision"], ["approve", "reject"])
            
            # Check that the file was modified
            test_file = self.project_path / "test_file.py"
            self.assertTrue(test_file.exists())
            content = test_file.read_text()
            
            # Check that type hints were added
            self.assertIn("def add(a:", content)
            self.assertIn(") ->", content)
        
        asyncio.run(run_orchestration())

if __name__ == "__main__":
    unittest.main()