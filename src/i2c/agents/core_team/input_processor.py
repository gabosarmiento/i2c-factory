
from textwrap import dedent
from agno.agent import Agent
from builtins import llm_middle, llm_highest, llm_small # Use llm_middle or llm_small for analysis

from i2c.agents.context_builder import RagContextBuilder

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

# --- Input Processor Agent ---
class InputProcessorAgent(Agent):
    """Clarifies raw user software ideas into structured objectives and languages."""
    
    def __init__(self, knowledge_base=None, **kwargs):
        """
        Initialize the Input Processor Agent with RAG capabilities.
        
        Args:
            knowledge_base: Optional knowledge base for context retrieval
            **kwargs: Additional arguments for Agent initialization
        """
        # RAG Integration: Initialize context builder with the knowledge base
        self.context_builder = RagContextBuilder(
            knowledge_base=knowledge_base,
            default_chunk_count=5,
            max_tokens=4000  # Conservative token limit
        )
        
        super().__init__(
            name="InputProcessor",
            model=llm_middle,
            description="Clarifies raw user software ideas into structured objectives and languages.",
            instructions=dedent("""
                **Requirement Intelligence Protocol:**

                You are a world-class Software Project Clarification Agent responsible for transforming raw ideas into structured specifications.

                1. **Domain Knowledge Extraction:**
                   - Identify the business domain and user needs behind technical requests
                   - Map user scenarios to concrete functional requirements
                   - Analyze implied constraints (legal, scalability, performance)
                   - Detect unstated assumptions about user expectations
                   - Apply industry-specific context to generic requests

                2. **Technological Landscape Analysis:**
                   - Evaluate appropriate technology stack for the requirements
                   - Assess maturity vs innovation tradeoffs for stack choices
                   - Map requirements to architectural patterns with historical success
                   - Consider maintainability and long-term viability
                   - Identify when existing tools/libraries solve needs without custom code

                3. **Complexity Gradient Evaluation:**
                   - Apply "Essential Complexity Only" principle to prevent overengineering
                   - Identify accidental vs essential complexity in requirements
                   - Scale technological solutions proportionally to problem complexity
                   - Map feature dependencies to identify core vs peripheral needs
                   - Apply first principles thinking to simplify complex requests

                4. **Output Format:**
                   Respond strictly with a JSON object containing 'objective' and 'language'.
                   Example: {"objective": "Create a CLI todo list manager.", "language": "Python"}
                   Do NOT include any extra text, greetings, explanations, or markdown formatting.
            """),
            **kwargs
        )
        
    def run(self, prompt, **kwargs):
        """
        Override run method to enhance with RAG context
        
        Args:
            prompt: The user prompt to process
            **kwargs: Additional arguments for the run method
            
        Returns:
            The agent's response with RAG-enhanced context
        """
        # RAG Integration: Enhance prompt with knowledge context if available
        enhanced_prompt = self._enhance_prompt_with_context(prompt)
        
        # Call the original run method with the enhanced prompt
        return super().run(enhanced_prompt, **kwargs)
        
    def _enhance_prompt_with_context(self, prompt: str) -> str:
        """
        Enhance the prompt with relevant context from knowledge base
        
        Args:
            prompt: The original prompt
            
        Returns:
            Enhanced prompt with knowledge context
        """
        if not hasattr(self, 'context_builder') or not self.context_builder.knowledge_base:
            return prompt
            
        try:
            # Build sub-queries for composite context
            sub_queries = [
                "software project architecture patterns and best practices",
                f"technology stack selection criteria for {prompt[:50]}",
                f"software complexity management for {prompt[:50]}"
            ]
            
            # Retrieve composite context
            context = self.context_builder.retrieve_composite_context(
                main_query=prompt,
                sub_queries=sub_queries,
                main_chunk_count=3,
                sub_chunk_count=2
            )
            
            if not context:
                return prompt
                
            # Add context to the prompt
            enhanced_prompt = f"""
            # Knowledge Context
            The following information may be relevant to the request:
            
            {context}
            
            # Original Request
            {prompt}
            """
            
            canvas.info("[RAG] Enhanced Input Processor prompt with knowledge context")
            return enhanced_prompt
            
        except Exception as e:
            canvas.warning(f"[RAG] Error enhancing prompt: {e}")
            return prompt

def create_input_processor_agent(knowledge_base=None):
    """Create an InputProcessorAgent with RAG capabilities."""
    return InputProcessorAgent(knowledge_base=knowledge_base)