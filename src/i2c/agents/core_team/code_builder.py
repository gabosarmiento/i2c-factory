# src/i2c/agents/core_team/code_builder.py
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

# --- Code Builder Agent ---
class CodeBuilderAgent(Agent):
    """Generates complete, runnable code for each specified project file."""
    
    def __init__(self, knowledge_base=None, **kwargs):
        """
        Initialize the Code Builder Agent with RAG capabilities.
        
        Args:
            knowledge_base: Optional knowledge base for context retrieval
            **kwargs: Additional arguments for Agent initialization
        """
        # RAG Integration: Initialize context builder with the knowledge base
        # Code generation benefits from detailed technical context
        self.context_builder = RagContextBuilder(
            knowledge_base=knowledge_base,
            default_chunk_count=10,  # Code generation needs more context for complex implementations
            max_tokens=8000  # Higher token limit for code generation
        )
        
        super().__init__(
            name="CodeBuilder",
            model=llm_highest,  # Use the highest capability model for code generation
            description="Generates complete, runnable code for each specified project file.",
            instructions=dedent("""
            # Code Generation Instructions

            Generate complete, executable code using the enhanced context provided through RAG integration.

            ## Use Enhanced Context
            - Apply architectural patterns from retrieved knowledge context
            - Follow the specific system_type and module boundaries provided
            - Use existing API endpoints, data models, and file organization rules from context
            - Match the established technology stack and frameworks detected in the project

            ## Code Quality
            - Generate syntactically correct code that matches language conventions
            - Include proper imports, error handling, and type safety
            - Follow existing code patterns and naming conventions from the project
            - Ensure cross-file consistency and architectural compliance

            ## Output Format
            - Output **ONLY the raw code** for the specified files.
            - No markdown blocks, explanations, or comments about generation.
            - Output code that passes strict **linters and formatters** specific to the tech stack.
            - Code must be complete and ready to write directly to files.
            - Use consistent indentation (4 spaces Python, 2 spaces JavaScript).
            - Ensure the code is **complete, runnable, syntactically correct**, and **verified against automated quality checks**.

            The RagContextBuilder has already provided relevant implementation context - use it to generate code that integrates perfectly with the existing project structure.
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
        Enhance the prompt with relevant code implementation context from knowledge base
        
        Args:
            prompt: The original prompt
            
        Returns:
            Enhanced prompt with knowledge context
        """
        if not hasattr(self, 'context_builder') or not self.context_builder.knowledge_base:
            return prompt
            
        try:
            # Extract code-specific information
            file_info = self._extract_file_info(prompt)
            
            # Handle multi-file code generation
            if len(file_info) > 1:
                # For multi-file projects, get architectural context first
                project_context = self.context_builder.retrieve_context(
                    query=f"software architecture for {' '.join(file_info.keys())}"
                )
                
                # Then get specific implementation details for each file
                file_contexts = []
                for filename, file_type in file_info.items():
                    file_context = self.context_builder.retrieve_context(
                        query=f"{file_type} implementation best practices for {filename}",
                        chunk_count=3
                    )
                    if file_context:
                        file_contexts.append(f"# For {filename}:\n{file_context}")
                
                # Combine contexts
                combined_context = project_context
                if file_contexts:
                    combined_context += "\n\n" + "\n\n".join(file_contexts)
                    
                context = combined_context
            else:
                # For single file, focus on detailed implementation
                filename = list(file_info.keys())[0] if file_info else ""
                file_type = list(file_info.values())[0] if file_info else ""
                
                # Build specialized sub-queries for this file type
                sub_queries = [
                    f"{file_type} implementation patterns",
                    f"{file_type} code examples for {filename}",
                    f"best practices for {file_type} in {filename}",
                    f"{file_type} security considerations",
                    f"{file_type} error handling patterns"
                ]
                
                # Get comprehensive implementation context
                context = self.context_builder.retrieve_composite_context(
                    main_query=f"{file_type} implementation for {filename}",
                    sub_queries=sub_queries
                )
            
            if not context:
                return prompt
                
            # Add context to the prompt
            enhanced_prompt = f"""
            # Implementation Knowledge Context
            The following knowledge will help you write high-quality code:
            
            {context}
            
            # Code Generation Request
            {prompt}
            """
            
            canvas.info(f"[RAG] Enhanced CodeBuilder prompt with implementation context ({len(context)} chars)")
            return enhanced_prompt
            
        except Exception as e:
            canvas.warning(f"[RAG] Error enhancing code builder prompt: {e}")
            return prompt
            
    def _extract_file_info(self, prompt: str) -> Dict[str, str]:
        """Extract information about files to be generated"""
        file_info = {}
        
        # Try to find filenames in the prompt
        import re
        
        # Look for filenames with extensions
        filename_matches = re.findall(r'[a-zA-Z0-9_\-]+\.[a-zA-Z0-9]+', prompt)
        
        for filename in filename_matches:
            # Determine file type based on extension
            extension = filename.split('.')[-1].lower()
            file_type = self._map_extension_to_language(extension)
            file_info[filename] = file_type
            
        # If no files found, use generic code query
        if not file_info:
            file_info["code.txt"] = "general code"
            
        return file_info
        
    def _map_extension_to_language(self, extension: str) -> str:
        """Map file extension to language or file type"""
        mapping = {
            "py": "Python",
            "js": "JavaScript",
            "ts": "TypeScript",
            "jsx": "React JSX",
            "tsx": "React TypeScript",
            "html": "HTML",
            "css": "CSS",
            "java": "Java",
            "go": "Go",
            "rs": "Rust",
            "c": "C",
            "cpp": "C++",
            "cs": "C#",
            "php": "PHP",
            "rb": "Ruby",
            "swift": "Swift",
            "kt": "Kotlin",
            "md": "Markdown",
            "json": "JSON",
            "yml": "YAML",
            "yaml": "YAML",
            "sql": "SQL",
            "sh": "Shell",
        }
        
        return mapping.get(extension, "general code")

def create_code_builder_agent(knowledge_base=None):
    """Create a CodeBuilderAgent with RAG capabilities."""
    return CodeBuilderAgent(knowledge_base=knowledge_base)