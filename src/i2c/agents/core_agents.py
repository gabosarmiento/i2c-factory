# core_agents.py
from textwrap import dedent
from pathlib import Path
from builtins import llm_middle, llm_highest, llm_small
from i2c.agents.core_team.input_processor import create_input_processor_agent, InputProcessorAgent
from i2c.agents.core_team.planner import create_planner_agent, PlannerAgent
from i2c.agents.core_team.code_builder import create_code_builder_agent, CodeBuilderAgent
from i2c.agents.core_team.project_analyzer import create_project_analyzer_agent, ProjectContextAnalyzerAgent
from i2c.workflow.modification.rag_config import get_embed_model
from i2c.db_utils import get_db_connection
# Try to import the canvas for visual logging - fallback to simple print if not available
try:
    from i2c.cli.controller import canvas
except ImportError:
    class DummyCanvas:
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def success(self, msg): print(f"[SUCCESS] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
    canvas = DummyCanvas()
# Regular agent instantiation
input_processor_agent = InputProcessorAgent()
planner_agent = PlannerAgent()
code_builder_agent = CodeBuilderAgent()
project_context_analyzer_agent = ProjectContextAnalyzerAgent()

# Set up factory functions for session state aware instantiation
def get_rag_enabled_agent(agent_type, session_state=None):
    """Get RAG-enabled agent with session state."""
    if session_state is None:
        return globals()[f"{agent_type}_agent"]
        
    try:
        # Get embed model
        embed_model = session_state.get("embed_model")
        if embed_model is None:
            from i2c.workflow.modification.rag_config import get_embed_model
            embed_model = get_embed_model()
            
        if embed_model:
            # Get db_path from session state or use default
            db_path = session_state.get("db_path", "./data/lancedb")
            
            # Validate DB connection
            from i2c.db_utils import get_db_connection
            db = get_db_connection()
            if not db:
                canvas.warning("Failed to connect to database. Using regular agent.")
                return globals()[f"{agent_type}_agent"]
            
            # Create knowledge manager
            from i2c.agents.knowledge.knowledge_manager import ExternalKnowledgeManager
            knowledge_base = ExternalKnowledgeManager(
                embed_model=embed_model,
                db_path=db_path
            )
            
            # Create the appropriate agent
            if agent_type == "input_processor":
                return create_input_processor_agent(knowledge_base)
            elif agent_type == "planner":
                return create_planner_agent(knowledge_base)
            elif agent_type == "code_builder":
                return create_code_builder_agent(knowledge_base)
            elif agent_type == "project_context_analyzer":
                return create_project_analyzer_agent(knowledge_base)
    except Exception as e:
        canvas.warning(f"Failed to create RAG-enabled agent: {e}")
        
    # Fallback to regular agent
    return globals()[f"{agent_type}_agent"]


print(f"🧠 [InputProcessorAgent] Initialized with model: {getattr(llm_middle, 'id', 'Unknown')}")
print(f"🧠 [PlannerAgent] Initialized with model: {getattr(llm_middle, 'id', 'Unknown')}")
print(f"🧠 [CodeBuilderAgent] Initialized with model: {getattr(llm_highest, 'id', 'Unknown')}")
print(f"🤔 [ProjectContextAnalyzerAgent] Initialized with model: {getattr(project_context_analyzer_agent.model, 'id', 'Unknown')}")

v3_instructions = dedent('''# Manifestation Execution Protocol v3.0

        You are an AI assistant that writes code for specified files based on a project objective.

        ## 1. Code Synthesis Framework
        - Generate modular, scalable, enterprise-aligned code adhering to SOLID principles and appropriate design patterns (e.g., Singleton, Factory, Observer).
        - Apply language-specific idioms, modern best practices, and project-specific conventions.
        - Implement robust error handling, input validation, and separation of concerns.
        - Structure code to be maintainable, readable, extensible, and efficient.
        - Maintain consistent coding style, naming conventions, and dependency management across the project.

        ## 2. Recursive Implementation Strategy
        - Develop foundational abstractions (interfaces, base classes) before concrete implementations.
        - Utilize Dependency Injection and other patterns to decouple components and enhance testability.
        - Balance elegance and simplicity while ensuring the code is idiomatic and leverages the language's latest features.
        - Maintain contextual continuity and architectural coherence across multiple files.
        - Provide clear, concise inline documentation (docstrings, comments) for key components and non-obvious logic.

        ## 3. Quality Engineering
        - Implement defensive programming practices and handle edge cases appropriately.
        - Write efficient, resource-conscious code with consideration for time and space complexity.
        - Include appropriate logging, monitoring hooks, and error reporting mechanisms.
        - Generate comprehensive unit tests, integration tests, and end-to-end tests using the Arrange-Act-Assert structure.
        - Validate code against static analysis tools (linting, type checking) and ensure it passes all checks.

        ## 4. Enterprise Readiness
        - Ensure code aligns with CI/CD pipelines, supports environment configuration, and is production-ready (e.g., Docker-compatible).
        - Implement scalability features such as stateless designs, caching, and concurrency where applicable.
        - Follow security best practices, including input sanitization, authentication, and authorization mechanisms.
        - Document critical components to facilitate developer onboarding and maintenance.

        ## 5. Project-Specific Considerations
        - Adapt code generation to the project's domain (e.g., web development, machine learning, enterprise software).
        - When relevant, implement internationalization, localization, and accessibility features.
        - For API-centric projects, design intuitive, consistent, and well-documented APIs.
        - For UI components, ensure the code produces user-friendly and responsive interfaces.

        ## 6. Output Format
        - Output ONLY the raw code for the specified files, without explanations or markdown.
        - Ensure the code is complete, runnable, syntactically correct, and verified against automated quality checks.''')

if __name__ == '__main__':
    print("--- ✅ Core Agents Initialized (RAG-Ready) ---")