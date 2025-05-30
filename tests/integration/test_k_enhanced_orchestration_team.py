import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
import json
from pathlib import Path

# Import the orchestration team builder
from i2c.workflow.orchestration_team import build_orchestration_team

# Import knowledge components
from i2c.agents.knowledge.knowledge_manager import ExternalKnowledgeManager
from i2c.agents.knowledge.enhanced_knowledge_ingestor import EnhancedKnowledgeIngestorAgent


class TestKnowledgeOrchestrationIntegration(unittest.TestCase):
    """
    Integration tests for the orchestration team with real knowledge components
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        # Create a temporary directory for test knowledge files
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.knowledge_dir = Path(cls.temp_dir.name)
        
        # Create test knowledge files
        cls._create_test_knowledge_files()
        
        # Mock the embedding model
        cls.mock_embed_model = MagicMock()
        cls.mock_embed_model.get_embedding.return_value = [0.1] * 384  # Mock embedding vector
        
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        cls.temp_dir.cleanup()
    
    @classmethod
    def _create_test_knowledge_files(cls):
        """Create test knowledge files with relevant content"""
        # Create a few markdown files with relevant content for testing
        auth_file = cls.knowledge_dir / "auth_best_practices.md"
        auth_file.write_text("""# Authentication Best Practices

1. Always use bcrypt or Argon2 for password hashing
2. Implement proper session management with secure cookies
3. Use JWT for stateless authentication
4. Implement rate limiting to prevent brute force attacks
5. Store user credentials in a secure database with encryption
        """)
        
        architecture_file = cls.knowledge_dir / "clean_architecture.md"
        architecture_file.write_text("""# Clean Architecture Principles

1. Dependency Rule: Dependencies point inward, with inner layers having no knowledge of outer layers
2. Entities: Business rules and objects at the core
3. Use Cases: Application-specific business rules
4. Interface Adapters: Convert data between use cases and external format
5. Frameworks & Drivers: External systems, databases, UI, web frameworks
        """)
        
        fullstack_file = cls.knowledge_dir / "fullstack_web_patterns.md"
        fullstack_file.write_text("""# Fullstack Web Application Patterns

1. Separate frontend and backend codebases
2. Use RESTful API for communication
3. Implement proper CORS configuration
4. Follow MVC pattern on the backend
5. Use component-based architecture on the frontend
        """)
    
    @patch('i2c.db_utils.get_db_connection')
    @patch('i2c.workflow.modification.rag_config.get_embed_model')
    def test_knowledge_integration(self, mock_get_embed, mock_get_db):
        """Test integration of knowledge with orchestration team"""
        # Set up mocks
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_get_embed.return_value = self.mock_embed_model
        
        # Create a real knowledge manager
        knowledge_manager = ExternalKnowledgeManager(
            embed_model=self.mock_embed_model,
            db_path=str(self.knowledge_dir)
        )
        
        # Mock the retrieve_knowledge method to return actual content from our test files
        def mock_retrieve(query, limit=5):
            # Simple mock that returns content based on keywords in query
            results = []
            
            if "auth" in query.lower():
                results.append({
                    "source": "auth_best_practices.md",
                    "content": (self.knowledge_dir / "auth_best_practices.md").read_text()
                })
                
            if "clean" in query.lower() or "architect" in query.lower():
                results.append({
                    "source": "clean_architecture.md",
                    "content": (self.knowledge_dir / "clean_architecture.md").read_text()
                })
                
            if "fullstack" in query.lower() or "web" in query.lower():
                results.append({
                    "source": "fullstack_web_patterns.md",
                    "content": (self.knowledge_dir / "fullstack_web_patterns.md").read_text()
                })
                
            return results[:limit]
        
        knowledge_manager.retrieve_knowledge = mock_retrieve
        
        # Create test objective
        test_objective = {
            "task": "Create a user authentication system for a fullstack web application",
            "architectural_context": {
                "system_type": "fullstack_web_app",
                "architecture_pattern": "clean_architecture"
            }
        }
        
        # Set up session state
        session_state = {
            "objective": test_objective,
            "project_path": str(self.knowledge_dir)
        }
        
        # Build orchestration team with knowledge integration
        with patch('builtins.llm_highest'):
            team = build_orchestration_team(
                initial_session_state=session_state,
                knowledge_base=knowledge_manager
            )
        
        # Verify knowledge was integrated into instructions
        instructions_text = "\n".join(team.instructions)
        
        # Check for knowledge context section
        self.assertIn("=== KNOWLEDGE CONTEXT ===", instructions_text)
        
        # Check for content from all three test files
        self.assertIn("Authentication Best Practices", instructions_text)
        self.assertIn("Clean Architecture Principles", instructions_text)
        self.assertIn("Fullstack Web Application Patterns", instructions_text)
        
        # Check for specific best practices
        self.assertIn("bcrypt", instructions_text)
        self.assertIn("Dependency Rule", instructions_text)
        self.assertIn("Separate frontend and backend", instructions_text)
        
        # Verify session state contains knowledge base
        self.assertEqual(team.session_state.get("knowledge_base"), knowledge_manager)
    
    @patch('i2c.db_utils.get_db_connection')
    @patch('i2c.workflow.modification.rag_config.get_embed_model')
    @patch('agno.team.Team.run')
    def test_knowledge_impacts_decision(self, mock_run, mock_get_embed, mock_get_db):
        """Test that knowledge influences orchestration decisions"""
        # Set up mocks
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_get_embed.return_value = self.mock_embed_model
        
        # Create a knowledge manager
        knowledge_manager = ExternalKnowledgeManager(
            embed_model=self.mock_embed_model,
            db_path=str(self.knowledge_dir)
        )
        
        # Mock retrieve_knowledge to return auth best practices
        knowledge_manager.retrieve_knowledge = MagicMock(return_value=[
            {
                "source": "auth_best_practices.md",
                "content": "Always use bcrypt for password hashing. Never store plaintext passwords."
            }
        ])
        
        # Create test objective
        test_objective = {
            "task": "Implement user login functionality",
            "architectural_context": {
                "system_type": "fullstack_web_app",
                "architecture_pattern": "clean_architecture"
            }
        }
        
        # Set up session state
        session_state = {
            "objective": test_objective,
            "project_path": str(self.knowledge_dir)
        }
        
        # Mock team.run response
        mock_result = MagicMock()
        mock_result.content = json.dumps({
            "decision": "approve",
            "reason": "Implemented secure authentication with bcrypt password hashing",
            "modifications": {
                "auth.py": "Added bcrypt password hashing",
                "models/user.py": "Updated User model with password field"
            },
            "quality_results": {"security": "passed"},
            "reasoning_trajectory": [
                {
                    "step": "Knowledge Analysis",
                    "description": "Applied password hashing best practices from knowledge context",
                    "success": True
                }
            ]
        })
        mock_run.return_value = mock_result
        
        # Build and run team
        with patch('builtins.llm_highest'):
            team = build_orchestration_team(
                initial_session_state=session_state,
                knowledge_base=knowledge_manager
            )
            
            # Execute team with a message
            result = team.run("Implement user login with proper security")
        
        # Verify run was called
        mock_run.assert_called_once()
        
        # Verify knowledge influenced the decision
        result_json = json.loads(result.content)
        self.assertEqual(result_json["decision"], "approve")
        self.assertIn("bcrypt", result_json["reason"])
        self.assertIn("bcrypt", result_json["modifications"]["auth.py"])
        
        # Verify reasoning trajectory includes knowledge application
        trajectory = result_json["reasoning_trajectory"]
        self.assertEqual(trajectory[0]["step"], "Knowledge Analysis")
        self.assertIn("knowledge context", trajectory[0]["description"])


if __name__ == "__main__":
    unittest.main()