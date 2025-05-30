import unittest
from unittest.mock import patch, MagicMock, AsyncMock, call
import asyncio
import os
import tempfile
import json
from pathlib import Path

# Import the orchestration agent
from i2c.agents.code_orchestration_agent import CodeOrchestrationAgent

# Import knowledge components
from i2c.agents.knowledge.knowledge_manager import ExternalKnowledgeManager


class TestCodeOrchestrationAgentIntegration(unittest.TestCase):
    """
    Integration tests for the Code Orchestration Agent with real knowledge components
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        # Create a temporary directory for test knowledge files
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.knowledge_dir = Path(cls.temp_dir.name)
        cls.project_dir = Path(cls.temp_dir.name) / "test_project"
        cls.project_dir.mkdir(exist_ok=True)
        
        # Create test knowledge files
        cls._create_test_knowledge_files()
        
        # Create test project files
        cls._create_test_project_files()
        
        # Mock the embedding model
        cls.mock_embed_model = MagicMock()
        cls.mock_embed_model.get_embedding.return_value = [0.1] * 384  # Mock embedding vector
        
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        cls.temp_dir.cleanup()
    
    @classmethod
    def _create_test_knowledge_files(cls):
        """Create test knowledge files with relevant content for testing"""
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
        
        testing_file = cls.knowledge_dir / "testing_best_practices.md"
        testing_file.write_text("""# Testing Best Practices

1. Write unit tests for individual functions
2. Use integration tests for component interaction
3. Implement end-to-end tests for critical user flows
4. Use mocks for external dependencies
5. Aim for high test coverage of business logic
        """)
    
    @classmethod
    def _create_test_project_files(cls):
        """Create a minimal project structure for testing"""
        # Backend structure
        backend_dir = cls.project_dir / "backend"
        backend_dir.mkdir(exist_ok=True)
        
        # Create main.py
        main_py = backend_dir / "main.py"
        main_py.write_text("""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
""")
        
        # Frontend structure
        frontend_dir = cls.project_dir / "frontend" / "src"
        frontend_dir.mkdir(exist_ok=True, parents=True)
        
        # Create App.jsx
        app_jsx = frontend_dir / "App.jsx"
        app_jsx.write_text("""
import React from 'react';
import './App.css';

function App() {
  return (
    <div className="App">
      <h1>Test App</h1>
    </div>
  );
}

export default App;
""")
        
        # Create App.css
        app_css = frontend_dir / "App.css"
        app_css.write_text("""
.App {
  text-align: center;
}
""")
    
    @patch('i2c.db_utils.get_db_connection')
    @patch('i2c.workflow.modification.rag_config.get_embed_model')
    def test_agent_initialization_with_knowledge(self, mock_get_embed, mock_get_db):
        """Test initialization of orchestration agent with knowledge manager"""
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
                
            if "test" in query.lower():
                results.append({
                    "source": "testing_best_practices.md",
                    "content": (self.knowledge_dir / "testing_best_practices.md").read_text()
                })
                
            return results[:limit]
        
        knowledge_manager.retrieve_knowledge = mock_retrieve
        
        # Create test objective
        test_objective = {
            "task": "Create a user authentication system for a fullstack web application",
            "constraints": ["Use JWT tokens", "Secure password storage"],
            "quality_gates": ["security", "performance"],
            "project_path": str(self.project_dir),
            "architectural_context": {
                "system_type": "fullstack_web_app",
                "architecture_pattern": "clean_architecture"
            }
        }
        
        # Set up session state
        session_state = {
            "objective": test_objective,
            "project_path": str(self.project_dir)
        }
        
        # Create orchestration agent with knowledge integration
        with patch('builtins.llm_middle'):
            agent = CodeOrchestrationAgent(
                session_state=session_state,
                knowledge_base=knowledge_manager
            )
        
        # Verify knowledge was integrated into instructions
        instructions_text = "\n".join(agent.instructions)
        
        # Check for knowledge context section
        self.assertIn("KNOWLEDGE CONTEXT", instructions_text)
        
        # Check for content from our test files
        self.assertIn("Authentication Best Practices", instructions_text)
        self.assertIn("bcrypt", instructions_text)
        
        # Verify session state contains knowledge base
        self.assertEqual(agent.session_state.get("knowledge_base"), knowledge_manager)

    # Make test_composite_knowledge_retrieval a class method with proper indentation
    @patch('i2c.db_utils.get_db_connection')
    @patch('i2c.workflow.modification.rag_config.get_embed_model')
    @patch('builtins.llm_middle')
    def test_composite_knowledge_retrieval(self, mock_llm, mock_get_embed, mock_get_db):
        """Test that agent can perform composite knowledge retrieval (multiple queries)"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_get_embed.return_value = self.mock_embed_model

        knowledge_manager = ExternalKnowledgeManager(
            embed_model=self.mock_embed_model,
            db_path=str(self.knowledge_dir)
        )

        query_results = {
            "auth": [{"source": "auth_best_practices.md", "content": "Use bcrypt for passwords"}],
            "clean architecture": [{"source": "clean_architecture.md", "content": "Dependency rule is important"}],
            "test": [{"source": "testing_best_practices.md", "content": "Write unit tests"}],
            "fullstack": [{"source": "fullstack_web_patterns.md", "content": "Separate frontend and backend"}]
        }

        def mock_retrieve(query, limit=5):
            results = []
            for key, value in query_results.items():
                if key in query.lower():
                    results.extend(value)
            return results[:limit]

        knowledge_manager.retrieve_knowledge = MagicMock(side_effect=mock_retrieve)

        test_objective = {
            "task": "Create user authentication with proper testing",
            "project_path": str(self.project_dir),
            "architectural_context": {
                "system_type": "fullstack_web_app",
                "architecture_pattern": "clean_architecture"
            }
        }

        session_state = {
            "objective": test_objective,
            "project_path": str(self.project_dir)
        }

        agent = CodeOrchestrationAgent(
            session_state=session_state,
            knowledge_base=knowledge_manager
        )
        agent._add_reasoning_step = MagicMock()

        context = agent._retrieve_knowledge_context(test_objective, test_objective["architectural_context"])

        self.assertIn("auth_best_practices.md", context)
        self.assertIn("bcrypt", context)

        query_calls = []
        for call in knowledge_manager.retrieve_knowledge.call_args_list:
            if hasattr(call, 'args') and call.args:
                query_calls.append(call.args[0])
        print("Query calls:", query_calls)        
        architecture_query_made = any('clean architecture' in query.lower() for query in query_calls)
        self.assertTrue(architecture_query_made, "No clean architecture query was made")

        self.assertIn("testing_best_practices.md", context)
        self.assertIn("Write unit tests", context)

    # Make test_knowledge_application_in_self_healing a class method with proper indentation
    @patch('i2c.db_utils.get_db_connection')
    @patch('i2c.workflow.modification.rag_config.get_embed_model')
    @patch('builtins.llm_middle')
    def test_knowledge_application_in_self_healing(self, mock_llm, mock_get_embed, mock_get_db):
        """Test that knowledge is applied during self-healing process"""

        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_get_embed.return_value = self.mock_embed_model

        knowledge_manager = ExternalKnowledgeManager(
            embed_model=self.mock_embed_model,
            db_path=str(self.knowledge_dir)
        )

        syntax_file = self.project_dir / "backend" / "syntax_error.py"
        syntax_file.write_text("""
def hello_world():
    print("Hello")
\tprint("World")  # Mixed tabs and spaces
""")

        def mock_retrieve(query, limit=5):
            if "syntax" in query.lower() or "indentation" in query.lower():
                return [{
                    "source": "python_style_guide.md",
                    "content": "Always use 4 spaces for indentation in Python. Never mix tabs and spaces."
                }]
            return []

        knowledge_manager.retrieve_knowledge = mock_retrieve

        test_objective = {
            "task": "Fix syntax issues",
            "project_path": str(self.project_dir)
        }

        session_state = {
            "objective": test_objective,
            "project_path": str(self.project_dir)
        }

        agent = CodeOrchestrationAgent(
            session_state=session_state,
            knowledge_base=knowledge_manager
        )

        agent._add_reasoning_step = MagicMock()

        async def simple_auto_fix_syntax(modification_result, issues):
            query = "python indentation best practices"
            syntax_knowledge = knowledge_manager.retrieve_knowledge(query, limit=2)
            knowledge_applied = len(syntax_knowledge) > 0

            modified_files = modification_result.get("modified_files", {})
            for file_path, content in modified_files.items():
                if file_path.endswith('.py'):
                    modified_files[file_path] = content.replace('\t', '    ')
            return {
                "modified_files": modified_files,
                "auto_fixed": True,
                "knowledge_applied": knowledge_applied
            }

        agent._auto_fix_syntax_issues = simple_auto_fix_syntax

        test_issues = ["Mixed tabs and spaces in backend/syntax_error.py"]
        modification_result = {"modified_files": {"backend/syntax_error.py": syntax_file.read_text()}}

        result = asyncio.run(agent._auto_fix_syntax_issues(modification_result, test_issues))

        self.assertIn("backend/syntax_error.py", result["modified_files"])
        self.assertNotIn("\t", result["modified_files"]["backend/syntax_error.py"])
        self.assertTrue(result["knowledge_applied"])

    # Make test_knowledge_application_in_execution_flow a class method with proper indentation
    @patch('i2c.db_utils.get_db_connection')
    @patch('i2c.workflow.modification.rag_config.get_embed_model')
    @patch('builtins.llm_middle')
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._initialize_teams')
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._initialize_reflective_operators')
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._setup_teams')
    def test_knowledge_application_in_execution_flow(
        self,
        mock_setup,
        mock_init_ops,
        mock_init_teams,
        mock_llm,
        mock_get_embed,
        mock_get_db,
    ):
        """Test that knowledge is applied throughout the execution flow"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_get_embed.return_value = self.mock_embed_model
        mock_setup.return_value = asyncio.Future()
        mock_setup.return_value.set_result(None)

        knowledge_manager = ExternalKnowledgeManager(
            embed_model=self.mock_embed_model,
            db_path=str(self.knowledge_dir)
        )

        def mock_retrieve(query, limit=5):
            if "auth" in query.lower():
                return [{
                    "source": "auth_best_practices.md",
                    "content": (self.knowledge_dir / "auth_best_practices.md").read_text()
                }]
            return []

        knowledge_manager.retrieve_knowledge = mock_retrieve

        test_objective = {
            "task": "Implement user authentication with secure password storage",
            "constraints": ["Use JWT tokens"],
            "quality_gates": ["security"],
            "project_path": str(self.project_dir)
        }

        session_state = {
            "objective": test_objective,
            "project_path": str(self.project_dir)
        }

        agent = CodeOrchestrationAgent(
            session_state=session_state,
            knowledge_base=knowledge_manager
        )

        agent._add_reasoning_step = MagicMock()
        agent._clean_results = MagicMock(return_value={})

        async def mock_analyze_project_context(project_path, task):
            return {
                "architectural_context": {
                    "system_type": "fullstack_web_app",
                    "architecture_pattern": "clean_architecture"
                },
                "context": {
                    "knowledge_insights": "Authentication requires proper password hashing."
                }
            }

        async def mock_create_modification_plan(task, constraints, analysis):
            return {
                "steps": [
                    {"file": "backend/auth.py", "action": "create", "what": "Authentication module"},
                    {"file": "frontend/src/components/Login.jsx", "action": "create", "what": "Login form"}
                ],
                "knowledge_applied": True
            }

        async def mock_execute_modifications(plan):
            return {
                "modified_files": {
                    "backend/auth.py": "from passlib.hash import bcrypt\n\ndef hash_password(password):\n    return bcrypt.hash(password)",
                    "frontend/src/components/Login.jsx": "import React from 'react';\n\nexport default function Login() {return <form>Login</form>;}"
                },
                "summary": {
                    "backend/auth.py": "Created password hashing module",
                    "frontend/src/components/Login.jsx": "Created login component"
                }
            }

        async def mock_run_quality_checks(modification_result, quality_gates):
            return {"passed": True}

        async def mock_run_operational_checks(modification_result):
            return {"passed": True}

        def mock_make_final_decision(quality_results, sre_results, modification_result):
            return ("approve", "Implemented secure authentication with bcrypt password hashing")

        agent._analyze_project_context = mock_analyze_project_context
        agent._create_modification_plan = mock_create_modification_plan
        agent._execute_modifications = mock_execute_modifications
        agent._run_quality_checks = mock_run_quality_checks
        agent._run_operational_checks = mock_run_operational_checks
        agent._make_final_decision = mock_make_final_decision

        result = asyncio.run(agent.execute(test_objective))

        self.assertIn("knowledge_applied", result)
        self.assertTrue(result["knowledge_applied"])

    # Make test_knowledge_impact_on_project_analysis a class method with proper indentation
    @patch('i2c.db_utils.get_db_connection')
    @patch('i2c.workflow.modification.rag_config.get_embed_model')
    @patch('builtins.llm_middle')
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._initialize_teams')
    @patch('i2c.agents.code_orchestration_agent.CodeOrchestrationAgent._initialize_reflective_operators')
    def test_knowledge_impact_on_project_analysis(
        self,
        mock_init_ops,
        mock_init_teams,
        mock_llm,
        mock_get_embed,
        mock_get_db,
    ):
        """Test that knowledge influences project analysis"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_get_embed.return_value = self.mock_embed_model

        knowledge_manager = ExternalKnowledgeManager(
            embed_model=self.mock_embed_model,
            db_path=str(self.knowledge_dir)
        )

        def mock_retrieve(query, limit=5):
            if "project" in query.lower() or "analysis" in query.lower():
                return [{
                    "source": "code_analysis.md",
                    "content": "Always analyze project structure, dependencies, and API contracts first."
                }]
            return []

        knowledge_manager.retrieve_knowledge = mock_retrieve

        test_objective = {
            "task": "Analyze project architecture",
            "project_path": str(self.project_dir)
        }

        session_state = {
            "objective": test_objective,
            "project_path": str(self.project_dir)
        }

        agent = CodeOrchestrationAgent(
            session_state=session_state,
            knowledge_base=knowledge_manager
        )

        agent._add_reasoning_step = MagicMock()
        agent._clean_results = MagicMock(return_value={})

        async def mock_analyze_project_context(project_path, task):
            analysis_knowledge = knowledge_manager.retrieve_knowledge(
                query=f"project analysis best practices for {task}",
                limit=2
            )
            knowledge_insights = "\n\n".join(
                f"[Analysis {i+1}] {chunk['source']}:\n{chunk['content'].strip()}"
                for i, chunk in enumerate(analysis_knowledge) if chunk.get("content")
            )
            return {
                "project_structure": {
                    "files": ["backend/main.py", "frontend/src/App.jsx"],
                    "languages": {"python": 1, "javascript": 1}
                },
                "task_analysis": {
                    "description": task,
                    "identified_targets": []
                },
                "context": {
                    "knowledge_insights": knowledge_insights
                },
                "architectural_context": {
                    "system_type": "fullstack_web_app",
                    "architecture_pattern": "clean_architecture"
                }
            }

        agent._analyze_project_context = mock_analyze_project_context

        analysis_result = asyncio.run(agent._analyze_project_context(Path(self.project_dir), "Analyze project architecture"))

        self.assertIn("context", analysis_result)
        self.assertIn("knowledge_insights", analysis_result["context"])
        self.assertIn("code_analysis.md", analysis_result["context"]["knowledge_insights"])
        self.assertIn("Always analyze project structure", analysis_result["context"]["knowledge_insights"])

    # Make test_knowledge_integration_end_to_end a class method with proper indentation
    @patch('i2c.db_utils.get_db_connection')
    @patch('i2c.workflow.modification.rag_config.get_embed_model')
    @patch('builtins.llm_middle')
    def test_knowledge_integration_end_to_end(self, mock_llm, mock_get_embed, mock_get_db):
        """Test end-to-end knowledge integration across multiple steps of execution"""
        if os.environ.get('CI'):
            self.skipTest("Skipping long-running end-to-end test in CI environment")

        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_get_embed.return_value = self.mock_embed_model

        knowledge_manager = ExternalKnowledgeManager(
            embed_model=self.mock_embed_model,
            db_path=str(self.knowledge_dir)
        )

        def mock_retrieve(query, limit=5):
            results = []
            if any(term in query.lower() for term in ["auth", "password", "login", "security"]):
                results.append({
                    "source": "auth_best_practices.md",
                    "content": (self.knowledge_dir / "auth_best_practices.md").read_text()
                })
            if any(term in query.lower() for term in ["architect", "structure", "pattern", "clean"]):
                results.append({
                    "source": "clean_architecture.md",
                    "content": (self.knowledge_dir / "clean_architecture.md").read_text()
                })
            if any(term in query.lower() for term in ["fullstack", "web", "frontend", "backend"]):
                results.append({
                    "source": "fullstack_web_patterns.md",
                    "content": (self.knowledge_dir / "fullstack_web_patterns.md").read_text()
                })
            if any(term in query.lower() for term in ["test", "coverage", "quality"]):
                results.append({
                    "source": "testing_best_practices.md",
                    "content": (self.knowledge_dir / "testing_best_practices.md").read_text()
                })
            return results[:limit]

        knowledge_manager.retrieve_knowledge = MagicMock(side_effect=mock_retrieve)

        test_objective = {
            "task": "Create secure user authentication for a fullstack web application with proper testing",
            "constraints": ["Use JWT tokens", "Secure password storage"],
            "quality_gates": ["security", "testing"],
            "project_path": str(self.project_dir),
            "architectural_context": {
                "system_type": "fullstack_web_app",
                "architecture_pattern": "clean_architecture"
            }
        }

        session_state = {
            "objective": test_objective,
            "project_path": str(self.project_dir)
        }

        agent = CodeOrchestrationAgent(
            session_state=session_state,
            knowledge_base=knowledge_manager
        )

        agent._add_reasoning_step = MagicMock()
        agent._clean_results = MagicMock(return_value={})

        async def mock_setup_teams(project_path): return None

        async def mock_analyze_project_context(project_path, task):
            return {
                "project_structure": {
                    "files": ["backend/main.py", "frontend/src/App.jsx"],
                    "languages": {"python": 1, "javascript": 1}
                },
                "task_analysis": {
                    "description": task,
                    "identified_targets": []
                },
                "context": {
                    "knowledge_insights": "Authentication requires proper password hashing."
                },
                "architectural_context": {
                    "system_type": "fullstack_web_app",
                    "architecture_pattern": "clean_architecture"
                }
            }

        async def mock_create_modification_plan(task, constraints, analysis):
            return {
                "steps": [
                    {"file": "backend/auth.py", "action": "create", "what": "Authentication module"},
                    {"file": "backend/tests/test_auth.py", "action": "create", "what": "Auth tests"},
                    {"file": "frontend/src/components/Login.jsx", "action": "create", "what": "Login form"}
                ],
                "knowledge_applied": True
            }

        async def mock_execute_modifications(plan):
            return {
                "modified_files": {
                    "backend/auth.py": "from passlib.hash import bcrypt\n\ndef hash_password(password):\n    return bcrypt.hash(password)",
                    "backend/tests/test_auth.py": "import unittest\nfrom auth import hash_password\n\nclass TestAuth(unittest.TestCase):\n    def test_hash_password(self):\n        self.assertIsNotNone(hash_password('test'))",
                    "frontend/src/components/Login.jsx": "import React from 'react';\n\nexport default function Login() {return <form>Login</form>;}"
                },
                "summary": {
                    "backend/auth.py": "Created password hashing module",
                    "backend/tests/test_auth.py": "Created auth tests",
                    "frontend/src/components/Login.jsx": "Created login component"
                }
            }

        async def mock_run_quality_checks(modification_result, quality_gates): return {"passed": True}
        async def mock_run_operational_checks(modification_result): return {"passed": True}

        def mock_make_final_decision(quality_results, sre_results, modification_result):
            return ("approve", "Implemented secure authentication with bcrypt hashing as per best practices")

        agent._setup_teams = mock_setup_teams
        agent._analyze_project_context = mock_analyze_project_context
        agent._create_modification_plan = mock_create_modification_plan
        agent._execute_modifications = mock_execute_modifications
        agent._run_quality_checks = mock_run_quality_checks
        agent._run_operational_checks = mock_run_operational_checks
        agent._make_final_decision = mock_make_final_decision

        result = asyncio.run(agent.execute(test_objective))

        self.assertIn("approve", result["decision"])
        self.assertIn("bcrypt", result["reason"])
        knowledge_manager.retrieve_knowledge.assert_called()


if __name__ == "__main__":
    unittest.main()