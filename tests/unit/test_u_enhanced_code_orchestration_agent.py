import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from i2c.agents.code_orchestration_agent import CodeOrchestrationAgent, OrchestrationResult


class MockKnowledgeBase:
    """Mock knowledge base for testing"""
    
    def __init__(self, mock_data=None):
        self.mock_data = mock_data or []
        self.retrieve_calls = []
    
    def retrieve_knowledge(self, query, limit=5):
        """Mock retrieve_knowledge method that records calls and returns mock data"""
        self.retrieve_calls.append({"query": query, "limit": limit})
        return self.mock_data


class TestCodeOrchestrationAgent(unittest.TestCase):
    """Test cases for the knowledge-enhanced code orchestration agent"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Sample objective for testing
        self.test_objective = {
            "task": "Create a user authentication system",
            "constraints": ["Use JWT tokens", "Hash passwords with bcrypt"],
            "quality_gates": ["security", "performance"],
            "project_path": "/tmp/test_project",
            "architectural_context": {
                "system_type": "fullstack_web_app",
                "architecture_pattern": "clean_architecture"
            }
        }
        
        # Create test session state
        self.test_session_state = {
            "objective": self.test_objective,
            "project_path": "/tmp/test_project",
            "task": "Create a user authentication system",
            "constraints": ["Use JWT tokens", "Hash passwords with bcrypt"]
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
        
        # Patch os.path.exists for project path checks
        self.path_exists_patch = patch('pathlib.Path.exists', return_value=True)
        self.path_is_dir_patch = patch('pathlib.Path.is_dir', return_value=True)
        self.path_exists_mock = self.path_exists_patch.start()
        self.path_is_dir_mock = self.path_is_dir_patch.start()
        
    def tearDown(self):
        """Clean up test fixtures"""
        self.path_exists_patch.stop()
        self.path_is_dir_patch.stop()

    def test_init_with_knowledge_base(self):
        """Test initialization with knowledge base"""
        # Create agent with knowledge base
        agent = CodeOrchestrationAgent(
            session_state=self.test_session_state,
            knowledge_base=self.mock_knowledge_base
        )
        
        # Verify knowledge base is stored
        self.assertEqual(agent.knowledge_base, self.mock_knowledge_base)
        
        # Verify knowledge base is in session state
        self.assertEqual(
            agent.session_state.get("knowledge_base"), 
            self.mock_knowledge_base
        )
        
        # Verify knowledge context is in instructions
        instructions_str = "\n".join(agent.instructions)
        self.assertIn("KNOWLEDGE CONTEXT", instructions_str)
        self.assertIn("auth_best_practices.md", instructions_str)
        self.assertIn("web_security.md", instructions_str)
    
    def test_init_without_knowledge_base(self):
        """Test initialization without knowledge base (backward compatibility)"""
        # Create agent without knowledge base
        agent = CodeOrchestrationAgent(
            session_state=self.test_session_state,
            knowledge_base=None
        )
        
        # Verify knowledge base is None
        self.assertIsNone(agent.knowledge_base)
        
        # Verify knowledge base is not in session state
        self.assertNotIn("knowledge_base", agent.session_state)
        
        # Verify knowledge context is not in instructions
        instructions_str = "\n".join(agent.instructions)
        self.assertNotIn("KNOWLEDGE CONTEXT", instructions_str)
        self.assertNotIn("auth_best_practices.md", instructions_str)
    
    def test_retrieve_knowledge_context(self):
        """Test knowledge context retrieval function"""
        # Create agent with knowledge base
        agent = CodeOrchestrationAgent(
            session_state=self.test_session_state,
            knowledge_base=self.mock_knowledge_base
        )
        
        # Call retrieve_knowledge_context
        result = agent._retrieve_knowledge_context(
            self.test_objective, 
            self.test_objective.get("architectural_context", {})
        )
        
        # Verify result contains expected content
        self.assertIn("auth_best_practices.md", result)
        self.assertIn("Always hash passwords", result)
        self.assertIn("web_security.md", result)
        
        # Verify queries were made
        self.assertEqual(len(self.mock_knowledge_base.retrieve_calls), 3)
        self.assertIn("user authentication", self.mock_knowledge_base.retrieve_calls[0]["query"])
        
    def test_retrieve_knowledge_context_no_knowledge_base(self):
        """Test knowledge context retrieval with no knowledge base"""
        # Create agent without knowledge base
        agent = CodeOrchestrationAgent(
            session_state=self.test_session_state,
            knowledge_base=None
        )
        
        # Call retrieve_knowledge_context
        result = agent._retrieve_knowledge_context(
            self.test_objective, 
            self.test_objective.get("architectural_context", {})
        )
        
        # Verify empty result
        self.assertEqual(result, "")
        
    def test_retrieve_knowledge_context_no_task(self):
        """Test knowledge context retrieval with no task in objective"""
        # Create agent with knowledge base
        agent = CodeOrchestrationAgent(
            session_state=self.test_session_state,
            knowledge_base=self.mock_knowledge_base
        )
        
        # Create a fresh mock knowledge base for this test to isolate retrieve calls
        isolated_mock_kb = MockKnowledgeBase(self.sample_knowledge)
        
        # Replace the agent's knowledge base with our isolated mock
        agent.knowledge_base = isolated_mock_kb
        
        # Call retrieve_knowledge_context with empty objective
        result = agent._retrieve_knowledge_context(
            {"description": "A project with no task field"}, 
            {}
        )
        
        # Verify empty result
        self.assertEqual(result, "")
        self.assertEqual(len(isolated_mock_kb.retrieve_calls), 0)
    
    @patch('builtins.llm_middle')
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._initialize_teams')
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._initialize_reflective_operators')
    def test_knowledge_integration_in_planning(self, mock_init_ops, mock_init_teams, mock_llm):
        """Test that knowledge context is integrated into planning context"""
        # Create agent with knowledge base
        agent = CodeOrchestrationAgent(
            session_state=self.test_session_state,
            knowledge_base=self.mock_knowledge_base
        )
        
        # Mock knowledge base return value for planning
        self.mock_knowledge_base.retrieve_knowledge = MagicMock(return_value=[
            {
                "source": "planning_best_practices.md",
                "content": "Plan changes incrementally. Use TDD approach."
            }
        ])
        
        # Mock _build_planning_context to capture inputs
        agent._build_planning_context = MagicMock(return_value="Enhanced planning context")
        
        # Call _create_modification_plan
        asyncio.run(agent._create_modification_plan(
            "Create user auth", 
            ["Use JWT"], 
            {"architectural_context": {}}
        ))
        
        # Verify _build_planning_context was called with knowledge context
        args, kwargs = agent._build_planning_context.call_args
        self.assertIn("planning_best_practices.md", args[4])
        knowledge_arg = args[4] if len(args) > 4 else ""
        self.assertIn("Plan changes incrementally", knowledge_arg)
    
    @patch('builtins.llm_middle')
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._initialize_teams')
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._initialize_reflective_operators')
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._setup_teams', new_callable=AsyncMock)
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._analyze_project_context', new_callable=AsyncMock)
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._create_modification_plan', new_callable=AsyncMock)
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._execute_modifications', new_callable=AsyncMock)
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._run_quality_checks', new_callable=AsyncMock)
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._run_operational_checks', new_callable=AsyncMock)
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._make_final_decision')
    def test_execute_with_knowledge(self, mock_decide, mock_sre, mock_quality, 
                                mock_execute, mock_plan, mock_analyze, mock_setup, 
                                mock_init_ops, mock_init_teams, mock_llm):
        """Test the main execute method with knowledge integration"""
        # Set up mocks
        # Set up async mock return values directly
        mock_setup.return_value = None
        mock_analyze.return_value = {"architectural_context": {}}
        mock_plan.return_value = {"steps": []}
        mock_execute.return_value = {"modified_files": {}}
        mock_quality.return_value = {"passed": True}
        mock_sre.return_value = {"passed": True}
        mock_decide.return_value = ("approve", "All tests passed")
            
        # Create agent with knowledge base
        agent = CodeOrchestrationAgent(
            session_state=self.test_session_state,
            knowledge_base=self.mock_knowledge_base
        )
        
        # Add the _clean_results method to the agent for this test
        agent._clean_results = MagicMock(return_value={})
        
        # Execute agent
        result = asyncio.run(agent.execute(self.test_objective))
        
        # Verify knowledge_applied flag is included in result
        self.assertIn("knowledge_applied", result)
        self.assertTrue(result["knowledge_applied"])
        
        # Verify all expected methods were called
        mock_setup.assert_called_once()
        mock_analyze.assert_called_once()
        mock_plan.assert_called_once()
        mock_execute.assert_called_once()
        mock_quality.assert_called_once()
        mock_sre.assert_called_once()
        mock_decide.assert_called_once()
    
    @patch('builtins.llm_middle')
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._initialize_teams')
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._initialize_reflective_operators')
    def test_knowledge_applied_to_self_healing(self, mock_init_ops, mock_init_teams, mock_llm):
        """Test that knowledge is applied to self-healing process"""
        # Create agent with knowledge base
        agent = CodeOrchestrationAgent(
            session_state=self.test_session_state,
            knowledge_base=self.mock_knowledge_base
        )
        
        # Mock knowledge base for specific fix context
        self.mock_knowledge_base.retrieve_knowledge = MagicMock(return_value=[
            {
                "source": "syntax_fixes.md",
                "content": "Always use 4 spaces for indentation in Python."
            }
        ])
        
        # Mock methods to test self-healing
        agent._auto_fix_syntax_issues = AsyncMock()
        agent._auto_fix_syntax_issues.return_value = {
            "modified_files": {"test.py": "fixed code"},
            "auto_fixed": True,
            "knowledge_applied": True
        }
        
        # Test self-healing with syntax issues
        recovery_analysis = {
            "strategy": "auto_fix_syntax",
            "confidence": "high",
            "auto_recoverable": True,
            "issues_found": ["Indentation error in line 10"],
            "patterns_detected": ["syntax_issues"]
        }
        
        modification_result = {"modified_files": {"test.py": "original code"}}
        
        # Execute self-healing
        result = asyncio.run(agent._execute_self_healing(recovery_analysis, modification_result))
        
        # Verify self-healing was called with the right strategy
        agent._auto_fix_syntax_issues.assert_called_once()
        
        # Verify knowledge was applied in the result
        self.assertTrue(result["knowledge_applied"])
    
    @patch('builtins.llm_middle')
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._initialize_teams')
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._initialize_reflective_operators')
    def test_analyze_project_context_with_knowledge(self, mock_init_ops, mock_init_teams, mock_llm):
        """Test that knowledge enhances project context analysis"""
        # Create agent with knowledge base
        agent = CodeOrchestrationAgent(
            session_state=self.test_session_state,
            knowledge_base=self.mock_knowledge_base
        )
        
        # Mock knowledge base for analysis context
        self.mock_knowledge_base.retrieve_knowledge = MagicMock(return_value=[
            {
                "source": "project_analysis.md",
                "content": "Analyze file structure and dependencies first."
            }
        ])
        
        # Mock file system operations
        agent._detect_languages = MagicMock(return_value={"python": 5})
        agent._get_content_samples = MagicMock(return_value={})
        
        # Create empty project path
        project_path = Path("/tmp/test_project")
        
        # Create mock files result
        with patch('pathlib.Path.rglob') as mock_rglob:
            mock_rglob.return_value = []
            
            # Mock architecture agent import to avoid actual import
            with patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._create_fallback_architectural_context') as mock_fallback:
                mock_fallback.return_value = {"system_type": "web_app"}
                
                # Call analyze_project_context
                result = asyncio.run(agent._analyze_project_context(project_path, "Create auth system"))
        
        # Verify knowledge is included in the context section
        self.assertIn("context", result)
        self.assertIn("knowledge_insights", result["context"])
        self.assertIn("project_analysis.md", str(result["context"]["knowledge_insights"]))


if __name__ == "__main__":
    unittest.main()