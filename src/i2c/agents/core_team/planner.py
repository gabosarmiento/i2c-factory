# src/i2c/agents/core_team/planner.py
import json
from typing import Dict
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

# --- Planner Agent ---
class PlannerAgent(Agent):
    """Plans the minimal viable file structure for the project based on clarified objectives."""
    
    def __init__(self, knowledge_base=None, **kwargs):
        """
        Initialize the Planner Agent with RAG capabilities.
        
        Args:
            knowledge_base: Optional knowledge base for context retrieval
            **kwargs: Additional arguments for Agent initialization
        """
        # RAG Integration: Initialize context builder with higher chunk count for planning
        self.context_builder = RagContextBuilder(
            knowledge_base=knowledge_base,
            default_chunk_count=8,  # Planning benefits from more comprehensive context
            max_tokens=6000  # Higher token limit for planning
        )
        
        super().__init__(
            name="Planner",
            model=llm_middle,
            description="Plans the minimal viable file structure for the project based on clarified objectives.",
            instructions=dedent("""
                **Architectural Genesis Protocol:**

                You are a Software Project Planning Agent responsible for designing minimal viable architectures.

                1. **Pattern-Language Synthesis:**
                   - Apply appropriate architectural patterns based on project requirements
                   - Design appropriate system boundaries based on domain needs
                   - Focus on pragmatic patterns that solve current objectives, not aspirational ones
                   - Scale architectural complexity to match problem dimensions
                   - Ensure separation of concerns with appropriate granularity
                   - Design for future flexibility without overengineering
                   - Maintain domain-driven boundaries proportional to project scale and context

                2. **Dimensional Architecture Mapping:**
                   - Choose appropriate file structure based on language conventions
                   - Apply standard project layouts for the identified language
                   - Include only essential files needed for core functionality
                   - Map cross-cutting concerns to appropriate components
                   - Apply the minimal viable structure principle
                   - Distinguish between initial deliverable structure and future extension placeholders
                   - Include test folders only when requirements specify testability or CI readiness

                3. **Implementation Minimalism:**
                   - Include only files absolutely necessary for requirements
                   - Avoid premature optimization in your file structure
                   - Follow language-specific best practices for organization
                   - Ensure consistency in naming conventions
                   - Avoid unnecessary abstraction layers
                   - Include composition-ready structure for core domains without adding abstraction prematurely
                   - Apply the "one-concern-per-file" principle to avoid bloated main modules
                   - Prioritize vertical slice simplicity (feature-first structuring if applicable)
                   
                4. **Quality Enforcement:**
                   - Ensure tests do not have duplicate unittest.main() calls
                   - Use consistent data models across all files
                   - Avoid creating duplicate implementations of the same functionality
                   - If creating a CLI app, use a single approach for the interface
                   - Use consistent file naming for data storage (e.g., todos.json)

                5. **Output Format:**
                   Given a project objective and programming language, output ONLY a minimal JSON array of essential file paths.
                   Example output: ["main.py", "game.py", "player.py"].
                   Do NOT include any commentary, folder hierarchies, or markdown formatting.
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
        Enhance the prompt with relevant architectural context from knowledge base
        
        Args:
            prompt: The original prompt
            
        Returns:
            Enhanced prompt with knowledge context
        """
        if not hasattr(self, 'context_builder') or not self.context_builder.knowledge_base:
            return prompt
            
        try:
            # Parse the prompt to extract key information for targeted retrieval
            project_info = self._extract_project_info(prompt)
            
            # Build focused sub-queries for architecture planning
            objective = project_info.get("objective", "")
            language = project_info.get("language", "")
            
            sub_queries = [
                f"{language} project structure best practices",
                f"{language} architecture for {objective[:50]}",
                f"minimal viable file structure for {language} {objective[:30]}",
                f"architecture patterns for {objective[:50]}",
                f"{language} framework conventions and file organization"
            ]
            
            # Retrieve comprehensive composite context for architecture planning
            context = self.context_builder.retrieve_composite_context(
                main_query=f"{language} architecture for {objective}",
                sub_queries=sub_queries,
                main_chunk_count=5,
                sub_chunk_count=2
            )
            
            if not context:
                return prompt
                
            # Add context to the prompt with clear architectural relevance
            enhanced_prompt = f"""
            # Architectural Knowledge Context
            The following architectural information is relevant to planning this project:
            
            {context}
            
            # Project Requirements
            {prompt}
            """
            
            canvas.info(f"[RAG] Enhanced Planner prompt with comprehensive architectural context ({len(context)//4} tokens)")
            return enhanced_prompt
            
        except Exception as e:
            canvas.warning(f"[RAG] Error enhancing planner prompt: {e}")
            return prompt
            
    def _extract_project_info(self, prompt: str) -> Dict[str, str]:
        """Extract key project information from the prompt for targeted queries"""
        # Simple extraction based on common patterns
        project_info = {
            "objective": "",
            "language": ""
        }
        
        # Try to extract from JSON structure if present
        try:
            import re
            from i2c.utils.json_extraction import extract_json_with_fallback

            json_match = re.search(r'\{.*\}', prompt, re.DOTALL)
            if json_match:
                data = extract_json_with_fallback(json_match.group(0), {})
                if isinstance(data, dict):
                    project_info["objective"] = data.get("objective", "")
                    project_info["language"] = data.get("language", "")
        except Exception:
            pass
            
        # If extraction failed, use basic keyword detection
        if not project_info["objective"] or not project_info["language"]:
            lower_prompt = prompt.lower()
            
            # Try to detect language
            for lang in ["python", "javascript", "typescript", "java", "go", "rust", "c++", "c#"]:
                if lang in lower_prompt:
                    project_info["language"] = lang
                    break
                    
            # Use the first 100 chars as the objective if not found
            if not project_info["objective"]:
                project_info["objective"] = prompt[:100]
                
        return project_info

def create_planner_agent(knowledge_base=None):
    """Create a PlannerAgent with RAG capabilities."""
    return PlannerAgent(knowledge_base=knowledge_base)