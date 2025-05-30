import unittest
from unittest.mock import MagicMock, patch
import json

from i2c.workflow.orchestration_team import build_orchestration_team, _retrieve_knowledge_context


class MockKnowledgeBase:
    """Mock knowledge base for testing"""
    
    def __init__(self, mock_data=None):
        self.mock_data = mock_data or []
        self.retrieve_calls = []
    
    def retrieve_knowledge(self, query, limit=5):
        """Mock retrieve_knowledge method that records calls and returns mock data"""
        self.retrieve_calls.append({"query": query, "limit": limit})
        return self.mock_data


class TestOrchestrationTeam(unittest.TestCase):
    """Test cases for the enhanced orchestration team with knowledge integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Sample objective for testing
        self.test_objective = {
            "task": "Create a user authentication system",
            "architectural_context": {
                "system_type": "fullstack_web_app",
                "architecture_pattern": "clean_architecture"
            }
        }
        
        # Sample knowledge chunks for mocking
        self.sample_knowledge = [
            {
                "source": "auth_best_practices.md",
                "content": "Always hash passwords using bcrypt or Argon2. Never store plain text passwords."
            },
            {
                "source": "web_security.md",
                "content": "Implement CSRF protection for all forms. Use HTTPS for all communications."
            }
        ]
        
        # Create a mock knowledge base
        self.mock_knowledge_base = MockKnowledgeBase(self.sample_knowledge)

    def test_retrieve_knowledge_context(self):
        """Test knowledge context retrieval function"""
        objective = {"task": "Implement user authentication"}
        arch_context = {"system_type": "web_app", "architecture_pattern": "mvc"}
        
        # Test with valid knowledge base
        result = _retrieve_knowledge_context(self.mock_knowledge_base, objective, arch_context)
        
        # Verify result contains expected content
        self.assertIn("auth_best_practices.md", result)
        self.assertIn("Always hash passwords", result)
        self.assertIn("web_security.md", result)
        
        # Verify queries were made
        self.assertEqual(len(self.mock_knowledge_base.retrieve_calls), 3)
        self.assertIn("user authentication", self.mock_knowledge_base.retrieve_calls[0]["query"])
        
    def test_retrieve_knowledge_context_no_knowledge_base(self):
        """Test knowledge context retrieval with no knowledge base"""
        objective = {"task": "Implement user authentication"}
        arch_context = {"system_type": "web_app", "architecture_pattern": "mvc"}
        
        # Test with no knowledge base
        result = _retrieve_knowledge_context(None, objective, arch_context)
        
        # Verify empty result
        self.assertEqual(result, "")
        
    def test_retrieve_knowledge_context_no_task(self):
        """Test knowledge context retrieval with no task in objective"""
        objective = {"description": "A project with no task field"}
        arch_context = {"system_type": "web_app"}
        
        # Test with valid knowledge base but no task
        result = _retrieve_knowledge_context(self.mock_knowledge_base, objective, arch_context)
        
        # Verify empty result
        self.assertEqual(result, "")
        self.assertEqual(len(self.mock_knowledge_base.retrieve_calls), 0)

    @patch('builtins.llm_highest')
    def test_build_orchestration_team_with_knowledge(self, mock_llm):
        """Test building an orchestration team with knowledge integration"""
        # Set up session state with objective
        session_state = {"objective": self.test_objective}
        
        # Build team with knowledge base
        team = build_orchestration_team(
            initial_session_state=session_state,
            knowledge_base=self.mock_knowledge_base
        )
        
        # Verify team was created successfully
        self.assertEqual(team.name, "CodeEvolutionTeam")
        self.assertEqual(len(team.members), 1)
        
        # Verify knowledge base is in session state
        self.assertEqual(
            team.session_state.get("knowledge_base"), 
            self.mock_knowledge_base
        )
        
        # Verify knowledge context is in instructions
        instructions_str = "\n".join(team.instructions)
        self.assertIn("=== KNOWLEDGE CONTEXT ===", instructions_str)
        self.assertIn("auth_best_practices.md", instructions_str)
        self.assertIn("web_security.md", instructions_str)

    @patch('builtins.llm_highest')
    def test_build_orchestration_team_no_knowledge(self, mock_llm):
        """Test building an orchestration team without knowledge base (backward compatibility)"""
        # Set up session state with objective
        session_state = {"objective": self.test_objective}
        
        # Build team without knowledge base
        team = build_orchestration_team(
            initial_session_state=session_state,
            knowledge_base=None
        )
        
        # Verify team was created successfully
        self.assertEqual(team.name, "CodeEvolutionTeam")
        self.assertEqual(len(team.members), 1)
        
        # Verify knowledge base is not in session state
        self.assertNotIn("knowledge_base", team.session_state)
        
        # Verify knowledge context is not in instructions
        instructions_str = "\n".join(team.instructions)
        self.assertNotIn("=== KNOWLEDGE CONTEXT ===", instructions_str)
        self.assertNotIn("auth_best_practices.md", instructions_str)

    @patch('agno.team.Team.run')
    def test_team_execution(self, mock_run):
        """Test team execution with knowledge context"""
        # Set up mock response
        mock_result = MagicMock()
        mock_result.content = json.dumps({
            "decision": "approve",
            "reason": "All checks passed with knowledge context applied",
            "modifications": {"auth.py": "Added bcrypt password hashing"},
            "quality_results": {"security": "passed"},
            "reasoning_trajectory": [
                {"step": "Knowledge Application", "description": "Applied password hashing best practices"}
            ]
        })
        mock_run.return_value = mock_result
        
        # Set up session state with objective
        session_state = {"objective": self.test_objective}
        
        # Build team with knowledge base
        team = build_orchestration_team(
            initial_session_state=session_state,
            knowledge_base=self.mock_knowledge_base
        )
        
        # Execute team
        message = {"task": "Implement user authentication"}
        result = team.run(message)
        
        # Verify run was called
        mock_run.assert_called_once()
        
        # Verify result contains knowledge-informed content
        result_json = json.loads(result.content)
        self.assertEqual(result_json["decision"], "approve")
        self.assertIn("knowledge", result_json["reason"].lower())
        self.assertIn("bcrypt", result_json["modifications"]["auth.py"])


if __name__ == "__main__":
    unittest.main()