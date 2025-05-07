# tests/test_rag_workflow_integration.py
# Integration test for the full RAG-enhanced modification workflow

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import pandas as pd
import json
import tempfile
import shutil
import os
from i2c.bootstrap import initialize_environment
initialize_environment()
# Import workflow components
from i2c.workflow.modification.rag_retrieval import retrieve_context_for_planner, retrieve_context_for_step
from i2c.workflow.modification.plan_generator import generate_modification_plan
from i2c.workflow.modification.code_executor import execute_modification_steps

class TestRAGWorkflowIntegration(unittest.TestCase):
    """Integration tests for the full RAG-enhanced modification workflow."""
    
    def setUp(self):
        """Set up test environment with a temporary project directory."""
        # Create a temporary directory for our test project
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir)
        
        # Create a simple project structure for testing
        os.makedirs(self.project_path / "utils", exist_ok=True)
        
        # Create a test math.py file
        with open(self.project_path / "utils" / "math.py", "w") as f:
            f.write('''# utils/math.py
# Math utility functions

def add_numbers(a, b):
    """Add two numbers and return the result."""
    try:
        result = a + b
        return result
    except TypeError:
        print("Error: Invalid input types")
        return None
''')

        # Create a test main.py file
        with open(self.project_path / "main.py", "w") as f:
            f.write('''# main.py
# Main application file

from utils.math import add_numbers

def main():
    # Example usage
    result = add_numbers(5, 10)
    print(f"The result is: {result}")

if __name__ == "__main__":
    main()
''')
        
        # Mock LanceDB table and embed model
        self.mock_table = MagicMock()
        self.mock_embed_model = MagicMock()
        self.mock_embed_model.encode.return_value = [0.1, 0.2, 0.3]
        # make get_embedding_and_usage return (vector, usage_dict)
        dummy_vec = self.mock_embed_model.encode.return_value
        self.mock_embed_model.get_embedding_and_usage.return_value = (dummy_vec, {"tokens": len(dummy_vec)})
        # Set up mock database query results (context chunks)
        self.mock_query_results = pd.DataFrame({
            'path': ['utils/math.py', 'main.py'],
            'chunk_type': ['function', 'function'],
            'chunk_name': ['add_numbers', 'main'],
            'content': [
                '''def add_numbers(a, b):
    """Add two numbers and return the result."""
    try:
        result = a + b
        return result
    except TypeError:
        print("Error: Invalid input types")
        return None''',
                
                '''def main():
    # Example usage
    result = add_numbers(5, 10)
    print(f"The result is: {result}")'''
            ]
        })
        
        # Patch the necessary components
        self.patchers = []
        
        # Patch RAG retrieval functions
        self.patchers.append(patch('i2c.workflow.modification.rag_retrieval.query_context'))
        self.mock_query_context = self.patchers[-1].start()
        self.mock_query_context.return_value = self.mock_query_results
        
        # Patch canvas (CLI output)
        self.patchers.append(patch('i2c.workflow.modification.plan_generator.canvas'))
        self.patchers.append(patch('i2c.workflow.modification.code_executor.canvas'))
        self.patchers.append(patch('i2c.workflow.modification.rag_retrieval.canvas'))
        
        # Start all remaining patchers
        for patcher in self.patchers[1:]:
            patcher.start()
    
    def tearDown(self):
        """Clean up temporary files and stop patchers."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
        
        # Stop all patchers
        for patcher in self.patchers:
            patcher.stop()
    
    @patch('i2c.agents.modification_team.modification_planner.ModificationPlannerAgent.run')
    @patch('i2c.agents.modification_team.code_modifier.CodeModifierAgent.run')
    def test_full_modification_workflow(self, mock_modifier_run, mock_planner_run):
        """Test the full modification workflow with RAG context."""
        # Set up mock responses
        mock_planner_response = MagicMock()
        mock_planner_response.content = json.dumps([
            {
                "file": "utils/math.py",
                "action": "modify",
                "what": "add subtract_numbers function",
                "how": "implement a function that takes two arguments and returns their difference"
            },
            {
                "file": "main.py",
                "action": "modify",
                "what": "update main to use subtract_numbers",
                "how": "add an example that calls subtract_numbers with 20 and 5"
            }
        ])
        mock_planner_run.return_value = mock_planner_response
        
        # Set up mock code modifier responses for each file
        mock_modifier_responses = {
            "utils/math.py": '''# utils/math.py
# Math utility functions

def add_numbers(a, b):
    """Add two numbers and return the result."""
    try:
        result = a + b
        return result
    except TypeError:
        print("Error: Invalid input types")
        return None

def subtract_numbers(a, b):
    """Subtract b from a and return the result."""
    try:
        result = a - b
        return result
    except TypeError:
        print("Error: Invalid input types")
        return None
''',
            "main.py": '''# main.py
# Main application file

from utils.math import add_numbers, subtract_numbers

def main():
    # Example usage
    result = add_numbers(5, 10)
    print(f"The result is: {result}")
    
    # Example of subtraction
    diff = subtract_numbers(20, 5)
    print(f"The difference is: {diff}")

if __name__ == "__main__":
    main()
'''
        }
        
        # Mock the modifier response based on file path
        def side_effect_modifier(prompt):
            # Look for file path in the prompt (flexible parsing)
            for line in prompt.splitlines():
                # Check for common file path indicators
                if "file" in line.lower() and ".py" in line:
                    # Extract the file path from the line
                    parts = line.split()
                    for part in parts:
                        if ".py" in part:
                            file_path = part.strip().replace("'", "").replace('"', "")
                            if file_path == "utils/math.py":
                                resp = MagicMock()
                                resp.content = mock_modifier_responses["utils/math.py"]
                                return resp
                            elif file_path == "main.py":
                                resp = MagicMock()
                                resp.content = mock_modifier_responses["main.py"]
                                return resp
            raise ValueError(f"Could not determine file path from prompt: {prompt[:100]}...")        
        mock_modifier_run.side_effect = side_effect_modifier
        
        # Execute the test workflow
        
        # 1. Get planning context
        planning_context = retrieve_context_for_planner(
            user_request="f Add a subtract_numbers function and use it in main",
            db=self.mock_table,
            embed_model=self.mock_embed_model
        )
        
        # 2. Generate modification plan
        modification_plan = generate_modification_plan(
            user_request="f Add a subtract_numbers function and use it in main",
            retrieved_context_plan=planning_context,
            project_path=self.project_path,
            language="python"
        )
        
        # 3. Execute the plan with RAG context for each step
        modified_code_map, files_to_delete = execute_modification_steps(
            modification_plan=modification_plan,
            project_path=self.project_path,
            db=self.mock_table,
            embed_model=self.mock_embed_model
        )
        
        # Verify correct number of steps in plan
        self.assertEqual(len(modification_plan), 2)
        self.assertEqual(modification_plan[0]["file"], "utils/math.py")
        self.assertEqual(modification_plan[1]["file"], "main.py")
        
        # Verify that the context was retrieved for planning
        self.mock_query_context.assert_called()
        
        # Verify that the context was retrieved for each step
        self.assertTrue(mock_modifier_run.call_count >= 2)
        
        # Verify the content of modified files
        self.assertEqual(len(modified_code_map), 2)
        self.assertIn("utils/math.py", modified_code_map)
        self.assertIn("main.py", modified_code_map)
        
        # Check content of math.py
        self.assertIn("def subtract_numbers(a, b):", modified_code_map["utils/math.py"])
        self.assertIn("result = a - b", modified_code_map["utils/math.py"])
        
        # Check content of main.py
        self.assertIn("from utils.math import add_numbers, subtract_numbers", modified_code_map["main.py"])
        self.assertIn("diff = subtract_numbers(20, 5)", modified_code_map["main.py"])

if __name__ == '__main__':
    unittest.main()