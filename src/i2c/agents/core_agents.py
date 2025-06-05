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
    
_expertise_cache = {}
# Knowledge-enhanced agent instantiation
# Create default instances to prevent import errors
try:
    input_processor_agent = InputProcessorAgent()
except:
    input_processor_agent = None

try:
    planner_agent = PlannerAgent()
except:
    planner_agent = None

try:
    code_builder_agent = CodeBuilderAgent()
except:
    code_builder_agent = None

try:
    project_context_analyzer_agent = ProjectContextAnalyzerAgent()
except:
    project_context_analyzer_agent = None

# Set up factory functions for session state aware instantiation
def get_rag_enabled_agent(agent_type, session_state=None):
    """Get knowledge-enhanced agent with internalized expertise"""
    
    # DEBUG: Track API route context
    canvas.info(f"🔍 DEBUG: Creating {agent_type} agent")
    if session_state:
        canvas.info(f"🔍 DEBUG: Session state keys: {list(session_state.keys())}")
        if "backend_api_routes" in session_state:
            routes = session_state["backend_api_routes"]
            canvas.info(f"🔍 DEBUG: Found API routes: {routes}")
        else:
            canvas.info(f"🔍 DEBUG: No API routes in session state")
    
    try:
        # Direct instantiation with error handling
        agent_class = None  # Initialize to prevent error
        
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
        
        # Check if agent_class was set
        if agent_class is None:
            canvas.error(f"Failed to resolve agent class for type: {agent_type}")
            return None
        
        # If no session_state, create basic agent
        if session_state is None:
            canvas.warning(f"🔍 DEBUG: No session_state for {agent_type} - creating basic agent")
            return agent_class()

        # DEBUG: Check what's actually in session_state
        canvas.info(f"🔍 DEBUG: session_state keys for {agent_type}: {list(session_state.keys())}") 
        
        try:
            # Get knowledge base from session
            knowledge_base = session_state.get("knowledge_base")
            canvas.info(f"🔍 DEBUG: Knowledge base exists in session: {knowledge_base is not None}")
            
            # If no knowledge base, create basic agent
            if knowledge_base is None:
                canvas.warning(f"🔍 DEBUG: No knowledge_base in session_state for {agent_type}")
                return agent_class()
            
            # Create knowledge-enhanced agent
            enhanced_agent = create_knowledge_enhanced_agent(
                agent_class, 
                knowledge_base, 
                agent_type
            )
            canvas.info(f"🔍 DEBUG: Enhanced agent created: {type(enhanced_agent).__name__}")
            # Log important session state keys only to reduce noise
            important_keys = ['knowledge_base', 'architectural_context', 'retrieved_context', 'backend_api_routes']
            
            if session_state:
                present_important = [key for key in important_keys if key in session_state]
                if present_important:
                    canvas.info(f"🔍 DEBUG: Important session keys present: {', '.join(present_important)}")
                else:
                    canvas.info(f"🔍 DEBUG: No important session keys found in {len(session_state)} total keys")
            
            # Additional enhancement if retrieved_context exists
            if "retrieved_context" in session_state:
                canvas.info(f"🔍 DEBUG: retrieved_context exists, length: {len(session_state['retrieved_context'])}")
                canvas.info(f"🔍 DEBUG: retrieved_context preview: {session_state['retrieved_context'][:200]}...")
                try:
                    from i2c.agents.core_team.enhancer import quick_enhance_agent
                    enhanced_agent = quick_enhance_agent(
                        enhanced_agent, 
                        session_state["retrieved_context"], 
                        agent_type
                    )
                    canvas.info(f"🧠 DEBUG: Agent further enhanced with retrieved context")
                except ImportError:
                    canvas.warning("Enhancer module not available - skipping additional enhancement")
                except Exception as e:
                    canvas.warning(f"Additional enhancement failed: {e}")

            # Inject API context based on architectural understanding
            api_context = None
            if session_state and agent_type == "code_builder":
                arch_context = session_state.get("architectural_context", {})
                system_type = arch_context.get("system_type")
                
                # Only inject API context for systems that have APIs and UIs
                if (system_type in ["fullstack_web_app", "microservices"] and 
                    "backend_api_routes" in session_state):
                    
                    api_context = session_state.get("api_route_summary", "")
                    canvas.info(f"🔍 DEBUG: Injecting API context for {system_type}")              
            
                    
                    if hasattr(enhanced_agent, 'instructions'):
                        api_instruction = f"""

        CRITICAL API INTEGRATION RULES:
        {api_context}
        - Frontend: Use ONLY these endpoints with fetch()
        - Backend: Maintain endpoint consistency
        """
                        enhanced_agent.instructions = enhanced_agent.instructions + api_instruction
                        canvas.success(f"✅ DEBUG: API instructions added to {agent_type}")
                    else:
                        canvas.warning(f"⚠️ DEBUG: {agent_type} has no instructions attribute")

            return enhanced_agent
            
        except Exception as e:
            canvas.warning(f"Failed to create enhanced {agent_type}: {e}")
            canvas.info(f"🔄 DEBUG: Falling back to basic agent for {agent_type}")
            return agent_class()  # Fallback to basic agent
            
    except Exception as e:
        canvas.error(f"Error creating agent {agent_type}: {e}")
        return None
    
def _extract_domain_expertise(knowledge_base, agent_role):
    """Let the agent search for its own expertise using agentic search"""
    
    # Check cache first
    cache_key = f"{agent_role}_{id(knowledge_base)}"
    if cache_key in _expertise_cache:
        return _expertise_cache[cache_key]
    
    if not knowledge_base:
        canvas.error(f"🔍 DEBUG: No knowledge_base provided for {agent_role}")
        return []
    
    try:
        # DEBUG: Check knowledge space
        canvas.info(f"🔍 DEBUG: Knowledge base type: {type(knowledge_base)}")
        if hasattr(knowledge_base, 'knowledge_space'):
            canvas.info(f"🔍 DEBUG: Searching in knowledge space: {knowledge_base.knowledge_space}")
        
        # Use the agent's natural search capability
        query = f"How to build and implement {agent_role} agents with best practices and examples"
        canvas.info(f"🔍 DEBUG: Searching with query: '{query}'")
        
        results = knowledge_base.retrieve_knowledge(query=query, limit=8)
        canvas.info(f"🔍 DEBUG: retrieve_knowledge returned: {type(results)}, length: {len(results) if results else 0}")
        
        if results:
            canvas.info(f"🔍 DEBUG: First result: {results[0] if results else 'None'}")
            _expertise_cache[cache_key] = results
            canvas.success(f"🔍 DEBUG: Agent found {len(results)} knowledge items for {agent_role}")
            return results
        
        canvas.warning(f"🔍 DEBUG: No results returned for {agent_role}")
        return []
        
    except Exception as e:
        canvas.error(f"Knowledge search failed for {agent_role}: {e}")
        import traceback
        canvas.error(f"Full traceback: {traceback.format_exc()}")
        return []
    
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
    canvas.info(f"🔍 DEBUG: create_knowledge_enhanced_agent called with agent_role='{agent_role}', knowledge_base={knowledge_base is not None}")
    if knowledge_base is None:
        canvas.warning(f"🔍 DEBUG: No knowledge_base provided for {agent_role} - returning basic agent")
        # Return regular agent if no knowledge
        return base_agent_class()
    
    try:
        canvas.info(f"🔍 DEBUG: Creating knowledge-enhanced {agent_role}")
        
        # Get domain expertise for this agent type
        domain_knowledge = _extract_domain_expertise(knowledge_base, agent_role)
        canvas.info(f"🔍 DEBUG: Got {len(domain_knowledge)} domain knowledge items")
        
        # Create the base agent
        agent = base_agent_class()
        canvas.info(f"🔍 DEBUG: Created base agent: {type(agent).__name__}")
        
        # Transform instructions to include internalized expertise
        if domain_knowledge:
            agent = _inject_expertise_into_agent(agent, domain_knowledge, agent_role)
            canvas.success(f"✅ Enhanced {agent_role} with internalized expertise")
        else:
            canvas.warning(f"⚠️ DEBUG: No domain knowledge found for {agent_role}")
        
        return agent
        
    except Exception as e:
        canvas.warning(f"Failed to enhance {agent_role}: {e}")
        import traceback
        canvas.error(f"🔍 DEBUG: Enhancement error traceback: {traceback.format_exc()}")
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