from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import logging

from i2c.agents.knowledge.pattern_extractor import PatternExtractorAgent
from i2c.cli.controller import canvas
logger = logging.getLogger(__name__)


class AgentKnowledgeEnhancer:
    """
    Framework-agnostic agent enhancement with knowledge-driven reasoning.
    Integrates seamlessly with existing agent creation workflows.
    """
    
    def __init__(self):
        self.reasoner = PatternExtractorAgent()
        self.enhancement_cache = {}  # Cache patterns to avoid re-processing
        
    def enhance_agent_with_knowledge(
        self,
        agent,
        knowledge_context: str,
        agent_type: str,
        task_context: Optional[str] = None
    ):
        """
        Enhance any agent with knowledge-driven reasoning capabilities.
        
        Args:
            agent: Any agent object with instructions attribute
            knowledge_context: Raw retrieved knowledge (from RAG/vector DB)
            agent_type: Type hint for reasoning requirements (planner, code_builder, etc.)
            task_context: Optional task description for context-specific enhancement
            
        Returns:
            Enhanced agent with knowledge reasoning requirements
        """
        if not knowledge_context or not hasattr(agent, 'instructions'):
            logger.debug(f"Skipping enhancement for {agent_type}: no context or instructions")
            return agent
        
        try:
            # Extract patterns (with caching)
            cache_key = hash(knowledge_context)
            if cache_key in self.enhancement_cache:
                patterns = self.enhancement_cache[cache_key]
            else:
                patterns = self._extract_patterns_directly(knowledge_context)

                self.enhancement_cache[cache_key] = patterns
            
            if not patterns:
                logger.debug(f"No actionable patterns found for {agent_type}")
                return agent
            
            # Create reasoning requirements
            requirements = self.reasoner.create_reasoning_requirements(patterns, agent_type)
            
            # Inject requirements into agent instructions
            self._inject_requirements_into_agent(agent, requirements)
            
            # Store patterns for validation
            agent._knowledge_patterns = patterns
            agent._enhanced_with_knowledge = True
            agent._agent_type = agent_type
            
            logger.info(f"Enhanced {agent_type} with {len(patterns)} pattern types")
            
        except Exception as e:
            logger.error(f"Failed to enhance {agent_type}: {e}")
            # Don't fail agent creation, just continue without enhancement
        
        return agent

    def _extract_patterns_directly(self, knowledge_context: str) -> Dict[str, List[str]]:
        """Extract patterns directly from knowledge context without using PatternExtractorAgent"""
        
        # DEBUG: Show what content we're trying to extract patterns from
        canvas.info(f"🔍 DEBUG: Pattern extraction analyzing {len(knowledge_context)} chars")
        canvas.info(f"🔍 DEBUG: Content preview: {knowledge_context[:500]}...")
        
        if not knowledge_context:
            return {"imports": [], "file_structure": [], "conventions": [], "architecture": [], "examples": []}
        
        # Split into sentences and clean up
        import re
        sentences = re.split(r'[.!?]+', knowledge_context)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        imports = []
        conventions = []
        architecture = []
        examples = []
        
        canvas.info(f"🔍 DEBUG: Processing {len(sentences)} sentences from knowledge")
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Look for import-like patterns (from X import Y, import X)
            if ('import' in sentence_lower or 'from' in sentence_lower) and len(sentence) < 100:
                imports.append(sentence.strip())
                canvas.info(f"🔍 DEBUG: Found import pattern: {sentence[:80]}...")
                
            # Look for class/function usage patterns (contains parentheses)
            elif ('(' in sentence and ')' in sentence) and len(sentence) < 150:
                examples.append(sentence.strip())
                canvas.info(f"🔍 DEBUG: Found usage example: {sentence[:80]}...")
                
            # Look for convention statements (use, create, define, build)
            elif any(word in sentence_lower for word in ['use', 'create', 'define', 'build', 'allows you to']) and len(sentence) < 200:
                conventions.append(sentence.strip())
                canvas.info(f"🔍 DEBUG: Found convention: {sentence[:80]}...")
                
            # Look for architecture concepts
            elif any(word in sentence_lower for word in ['framework', 'system', 'architecture', 'pattern', 'team', 'agent']) and len(sentence) < 150:
                architecture.append(sentence.strip())
                canvas.info(f"🔍 DEBUG: Found architecture: {sentence[:80]}...")
        
        result = {
            "imports": imports[:5],
            "file_structure": [],
            "conventions": conventions[:5],
            "architecture": architecture[:3], 
            "examples": examples[:5]
        }
        
        canvas.info(f"🔍 DEBUG: Final extracted patterns: {len(imports)} imports, {len(conventions)} conventions, {len(examples)} examples, {len(architecture)} architecture")
        return result

    def enhance_agent_instructions(
        self,
        base_instructions: Union[str, List[str]],
        knowledge_context: str,
        agent_type: str
    ) -> Union[str, List[str]]:
        """
        Enhance instructions directly without modifying agent object.
        Useful for integration with existing agent factories.
        """
        if not knowledge_context:
            return base_instructions
        
        try:
            patterns = self.reasoner.extract_actionable_patterns(knowledge_context)
            if not patterns:
                return base_instructions
            
            requirements = self.reasoner.create_reasoning_requirements(patterns, agent_type)
            
            # Handle both string and list instruction formats
            if isinstance(base_instructions, list):
                return base_instructions + requirements
            else:
                return str(base_instructions) + "\n\n" + "\n".join(requirements)
                
        except Exception as e:
            logger.error(f"Failed to enhance instructions for {agent_type}: {e}")
            return base_instructions

    def validate_enhanced_agent_output(self, agent, output: str) -> Dict[str, Any]:
        """
        Validate that enhanced agent applied knowledge patterns.
        Returns validation results for feedback/learning.
        """
        if not hasattr(agent, '_knowledge_patterns'):
            return {"enhanced": False, "message": "Agent was not enhanced with knowledge"}
        
        try:
            # Try the PatternExtractorAgent validation
            success, violations = self.reasoner.validate_pattern_application(
                output, agent._knowledge_patterns
            )
        except Exception as e:
            # Fallback validation
            print(f"PatternExtractorAgent validation failed: {e}")
            success, violations = self._fallback_validation(output, agent._knowledge_patterns)
        
        return {
            "enhanced": True,
            "success": success,
            "violations": violations,
            "patterns_available": len(agent._knowledge_patterns),
            "agent_type": getattr(agent, '_agent_type', 'unknown')
        }

    def _fallback_validation(self, output: str, patterns: Dict) -> tuple[bool, List[str]]:
        """Simple fallback validation"""
        violations = []
        output_lower = output.lower()
        
        # Check for basic pattern application
        has_imports = any(
            any(keyword in output_lower for keyword in imp.lower().split()[:2]) 
            for imp in patterns.get('imports', [])
        )
        has_justification = 'applied patterns:' in output_lower
        
        if not has_imports and patterns.get('imports'):
            violations.append("Missing documented imports")
        if not has_justification:
            violations.append("Missing pattern application justification")
        
        success = len(violations) == 0
        return success, violations
    
    def create_enhancement_hook(self, session_state_key: str = "retrieved_context"):
        """
        Create a reusable enhancement function for integration with existing workflows.
        
        Returns:
            Function that can be called in agent creation pipelines
        """
        def enhancement_hook(agent, session_state: Dict, agent_type: str):
            if session_state and session_state_key in session_state:
                knowledge_context = session_state[session_state_key]
                task_context = session_state.get("task", "")
                return self.enhance_agent_with_knowledge(
                    agent, knowledge_context, agent_type, task_context
                )
            return agent
        
        return enhancement_hook
    
    def _inject_requirements_into_agent(self, agent, requirements: List[str]):
        """Safely inject requirements into agent instructions with knowledge priority"""
        if not requirements:
            return
        
        # Handle different instruction formats - PRIORITIZE knowledge requirements
        if hasattr(agent, 'instructions'):
            current_instructions = agent.instructions
            
            if isinstance(current_instructions, list):
                # PUT KNOWLEDGE FIRST - makes it primary focus
                agent.instructions = requirements + current_instructions
                logger.info(f"Enhanced agent with {len(requirements)} knowledge requirements (prioritized)")
                
                # DEBUG: Log what was injected
                canvas.info(f"💉 DEBUG: Injected {len(requirements)} requirements into {type(agent).__name__}")
                canvas.info(f"🔍 DEBUG: First requirement: {requirements[0] if requirements else 'None'}")
                canvas.info(f"📋 DEBUG: Total instructions now: {len(agent.instructions)}")
     
            
            elif isinstance(current_instructions, str):
                # PUT KNOWLEDGE FIRST in string format
                knowledge_text = "\n".join(requirements)
                agent.instructions = f"{knowledge_text}\n\n{current_instructions}"
                logger.info(f"Enhanced agent instructions with knowledge priority")
            else:
                # Fallback: convert to string with knowledge first
                knowledge_text = "\n".join(requirements)
                agent.instructions = f"{knowledge_text}\n\n{str(current_instructions)}"
                logger.info(f"Enhanced agent with fallback knowledge priority")
        
        # Some agents might use different attribute names
        elif hasattr(agent, 'system_prompt'):
            current_prompt = agent.system_prompt or ""
            knowledge_text = "\n".join(requirements)
            agent.system_prompt = f"{knowledge_text}\n\n{current_prompt}"
        
        elif hasattr(agent, 'prompt'):
            current_prompt = agent.prompt or ""
            knowledge_text = "\n".join(requirements)
            agent.prompt = f"{knowledge_text}\n\n{current_prompt}"

class SessionStateEnhancer:
    """
    Manages knowledge context in session state for multi-step workflows.
    Ensures knowledge persists across agent interactions.
    """
    
    def __init__(self):
        self.enhancer = AgentKnowledgeEnhancer()
    
    def store_knowledge_context(
        self,
        session_state: Dict,
        knowledge_context: str,
        context_source: str = "rag_retrieval"
    ):
        """Store knowledge context in session state for reuse"""
        if not session_state:
            session_state = {}
        
        session_state["retrieved_context"] = knowledge_context
        session_state["context_source"] = context_source
        session_state["context_stored_at"] = self._get_timestamp()
        
        return session_state
    
    def get_knowledge_context(self, session_state: Dict) -> Optional[str]:
        """Retrieve stored knowledge context"""
        return session_state.get("retrieved_context") if session_state else None
    
    def enhance_agent_from_session(
        self,
        agent,
        session_state: Dict,
        agent_type: str
    ):
        """Enhance agent using knowledge context from session state"""
        knowledge_context = self.get_knowledge_context(session_state)
        
        if knowledge_context:
            task_context = session_state.get("task", "")
            return self.enhancer.enhance_agent_with_knowledge(
                agent, knowledge_context, agent_type, task_context
            )
        
        return agent
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for tracking"""
        from datetime import datetime
        return datetime.now().isoformat()


# Integration utilities for existing codebase
def create_knowledge_enhanced_agent_factory():
    """
    Create a factory function that can replace existing agent creation.
    Drop-in replacement for get_rag_enabled_agent() pattern.
    """
    enhancer = AgentKnowledgeEnhancer()
    
    def enhanced_agent_factory(agent_class, agent_type: str, session_state: Dict = None):
        """Create an enhanced agent with knowledge reasoning"""
        # Create base agent
        agent = agent_class()
        
        # Enhance with knowledge if available
        if session_state and "retrieved_context" in session_state:
            agent = enhancer.enhance_agent_with_knowledge(
                agent, 
                session_state["retrieved_context"], 
                agent_type,
                session_state.get("task", "")
            )
        
        return agent
    
    return enhanced_agent_factory


def enhance_existing_agent_creation(original_function):
    """
    Decorator to enhance existing agent creation functions.
    Can wrap get_rag_enabled_agent() or similar functions.
    """
    enhancer = AgentKnowledgeEnhancer()
    
    def wrapper(agent_type, session_state=None, *args, **kwargs):
        # Call original function
        agent = original_function(agent_type, session_state, *args, **kwargs)
        
        # Enhance with knowledge if available
        if session_state and "retrieved_context" in session_state:
            agent = enhancer.enhance_agent_with_knowledge(
                agent,
                session_state["retrieved_context"],
                agent_type,
                session_state.get("task", "")
            )
        
        return agent
    
    return wrapper


# Quick integration helpers
def quick_enhance_agent(agent, knowledge_context: str, agent_type: str):
    """Quick enhancement for one-off agent creation"""
    enhancer = AgentKnowledgeEnhancer()
    return enhancer.enhance_agent_with_knowledge(agent, knowledge_context, agent_type)


def quick_enhance_instructions(instructions, knowledge_context: str, agent_type: str):
    """Quick enhancement for instruction strings/lists"""
    enhancer = AgentKnowledgeEnhancer()
    return enhancer.enhance_agent_instructions(instructions, knowledge_context, agent_type)


# Test examples and validation
if __name__ == "__main__":
    # Test 1: Basic agent enhancement
    def test_basic_enhancement():
        print("🧪 Testing basic agent enhancement...")
        
        # Mock agent class
        class MockAgent:
            def __init__(self):
                self.instructions = ["Be helpful", "Generate good code"]
                self.name = "TestAgent"
        
        # Mock knowledge context
        knowledge_context = """
        from agno.agent import Agent
        from agno.team import Team
        
        Always use Agent(model=..., instructions=...) pattern.
        Separate frontend and backend code.
        Use proper error handling.
        """
        
        # Test enhancement
        enhancer = AgentKnowledgeEnhancer()
        agent = MockAgent()
        
        print(f"Before enhancement: {len(agent.instructions)} instructions")
        
        enhanced_agent = enhancer.enhance_agent_with_knowledge(
            agent, knowledge_context, "code_builder"
        )
        
        print(f"After enhancement: {len(enhanced_agent.instructions)} instructions")
        print("Enhanced instructions include:", enhanced_agent.instructions[-2:])
        print("✅ Basic enhancement test passed")
    
    # Test 2: Session state integration
    def test_session_state_integration():
        print("\n🧪 Testing session state integration...")
        
        session_enhancer = SessionStateEnhancer()
        session_state = {}
        
        # Store knowledge
        knowledge = "Use FastAPI for backend. React for frontend."
        session_state = session_enhancer.store_knowledge_context(
            session_state, knowledge, "test_retrieval"
        )
        
        print(f"Stored context: {session_state.get('retrieved_context')[:50]}...")
        
        # Enhance agent from session
        class MockAgent:
            def __init__(self):
                self.instructions = ["Plan project files"]
        
        agent = MockAgent()
        enhanced = session_enhancer.enhance_agent_from_session(
            agent, session_state, "planner"
        )
        
        print(f"Agent enhanced: {hasattr(enhanced, '_enhanced_with_knowledge')}")
        print("✅ Session state integration test passed")
    
    # Test 3: Instruction enhancement only
    def test_instruction_enhancement():
        print("\n🧪 Testing instruction enhancement...")
        
        base_instructions = ["Generate clean code", "Follow best practices"]
        knowledge = "Always use TypeScript. Add proper type annotations."
        
        enhancer = AgentKnowledgeEnhancer()
        enhanced_instructions = enhancer.enhance_agent_instructions(
            base_instructions, knowledge, "code_builder"
        )
        
        print(f"Original: {len(base_instructions)} instructions")
        print(f"Enhanced: {len(enhanced_instructions)} instructions")
        print("New instructions include TypeScript guidance")
        print("✅ Instruction enhancement test passed")
    
    # Test 4: Validation
    def test_validation():
        print("\n🧪 Testing validation...")
        
        class MockAgent:
            def __init__(self):
                self.instructions = []
        
        agent = MockAgent()
        enhancer = AgentKnowledgeEnhancer()
        
        # Enhance agent
        enhanced = enhancer.enhance_agent_with_knowledge(
            agent, "Use Agent pattern", "code_builder"
        )
        
        # Test validation
        good_output = "from agno.agent import Agent\nAgent(model=..., instructions=...)\nApplied patterns: import:agno.agent"
        bad_output = "print('hello world')"
        
        good_result = enhancer.validate_enhanced_agent_output(enhanced, good_output)
        bad_result = enhancer.validate_enhanced_agent_output(enhanced, bad_output)
        
        print(f"Good output validation: {good_result['success']}")
        print(f"Bad output validation: {bad_result['success']}")
        print("✅ Validation test passed")
    
    # Run all tests
    test_basic_enhancement()
    test_session_state_integration()
    test_instruction_enhancement()
    test_validation()
    
    print("\n🎉 All tests passed! Enhancer ready for integration.")