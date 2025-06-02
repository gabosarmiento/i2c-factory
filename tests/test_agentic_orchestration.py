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
            # Debug: Check what modifications were reported
            modifications = result["result"].get("modifications", {})
            print(f"DEBUG: Reported modifications: {modifications}")

            # Debug: Check session state for file changes
            session_state = result.get("session_state", {})
            modified_files = session_state.get("modified_files", {})
            print(f"DEBUG: Session modified files: {modified_files}")
            # Check that the orchestration completed
            self.assertIn("result", result)
            self.assertIn("decision", result["result"])
            self.assertIn(result["result"]["decision"], ["approve", "reject"])
            
            # Check that new files were created with type hints
            add_file = self.project_path / "add.py"
            main_file = self.project_path / "main.py"
            test_file = self.project_path / "test_file.py"

            # Check any of the files that might have been modified
            target_file = None
            for file_path in [add_file, test_file, main_file]:
                if file_path.exists():
                    target_file = file_path
                    break

            self.assertIsNotNone(target_file, "No modified file found")
            content = target_file.read_text()
            # Check that type hints were added
            self.assertIn("def add(a:", content)
            self.assertIn(") ->", content)
        
        asyncio.run(run_orchestration())

if __name__ == "__main__":
    unittest.main()