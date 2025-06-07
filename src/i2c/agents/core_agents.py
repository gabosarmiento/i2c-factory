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

def filter_session_state_for_agent(session_state: dict, agent_type: str) -> dict:
    """
    PHASE 2: Surgical context filtering - reduce bloat while preserving functionality
    
    Based on diagnostic data:
    - knowledge_context is 9.6KB (70% of session state)
    - Need to filter this per agent type
    - Preserve all critical keys for functionality
    """
    if not session_state:
        return session_state
    
    # Create filtered copy
    filtered_state = session_state.copy()
    
    # Only filter for code_builder initially (safest to test)
    if agent_type == "code_builder":
        canvas.info(f"🔧 PHASE 2: Applying context filtering for {agent_type}")

        # Define what each agent type actually needs
        AGENT_CONTEXT_REQUIREMENTS = {
            "code_builder": {
                "required": [
                    "project_path",
                    "architectural_context", 
                    "backend_api_routes",
                    "api_route_summary",
                    "knowledge_base"
                ],
                "optional": [
                    "retrieved_context",
                    "project_structure",
                    "language_context"
                ],
                "skip": [
                    "knowledge_context",  # This is the 9.6KB bloat
                    "validation_results", 
                    "generation_history",
                    "previous_attempts"
                ]
            },
            "input_processor": {
                "required": ["project_path", "knowledge_base"],
                "optional": ["architectural_context"],
                "skip": ["knowledge_context", "retrieved_context", "backend_api_routes"]
            },
            "planner": {
                "required": ["project_path", "architectural_context", "knowledge_base"],
                "optional": ["project_structure"],
                "skip": ["knowledge_context", "retrieved_context", "backend_api_routes"]
            },
            "project_context_analyzer": {
                "required": ["project_path", "knowledge_base"],
                "optional": ["project_structure"],
                "skip": ["knowledge_context", "retrieved_context", "backend_api_routes", "architectural_context"]
            }
        }
        
        # Get requirements for this agent type
        requirements = AGENT_CONTEXT_REQUIREMENTS.get(agent_type, {
            "required": ["project_path", "knowledge_base"],
            "optional": [],
            "skip": ["knowledge_context"]
        })
        
        # Build filtered context with only what's needed
        filtered_state = {}
        
        # Always include required keys
        for key in requirements["required"]:
            if key in session_state:
                filtered_state[key] = session_state[key]
        
        # Include optional keys if they exist and aren't too large
        for key in requirements["optional"]:
            if key in session_state:
                value = session_state[key]
                # Only skip optional keys if they're extremely large (>20KB)
                if len(str(value)) < 20000:
                    filtered_state[key] = value
                else:
                    canvas.info(f"🔧 Skipping large optional key {key} ({len(str(value)):,} chars)")
        
        # Log what we're doing
        original_keys = set(session_state.keys())
        filtered_keys = set(filtered_state.keys())
        skipped_keys = original_keys - filtered_keys
        
        original_size = len(str(session_state))
        filtered_size = len(str(filtered_state))
        
        canvas.info(f"🔧 PHASE 2 CORRECTED: Context selectivity for {agent_type}")
        canvas.info(f"   Original keys: {len(original_keys)} ({original_size:,} chars)")
        canvas.info(f"   Filtered keys: {len(filtered_keys)} ({filtered_size:,} chars)")
        
        if skipped_keys:
            canvas.info(f"   Skipped keys: {', '.join(sorted(skipped_keys))}")
        
        if filtered_size < original_size:
            reduction_pct = ((original_size-filtered_size)/original_size*100)
            canvas.success(f"🔧 Context reduced: {original_size:,} → {filtered_size:,} chars ({reduction_pct:.1f}% reduction)")
        else:
            canvas.info(f"🔧 Context preserved: {filtered_size:,} chars")
    else:
        # For other agents, pass through unchanged (for now)
        canvas.info(f"🔧 PHASE 2: No filtering for {agent_type} (preserving original behavior)")
    
    return filtered_state

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
    """AGNO-native agent factory with dynamic knowledge access"""
    
    # =================================================================
    # DIAGNOSTIC LOGGING - PHASE 1: Measure session_state size
    # =================================================================
    canvas.info(f"📊 PROMPT ANALYSIS: Creating {agent_type} agent")
    
    if session_state:
        # Count keys and measure content size
        total_keys = len(session_state)
        total_chars = 0
        large_keys = []
        
        for key, value in session_state.items():
            try:
                if isinstance(value, str):
                    size = len(value)
                elif isinstance(value, (list, dict)):
                    size = len(str(value))
                else:
                    size = len(str(value))
                
                total_chars += size
                
                # Track keys with substantial content
                if size > 1000:
                    large_keys.append(f"{key}({size:,}chars)")
                    
            except Exception as e:
                canvas.warning(f"📊 Error measuring key {key}: {e}")
        
        # Log session state metrics
        canvas.info(f"📊 SESSION STATE METRICS:")
        canvas.info(f"   Total keys: {total_keys}")
        canvas.info(f"   Total content: {total_chars:,} characters")
        
        if large_keys:
            canvas.info(f"   Large keys: {', '.join(large_keys)}")
        
        # Categorize by size
        if total_chars > 40000:
            canvas.warning(f"📊 ⚠️  VERY LARGE SESSION STATE - May cause prompt issues")
        elif total_chars > 20000:
            canvas.warning(f"📊 ⚠️  LARGE SESSION STATE - Monitor for issues")
        elif total_chars > 10000:
            canvas.info(f"📊 MEDIUM SESSION STATE - Reasonable size")
        else:
            canvas.info(f"📊 ✅ SMALL SESSION STATE - Optimal size")
            
        # PHASE 2 DIAGNOSIS: Log all session state keys for system analysis
        canvas.info(f"📊 FULL SESSION STATE KEYS for {agent_type}:")
        for key, value in session_state.items():
            value_type = type(value).__name__
            value_size = len(str(value))
            # Show preview for small values, size for large ones
            if value_size < 100:
                if isinstance(value, str):
                    preview = f'"{value}"'
                else:
                    preview = str(value)
                canvas.info(f"   {key}: {value_type} = {preview}")
            else:
                canvas.info(f"   {key}: {value_type} ({value_size:,} chars)")
        # DEBUG: Track API route context (existing logic)
        if "backend_api_routes" in session_state:
            routes = session_state["backend_api_routes"]
            canvas.info(f"🔍 DEBUG: Found API routes: {routes}")
        else:
            canvas.info(f"🔍 DEBUG: No API routes in session state")
    else:
        canvas.info(f"📊 No session_state provided for {agent_type}")
    
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
        
        # =================================================================
        # PHASE 2: Apply surgical context filtering before agent creation
        # =================================================================
        filtered_session_state = filter_session_state_for_agent(session_state, agent_type)
        
        try:
            # Get knowledge base from filtered session
            knowledge_base = filtered_session_state.get("knowledge_base")
            canvas.info(f"🔍 DEBUG: Knowledge base exists in session: {knowledge_base is not None}")
            
            # If no knowledge base, create basic agent
            if knowledge_base is None:
                canvas.warning(f"🔍 DEBUG: No knowledge_base in session_state for {agent_type}")
                return agent_class()
            
            # AGNO-NATIVE: Create agent with dynamic knowledge access
            try:
                # Try AGNO-native agent creation with session_state and add_context
                enhanced_agent = agent_class(
                    add_context=True,  # Enable AGNO's native knowledge access
                    session_state=filtered_session_state  # Pass session_state with knowledge_base
                )
                canvas.success(f"✅ Created AGNO-native {agent_type} with dynamic knowledge access")
            except TypeError:
                # Fallback to legacy enhancement if agent doesn't support AGNO-native
                enhanced_agent = create_knowledge_enhanced_agent(
                    agent_class, 
                    knowledge_base, 
                    agent_type
                )
                canvas.warning(f"⚠️ Using legacy enhancement for {agent_type} (consider updating to AGNO-native)")
            
            canvas.info(f"🔍 DEBUG: Enhanced agent created: {type(enhanced_agent).__name__}")
            # Log important session state keys only to reduce noise
            important_keys = ['knowledge_base', 'architectural_context', 'retrieved_context', 'backend_api_routes']
            
            if filtered_session_state:
                present_important = [key for key in important_keys if key in filtered_session_state]
                if present_important:
                    canvas.info(f"🔍 DEBUG: Important session keys present: {', '.join(present_important)}")
                else:
                    canvas.info(f"🔍 DEBUG: No important session keys found in {len(filtered_session_state)} total keys")
            
            # SIMPLIFIED: Use retrieved_context for all agents
            if "retrieved_context" in filtered_session_state:
                try:
                    from i2c.agents.core_team.enhancer import AgentKnowledgeEnhancer
                    enhancer = AgentKnowledgeEnhancer()
                    enhanced_agent = enhancer.enhance_agent_with_knowledge(
                        enhanced_agent, 
                        filtered_session_state["retrieved_context"], 
                        agent_type
                    )
                    canvas.success(f"✅ Enhanced {agent_type} with retrieved_context")
                except Exception as e:
                    canvas.warning(f"⚠️ Enhancement failed for {agent_type}: {e}")
            else:
                canvas.warning(f"⚠️ No retrieved_context available for {agent_type}")

            # Inject API context based on architectural understanding
            api_context = None
            if filtered_session_state and agent_type == "code_builder":
                arch_context = filtered_session_state.get("architectural_context", {})
                system_type = arch_context.get("system_type")
                
                # Only inject API context for systems that have APIs and UIs
                if (system_type in ["fullstack_web_app", "microservices"] and 
                    "backend_api_routes" in filtered_session_state):
                    
                    api_context = filtered_session_state.get("api_route_summary", "")
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

            # =================================================================
            # DIAGNOSTIC LOGGING - PHASE 1: Measure final agent prompt size
            # =================================================================
            try:
                if hasattr(enhanced_agent, 'instructions'):
                    instructions = enhanced_agent.instructions
                    
                    if isinstance(instructions, list):
                        instruction_count = len(instructions)
                        total_instruction_chars = sum(len(str(inst)) for inst in instructions)
                    elif isinstance(instructions, str):
                        instruction_count = 1
                        total_instruction_chars = len(instructions)
                    else:
                        instruction_count = 1
                        total_instruction_chars = len(str(instructions))
                    
                    canvas.info(f"📊 FINAL AGENT METRICS for {agent_type}:")
                    canvas.info(f"   Instruction count: {instruction_count}")
                    canvas.info(f"   Total instruction chars: {total_instruction_chars:,}")
                    
                    # Categorize instruction size
                    if total_instruction_chars > 10000:
                        canvas.warning(f"📊 ⚠️  VERY LARGE INSTRUCTIONS - May overwhelm agent")
                    elif total_instruction_chars > 5000:
                        canvas.warning(f"📊 ⚠️  LARGE INSTRUCTIONS - Monitor performance")
                    elif total_instruction_chars > 2000:
                        canvas.info(f"📊 MEDIUM INSTRUCTIONS - Reasonable size")
                    else:
                        canvas.info(f"📊 ✅ COMPACT INSTRUCTIONS - Optimal size")
                        
                    # Check for specific bloat indicators
                    if instruction_count > 20:
                        canvas.warning(f"📊 ⚠️  HIGH INSTRUCTION COUNT - May cause confusion")
                        
                else:
                    canvas.info(f"📊 Agent {agent_type} has no instructions attribute to measure")
                    
            except Exception as e:
                canvas.warning(f"📊 Error measuring final agent instructions: {e}")

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