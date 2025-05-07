from unittest.mock import patch, MagicMock
from i2c.bootstrap import initialize_environment
initialize_environment()
# Immediately patch out the real DB connection
patcher = patch(
    'i2c.agents.modification_team.context_reader.context_indexer.get_db_connection',
    return_value=MagicMock(create_table=lambda *args, **kwargs: True)
)
patcher.start()

# Now import the modules under test
import unittest
from pathlib import Path
import pandas as pd
import numpy as np

from i2c.workflow.modification.rag_retrieval import retrieve_context_for_step
from i2c.workflow.modification.code_executor import execute_modification_steps
from i2c.agents.modification_team.code_modifier import code_modifier_agent
class TestStepSpecificRAGRetrieval(unittest.TestCase):
    """Test the step-specific RAG context retrieval implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock embedding model
        self.mock_embed_model = MagicMock()
        # simulate the two‐tuple return of get_embedding_and_usage()
        dummy_vec = np.array([0.1, 0.2, 0.3])
        self.mock_embed_model.get_embedding_and_usage.return_value = (dummy_vec, {"tokens": 3})
        # if your code still calls `.encode()`, you can leave this or remove it
        self.mock_embed_model.encode.return_value = dummy_vec        
        # Create a mock project path
        self.project_path = Path('/test/project')
        
        # Create a mock table with query method
        self.mock_table = MagicMock()
        
        # Sample modification step
        self.sample_step = {
            'file': 'sample.py',
            'action': 'modify',
            'what': 'Add a new function',
            'how': 'Implement calculate_average function'
        }
        
        # Mock CLI canvas to avoid prints during tests
        self.canvas_patcher = patch('i2c.workflow.modification.rag_retrieval.canvas')
        self.mock_canvas = self.canvas_patcher.start()
        
        # Mock query_context function
        self.query_context_patcher = patch('i2c.workflow.modification.rag_retrieval.query_context')
        self.mock_query_context = self.query_context_patcher.start()
        
    def tearDown(self):
        """Tear down test fixtures."""
        self.canvas_patcher.stop()
        self.query_context_patcher.stop()
    
    def test_retrieve_context_for_step_with_results(self):
        """Test retrieving context for a step when results are available."""
        # Set up mock query results
        mock_results = pd.DataFrame({
            'path': ['file1.py', 'file2.py'],
            'chunk_type': ['function', 'function'],
            'chunk_name': ['calculate_sum', 'process_data'],
            'content': ['def calculate_sum(a, b):\n    return a + b', 'def process_data(data):\n    return data']
        })
        self.mock_query_context.return_value = mock_results
        
        # Call the function
        result = retrieve_context_for_step(self.sample_step, self.mock_table, self.mock_embed_model)
        
        # Verify results
        self.assertIsNotNone(result)
        self.assertIn('calculate_sum', result)
        self.assertIn('process_data', result)
        self.assertIn('Retrieved Context for step', result)
    
    def test_retrieve_context_for_step_with_no_results(self):
        """Test retrieving context for a step when no results are available."""
        # Set up empty query results
        self.mock_query_context.return_value = pd.DataFrame()
        
        # Call the function
        result = retrieve_context_for_step(self.sample_step, self.mock_table, self.mock_embed_model)
        
        # Verify results
        self.assertIsNone(result)
    
    @patch('i2c.agents.modification_team.code_modifier.CodeModifierAgent.run')
    @patch('i2c.workflow.modification.code_executor.retrieve_context_for_step')
    def test_execute_modification_steps_with_context(self, mock_retrieve_context, mock_agent_run):
        """Test executing modification steps with context retrieval."""
        # Set up mocks
        mock_retrieve_context.return_value = "Retrieved context for testing"
        
        # Mock agent response
        mock_response = MagicMock()
        mock_response.content = "def test_function():\n    return 'test'"
        mock_agent_run.return_value = mock_response
        
        # Create a mock Code Modifier agent
        with patch('i2c.workflow.modification.code_executor.code_modifier_agent') as mock_agent:
            # Set up the mock to return the code
            mock_agent.modify_code.return_value = "def test_function():\n    return 'test'"
            
            # Create modification plan
            modification_plan = [self.sample_step]
            
            # Execute the steps
            modified_code_map, files_to_delete = execute_modification_steps(
                modification_plan, 
                self.project_path, 
                self.mock_table, 
                self.mock_embed_model
            )
            
            # Verify that context was retrieved and passed to the agent
            mock_retrieve_context.assert_called_once_with(
                self.sample_step, 
                self.mock_table, 
                self.mock_embed_model
            )
            
            mock_agent.modify_code.assert_called_once()
            # Check that the context was passed to modify_code
            _, kwargs = mock_agent.modify_code.call_args
            self.assertEqual(kwargs['retrieved_context'], "Retrieved context for testing")
            
            # Check the results
            self.assertEqual(len(modified_code_map), 1)
            self.assertEqual(modified_code_map['sample.py'], "def test_function():\n    return 'test'")
            self.assertEqual(len(files_to_delete), 0)



if __name__ == '__main__':
    # Stop the patch after imports so that tearDown can still do cleanup.
    patcher.stop()
    unittest.main()