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
# Knowledge-enhanced agent instantiation
input_processor_agent = None  # Will be created dynamically
planner_agent = None
code_builder_agent = None
project_context_analyzer_agent = None

# Set up factory functions for session state aware instantiation
def get_rag_enabled_agent(agent_type, session_state=None):
    """Get knowledge-enhanced agent with internalized expertise"""
    
    try:
        # Direct instantiation with error handling
        if agent_type == "input_processor":
            agent_class = InputProcessorAgent
        elif agent_type == "planner":
            agent_class = PlannerAgent
        elif agent_type == "code_builder":
            agent_class = CodeBuilderAgent
        elif agent_type == "project_context_analyzer":
            agent_class = ProjectContextAnalyzerAgent
        else:
            canvas.error(f"Unknown agent type: {agent_type}")
            return None
        
        if session_state is None:
            return agent_class()
            
        try:
            # Get knowledge base from session
            knowledge_base = session_state.get("knowledge_base")
            
            # Create knowledge-enhanced agent
            enhanced_agent = create_knowledge_enhanced_agent(
                agent_class, 
                knowledge_base, 
                agent_type
            )
            
            return enhanced_agent
            
        except Exception as e:
            canvas.warning(f"Failed to create enhanced {agent_type}: {e}")
            return agent_class()  # Fallback
            
    except Exception as e:
        canvas.error(f"Error creating agent {agent_type}: {e}")
        return None
print("🤔 [InputProcessorAgent] Ready for dynamic initialization")
print("📋 [PlannerAgent] Ready for dynamic initialization") 
print("🔨 [CodeBuilderAgent] Ready for dynamic initialization")
print("🤔 [ProjectContextAnalyzerAgent] Ready for dynamic initialization")

def _extract_domain_expertise(knowledge_base, agent_role):
    """Extract relevant expertise for specific agent role"""
    
    role_queries = {
        "input_processor": ["requirement analysis", "user story clarification", "project scoping"],
        "planner": ["software architecture", "file structure", "project planning"], 
        "code_builder": ["code generation", "programming patterns", "implementation"],
        "project_analyzer": ["code analysis", "project structure", "architecture review"]
    }
    
    queries = role_queries.get(agent_role.lower(), [agent_role])
    all_expertise = []
    
    for query in queries:
        try:
            # Get principles and patterns for this domain
            principles = knowledge_base.retrieve_knowledge(
                query=f"principles best practices {query}", 
                limit=3
            )
            examples = knowledge_base.retrieve_knowledge(
                query=f"examples patterns {query}",
                limit=2
            )
            
            all_expertise.extend(principles)
            all_expertise.extend(examples)
            
        except Exception:
            continue
    
    return all_expertise[:8]  # Limit to top 8 pieces

def _inject_expertise_into_agent(agent, expertise, agent_role):
    """Inject deep expertise with reasoning chains"""
    
    if not expertise:
        return agent
    
    # Process with deep transformer
    from i2c.agents.knowledge.principle_transformer import DeepPrincipleTransformer
    deep_transformer = DeepPrincipleTransformer()
    
    # Extract contextual patterns from expertise
    contextual_patterns = deep_transformer.extract_contextual_patterns(expertise)
    
    # Create reasoning-based expertise
    reasoning_context = f"""
Your expertise as a {agent_role} includes deep contextual understanding:

{deep_transformer.synthesize_deep_expertise(contextual_patterns)}

REASONING APPROACH:
1. Analyze the context deeply before applying patterns
2. Consider edge cases and potential conflicts
3. Choose the optimal approach based on specific requirements
4. Implement with confidence, knowing when and why to apply each pattern

Think like an expert who naturally reasons through problems using internalized knowledge."""
    
    # Modify agent instructions
    original_instructions = getattr(agent, 'instructions', [])
    if isinstance(original_instructions, list):
        enhanced_instructions = [reasoning_context] + original_instructions
    else:
        enhanced_instructions = reasoning_context + "\n\n" + str(original_instructions)
    
    agent.instructions = enhanced_instructions
    return agent

def create_knowledge_enhanced_agent(base_agent_class, knowledge_base=None, agent_role=""):
    """Create agent with internalized knowledge instead of external references"""
    
    if knowledge_base is None:
        # Return regular agent if no knowledge
        return base_agent_class()
    
    try:
        # Get domain expertise for this agent type
        domain_knowledge = _extract_domain_expertise(knowledge_base, agent_role)
        
        # Create the base agent
        agent = base_agent_class()
        
        # Transform instructions to include internalized expertise
        if domain_knowledge:
            agent = _inject_expertise_into_agent(agent, domain_knowledge, agent_role)
            canvas.success(f"✅ Enhanced {agent_role} with internalized expertise")
        
        return agent
        
    except Exception as e:
        canvas.warning(f"Failed to enhance {agent_role}: {e}")
        return base_agent_class()  # Fallback to regular agent
    
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