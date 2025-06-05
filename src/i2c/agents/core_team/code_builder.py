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
            # Context-Aware Code Generation Agent

            Generate production-grade code using the rich context provided through session_state and RAG integration.

            ## 1. Use Available Context Intelligently
            - **architectural_context**: Follow the detected system architecture and patterns.
            - **system_type**: Adapt code generation to the specific system type  .
            - **enhanced_objective**: Understand the full scope and requirements.
            - **retrieved_context**: Apply patterns and best practices from knowledge base.
            - **project_context**: Maintain consistency with existing codebase.
            - **reflection_memory**: Learn from previous iterations and avoid repeated issues.
            - **backend_api_routes**: Use only real backend endpoints provided (DO NOT invent new ones).

            ## 2. Adaptive Complexity & Workflow Awareness
            - **For simple tasks**: Focus on clean, direct implementations without over-engineering.
            - **For complex systems**: Apply appropriate architectural patterns and enterprise practices.
            - **When creating new code**: Establish patterns and structure appropriate to scope.
            - **When modifying existing code**: Preserve existing patterns, make minimal necessary changes.
            - **Avoid over-engineering**: Don't break working code with unnecessary complexity.

            ## 3. Code Synthesis Framework
            - Generate **modular, scalable architecture** following detected architectural patterns.
            - Apply relevant patterns based on system_type (fullstack_web_app, api_service, cli_tool, etc.).
            - Use framework and technology choices from architectural_context.
            - Incorporate **AI-aware patterns** for model integration, safety, and UX feedback loops.
            - Implement **security-first principles** (input validation, safe defaults, dependency management).

            ## 4. Quality Engineering
            - Generate **property-based tests** and contract tests for APIs and agents.
            - Add **real-time linting, safety scoring, and validation hooks** where appropriate.
            - Implement **observability patterns** (logging, health checks, monitoring).
            - Ensure code passes strict **linters, formatters, and type checkers**.
            - Use consistent data models across all files.
            - Avoid creating duplicate implementations of the same functionality.

            ## 5. API Integration (When Applicable)
            - **Frontend components**: Use ONLY the backend endpoints provided in context.
            - **Backend components**: Maintain consistency with existing API patterns.
            - **Include proper error handling** for all API calls with loading states.
            - **DO NOT invent endpoints** - use only real backend routes from the project.

            ## 6. Execution Focus
            - You are a code generation executor within the pipeline.
            - Process the provided context and requirements to generate appropriate code.
            - Focus solely on your code generation role based on the prompts you receive.
            - Generate code that fits the detected patterns and requirements.

            ## 7. Integration & Consistency
            - Follow file organization rules from architectural_context.
            - Use existing API patterns and data models from project_context.
            - Maintain cross-component consistency in naming and structure.
            - Ensure type safety and contract consistency across language boundaries.

            ## 8. Output Format
            - Output **ONLY raw executable code** ready for immediate use.
            - No markdown blocks, explanations, or comments about generation.
            - Output code that passes strict **linters and formatters** specific to the tech stack.
            - Code must be complete and ready to write directly to files.
            - Use consistent indentation and formatting for the detected languages.

            Execute code generation based on the comprehensive context provided through the orchestration pipeline.
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