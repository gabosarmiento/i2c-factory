# tests/test_enhanced_rag_utilization.py
# Tests for the enhanced prompts and RAG utilization in Phase 4.2

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import pandas as pd
import json

from i2c.bootstrap import initialize_environment
initialize_environment()
# Import modules to test
from i2c.agents.modification_team.modification_planner import modification_planner_agent
from i2c.agents.modification_team.code_modifier import code_modifier_agent
from i2c.workflow.modification.plan_generator import generate_modification_plan

class TestEnhancedRAGUtilization(unittest.TestCase):
    """Tests for the enhanced RAG utilization in planner and modifier agents."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock project path
        self.project_path = Path('/test/project')
        
        # Sample context with code patterns for testing
        self.sample_context = '''
[Retrieved Context for planning:]
--- Start Chunk: utils/math.py (function: add_numbers) ---
def add_numbers(a, b):
    """Add two numbers and return the result."""
    try:
        result = a + b
        return result
    except TypeError:
        print("Error: Invalid input types")
        return None
--- End Chunk: utils/math.py ---

--- Start Chunk: models/user.py (class: User) ---
from database import db
from i2c.utils.validators import validate_email

class User:
    def __init__(self, username, email):
        self.username = username
        if validate_email(email):
            self.email = email
        else:
            raise ValueError("Invalid email format")
            
    def save(self):
        try:
            db.save_user(self)
            return True
        except Exception as e:
            print(f"Error saving user: {e}")
            return False
--- End Chunk: models/user.py ---
'''
        
        # Sample feature request
        self.feature_request = "f Add a subtract_numbers function to the math utilities"
        
        # Mock response for planner
        self.mock_planner_response = MagicMock()
        self.mock_planner_response.content = json.dumps([
            {
                "file": "utils/math.py",
                "action": "modify",
                "what": "add subtract_numbers function",
                "how": "implement a function that takes two arguments and returns their difference"
            }
        ])
        
        # Mock response for code modifier
        self.mock_modifier_response = MagicMock()
        self.mock_modifier_response.content = '''
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
'''
        
        # Existing code for modification test
        self.existing_code = '''
def add_numbers(a, b):
    """Add two numbers and return the result;"""
    try:
        result = a + b
        return result
    except TypeError:
        print("Error: Invalid input types")
        return None
'''
        
        # Mock CLI canvas to avoid prints during tests
        self.canvas_patcher = patch('workflow.modification.plan_generator.canvas')
        self.mock_canvas = self.canvas_patcher.start()
        
    def tearDown(self):
        """Tear down test fixtures."""
        self.canvas_patcher.stop()
    
    @patch('agents.modification_team.modification_planner.ModificationPlannerAgent.run')
    def test_enhanced_planner_prompt(self, mock_run):
        """Test that the planner prompt is properly structured with context sections."""
        # Set up mock response
        mock_run.return_value = self.mock_planner_response
        
        # Call the function
        result = generate_modification_plan(
            user_request=self.feature_request,
            retrieved_context_plan=self.sample_context,
            project_path=self.project_path,
            language="python"
        )
        
        # Verify that the planner was called with a well-structured prompt
        args, _ = mock_run.call_args
        prompt = args[0]
        
        # Check for key sections in the prompt
        self.assertIn("# Project Information", prompt)
        self.assertIn("# User Request", prompt)
        self.assertIn("# Retrieved Context", prompt)
        self.assertIn("# Planning Instructions", prompt)
        
        # Verify that the context was included
        self.assertIn("utils/math.py", prompt)
        self.assertIn("models/user.py", prompt)
        
        # Verify result parsing
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["file"], "utils/math.py")
        self.assertEqual(result[0]["action"], "modify")
    
    @patch('agents.modification_team.code_modifier.CodeModifierAgent.run')
    def test_code_modifier_context_extraction(self, mock_run):
        """Test the code modifier's context extraction methods."""
        # Create an instance for testing
        agent = code_modifier_agent
        
        # Test import extraction
        imports = agent._extract_imports_from_context(self.sample_context)
        self.assertIn("from database import db", imports)
        self.assertIn("from utils.validators import validate_email", imports)
        
        # Test pattern extraction
        patterns = agent._extract_coding_patterns(self.sample_context)
        self.assertTrue(any("try:" in p for p in patterns["error_handling"]))
        self.assertTrue(any("def add_numbers" in p for p in patterns["function_patterns"]))
        self.assertIn("username", patterns["naming_conventions"])
        
    @patch('agents.modification_team.code_modifier.CodeModifierAgent.run')
    def test_enhanced_modifier_prompt(self, mock_run):
        """Test that the code modifier prompt properly incorporates context analysis."""
        # Set up mock response
        mock_run.return_value = self.mock_modifier_response
        
        # Create a modification step
        step = {
            "file": "utils/math.py",
            "action": "modify",
            "what": "add subtract_numbers function",
            "how": "implement a function that takes two arguments and returns their difference"
        }
        
        # Call modify_code with our test data
        modified_code = code_modifier_agent.modify_code(
            modification_step=step,
            project_path=self.project_path,
            retrieved_context=self.sample_context
        )
        
        # Extract the prompt that was sent to the LLM
        args, _ = mock_run.call_args
        prompt = args[0]
        
        # Check for enhanced prompt sections
        self.assertIn("# Project and Task Information", prompt)
        self.assertIn("# Retrieved Context Analysis", prompt)
        self.assertIn("## Common Import Patterns", prompt)
        self.assertIn("## Code Style Patterns", prompt)
        self.assertIn("## Raw Context Chunks", prompt)
        self.assertIn("# Quality Check Requirements", prompt)
        
        # Verify that the function was added to the code
        self.assertIn("def subtract_numbers(a, b):", modified_code)
        self.assertIn("result = a - b", modified_code)
        # Verify that error handling pattern was maintained
        self.assertIn("except TypeError:", modified_code)

if __name__ == '__main__':
    unittest.main()