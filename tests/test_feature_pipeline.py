# tests/test_feature_pipeline.py
"""Tests for the Feature Pipeline"""
# Load LLMs and set builtins
from llm_providers import initialize_groq_providers
import builtins
(
    builtins.llm_highest,
    builtins.llm_middle,
    builtins.llm_small,
    builtins.llm_xs
) = initialize_groq_providers()
import sys, os 
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json
from datetime import datetime

project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

from models.user_story import UserStory, AcceptanceCriteria, StoryPriority, StoryStatus
from story_manager import StoryManager
from workflow.feature_pipeline import FeaturePipeline
from agents.budget_manager import BudgetManagerAgent



class TestFeaturePipeline(unittest.TestCase):
    """Test cases for Feature Pipeline"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path("/tmp/test_stories")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Mock dependencies
        self.mock_knowledge_manager = Mock()
        self.mock_budget_manager = Mock(spec=BudgetManagerAgent)
        self.mock_embed_model = Mock()
        self.mock_db_connection = Mock()
        
        # Create test story
        self.test_story = UserStory(
            title="Test Feature",
            description="Test description",
            as_a="developer",
            i_want="to test features",
            so_that="I can ensure quality",
            acceptance_criteria=[
                AcceptanceCriteria(description="Test passes")
            ],
            story_id="test_123"
        )
        
        # Initialize managers
        self.story_manager = StoryManager(
            storage_path=self.temp_dir,
            knowledge_manager=self.mock_knowledge_manager
        )
        
        # Create pipeline
        self.pipeline = FeaturePipeline(
            project_path=self.temp_dir,
            story_manager=self.story_manager,
            budget_manager=self.mock_budget_manager,
            embed_model=self.mock_embed_model,
            db_connection=self.mock_db_connection
        )
    
    def tearDown(self):
        """Clean up after tests"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_process_story_success(self):
        """Test successful story processing"""
        # Setup mocks
        self.story_manager.stories["test_123"] = self.test_story
        
        # Mock agent responses
        self.pipeline.doc_retriever.execute = Mock(return_value=(True, {"documents": []}))
        self.pipeline.best_practices.execute = Mock(return_value=(True, {"best_practices": []}))
        self.pipeline.plan_refiner.execute = Mock(return_value=(True, {"plan": []}))
        
        # Mock execute_modification_cycle
        with patch('workflow.feature_pipeline.execute_modification_cycle') as mock_execute:
            mock_execute.return_value = {"success": True, "code_map": {}}
            
            # Process story
            success, result = self.pipeline.process_story("test_123")
            
            self.assertTrue(success)
            self.assertIn("context", result)
            self.assertIn("plan", result)
            self.assertIn("implementation", result)
    
    def test_process_story_with_issues(self):
        """Test story processing with issues that need resolution"""
        # Setup mocks
        self.story_manager.stories["test_123"] = self.test_story
        
        # Create a dummy test.py file where the pipeline expects it
        test_file_path = self.temp_dir / "test.py"
        test_file_path.write_text("def test_dummy(): assert True")      
        
        # Mock agent responses
        self.pipeline.doc_retriever.execute = Mock(return_value=(True, {"documents": []}))
        self.pipeline.best_practices.execute = Mock(return_value=(True, {"best_practices": []}))
        self.pipeline.plan_refiner.execute = Mock(return_value=(True, {"plan": []}))
        self.pipeline.issue_resolver.execute = Mock(return_value=(True, {"fixed_content": "fixed"}))
        
        # Mock execute_modification_cycle with issues
        with patch('workflow.feature_pipeline.execute_modification_cycle') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "code_map": {},
                "test_failures": {"test.py": {"error": "test failed"}}
            }
            
            # Process story
            success, result = self.pipeline.process_story("test_123")
            
            self.assertTrue(success)
            self.assertIn("resolution", result)
    
    def test_process_story_not_found(self):
        """Test processing non-existent story"""
        success, result = self.pipeline.process_story("nonexistent")
        
        self.assertFalse(success)
        self.assertEqual(result["error"], "Story not found")
    
    def test_gather_context(self):
        """Test context gathering"""
        # Mock knowledge retrieval
        self.story_manager.get_story_context = Mock(return_value=[{"content": "test"}])
        self.pipeline.doc_retriever.execute = Mock(return_value=(True, {"documents": []}))
        
        with patch('workflow.feature_pipeline.retrieve_combined_context') as mock_retrieve:
            mock_retrieve.return_value = {
                "code_context": "code context",
                "knowledge_context": "knowledge context"
            }
            
            result = self.pipeline._gather_context(self.test_story)
            
            self.assertTrue(result["success"])
            self.assertIn("story_context", result)
            self.assertIn("documentation", result)
            self.assertEqual(result["code_context"], "code context")
    
    def test_generate_plan(self):
        """Test plan generation"""
        context = {
            "code_context": "test context",
            "knowledge_context": "test knowledge"
        }
        
        # Mock agent responses
        self.pipeline.best_practices.execute = Mock(return_value=(
            True, 
            {"best_practices": [{"practice": "test", "rationale": "testing"}]}
        ))
        self.pipeline.plan_refiner.execute = Mock(return_value=(
            True,
            {"plan": [{"file": "test.py", "action": "create"}]}
        ))
        
        result = self.pipeline._generate_plan(self.test_story, context)
        
        self.assertTrue(result["success"])
        self.assertIn("initial_plan", result)
        self.assertIn("refined_plan", result)
        self.assertIn("best_practices", result)
    
    def test_implement_feature(self):
        """Test feature implementation"""
        plan_result = {
            "refined_plan": [{"file": "test.py", "action": "create"}]
        }
        
        with patch('workflow.feature_pipeline.execute_modification_cycle') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "code_map": {"test.py": "print('test')"},
                "language": "python"
            }
            
            result = self.pipeline._implement_feature(self.test_story, plan_result)
            
            self.assertTrue(result["success"])
            self.assertIn("code_map", result)
            self.assertEqual(result["language"], "python")
    
    def test_resolve_issues(self):
        """Test issue resolution"""
        issues = [
            {
                "type": "test_failure",
                "file": "test.py",
                "details": {"error": "assertion failed"}
            }
        ]
        
        # Create test file
        test_file = self.temp_dir / "test.py"
        test_file.write_text("def test(): assert False")
        
        # Mock issue resolver
        self.pipeline.issue_resolver.execute = Mock(return_value=(
            True,
            {"fixed_content": "def test(): assert True"}
        ))
        
        result = self.pipeline._resolve_issues(issues)
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["resolved_issues"]), 1)
        self.assertEqual(len(result["unresolved_issues"]), 0)
        
        # Check if file was updated
        self.assertEqual(test_file.read_text(), "def test(): assert True")


if __name__ == "__main__":
    unittest.main()