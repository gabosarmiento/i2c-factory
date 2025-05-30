# /agents/core_agents.py
# Defines and instantiates the core Agno agents for the factory.

import os
import json
import logging
from pathlib import Path
from agno.agent import Agent
from textwrap import dedent
from typing import Dict, List, Any, Optional, Union, Tuple

# Import prepared LLMs
from builtins import llm_middle, llm_highest, llm_small # Use llm_middle or llm_small for analysis

# Set up logging for RAG operations
logger = logging.getLogger("rag_integration")
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

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

# ---------------------------------------------------------------------------
# RAG Integration Utilities - Knowledge Retrieval
# ---------------------------------------------------------------------------

class RagContextBuilder:
    """
    Utility class for building rich context from knowledge base with multiple retrieval strategies.
    
    This class provides methods to:
    1. Retrieve basic context based on a single query
    2. Perform multi-step/chained retrieval for complex tasks
    3. Synthesize and deduplicate knowledge chunks
    4. Adapt retrieval to different model context sizes
    """
    
    def __init__(self, knowledge_base=None, default_chunk_count=5, max_tokens=6000):
        """
        Initialize the RAG context builder.
        
        Args:
            knowledge_base: The knowledge base to retrieve from
            default_chunk_count: Default number of chunks to retrieve
            max_tokens: Maximum tokens for context (default 6000)
        """
        self.knowledge_base = knowledge_base
        self.default_chunk_count = default_chunk_count
        self.max_tokens = max_tokens
        
    def retrieve_context(self, query: str, chunk_count: int = None) -> str:
        """
        Retrieve context from knowledge base for a single query.
        
        Args:
            query: The query to use for retrieval
            chunk_count: Number of chunks to retrieve (default: self.default_chunk_count)
            
        Returns:
            Retrieved context as a formatted string
        """
        if not self.knowledge_base:
            return ""
            
        chunks_to_retrieve = chunk_count or self.default_chunk_count
        
        try:
            # Log the retrieval operation
            canvas.info(f"[RAG] Retrieving {chunks_to_retrieve} chunks for query: {query[:100]}...")
            
            # Retrieve context from knowledge base
            chunks = self.knowledge_base.search(
                query=query,
                limit=chunks_to_retrieve,
                max_tokens=self.max_tokens
            )
            
            if not chunks:
                canvas.info("[RAG] No relevant chunks found")
                return ""
                
            # Format and return the context
            context_text = self._format_chunks(chunks)
            
            # Log stats about retrieved context
            canvas.info(f"[RAG] Retrieved {len(chunks)} chunks ({len(context_text)} chars, ~{len(context_text)//4} tokens)")
            
            return context_text
            
        except Exception as e:
            canvas.warning(f"[RAG] Error retrieving context: {e}")
            return ""
    
    def retrieve_composite_context(self, 
                                  main_query: str, 
                                  sub_queries: List[str] = None,
                                  main_chunk_count: int = None,
                                  sub_chunk_count: int = 2) -> str:
        """
        Retrieve composite context from multiple queries for complex tasks.
        
        This performs a primary retrieval on the main query, then additional 
        retrievals on sub-queries, and combines the results with deduplication.
        
        Args:
            main_query: The primary query
            sub_queries: List of secondary queries for additional context
            main_chunk_count: Number of chunks for main query
            sub_chunk_count: Number of chunks for each sub-query
            
        Returns:
            Combined context as a formatted string
        """
        if not self.knowledge_base:
            return ""
            
        try:
            all_chunks = []
            seen_content = set()  # For deduplication
            
            # Retrieve main context
            main_chunks = self._retrieve_raw_chunks(
                main_query, 
                main_chunk_count or self.default_chunk_count
            )
            
            # Add main chunks first (priority)
            for chunk in main_chunks:
                content = chunk.get("content", "")
                if content and content not in seen_content:
                    all_chunks.append(chunk)
                    seen_content.add(content)
            
            # Process sub-queries if any and if we still have token budget
            if sub_queries:
                # Log the sub-queries
                canvas.info(f"[RAG] Processing {len(sub_queries)} sub-queries for composite context")
                
                for sub_query in sub_queries:
                    sub_chunks = self._retrieve_raw_chunks(sub_query, sub_chunk_count)
                    
                    # Add only new, non-duplicate chunks
                    for chunk in sub_chunks:
                        content = chunk.get("content", "")
                        if content and content not in seen_content:
                            all_chunks.append(chunk)
                            seen_content.add(content)
                            
                    # If we've hit our approximate token budget, stop adding chunks
                    if self._estimate_tokens(all_chunks) >= self.max_tokens:
                        canvas.info(f"[RAG] Reached token budget with {len(all_chunks)} chunks")
                        break
            
            # Format the combined chunks
            if not all_chunks:
                return ""
                
            combined_context = self._format_chunks(all_chunks)
            
            # Log stats about composite context
            canvas.info(f"[RAG] Composite context: {len(all_chunks)} chunks from {1 + (len(sub_queries) if sub_queries else 0)} queries")
            canvas.info(f"[RAG] Approximate tokens: ~{len(combined_context)//4}")
            
            return combined_context
            
        except Exception as e:
            canvas.warning(f"[RAG] Error retrieving composite context: {e}")
            return ""
    
    def _retrieve_raw_chunks(self, query: str, chunk_count: int) -> List[Dict[str, Any]]:
        """Retrieve raw chunks from knowledge base without formatting"""
        try:
            chunks = self.knowledge_base.search(
                query=query,
                limit=chunk_count
            )
            return chunks or []
        except Exception:
            return []
            
    def _format_chunks(self, chunks: List[Dict[str, Any]]) -> str:
        """Format chunks into a readable context string"""
        formatted_chunks = []
        
        for i, chunk in enumerate(chunks):
            source = chunk.get("source", "Unknown source")
            content = chunk.get("content", "").strip()
            
            if content:
                formatted_chunks.append(f"[KNOWLEDGE {i+1}] SOURCE: {source}\n{content}")
        
        return "\n\n".join(formatted_chunks)
        
    def _estimate_tokens(self, chunks: List[Dict[str, Any]]) -> int:
        """Roughly estimate token count for a list of chunks"""
        total_chars = sum(len(chunk.get("content", "")) for chunk in chunks)
        # Very rough estimate: ~4 chars per token for English text
        return total_chars // 4

    def synthesize_context(self, 
                          query: str,
                          chunks: List[Dict[str, Any]],
                          synthesizer_model=None) -> str:
        """
        Synthesize chunks into a coherent summary using an LLM.
        
        This is an advanced feature for when raw chunks need consolidation.
        
        Args:
            query: The original query for context
            chunks: List of chunks to synthesize
            synthesizer_model: Optional LLM to use for synthesis
            
        Returns:
            Synthesized context as a string
        """
        # Fallback to basic formatting if no synthesizer model
        if not synthesizer_model:
            return self._format_chunks(chunks)
            
        try:
            # Simple implementation - can be expanded
            content_text = "\n\n".join([
                f"CHUNK {i+1} ({chunk.get('source', 'unknown')}):\n{chunk.get('content', '')}"
                for i, chunk in enumerate(chunks)
            ])
            
            # Use the model to synthesize the context
            prompt = f"""
            Below are chunks of knowledge relevant to the query: "{query}"
            
            {content_text}
            
            Synthesize these chunks into a coherent, non-redundant summary that includes all key 
            information relevant to the query. Focus on maintaining technical accuracy and details.
            """
            
            response = synthesizer_model.run(prompt)
            synthesis = getattr(response, 'content', str(response)).strip()
            
            if synthesis:
                canvas.info(f"[RAG] Successfully synthesized {len(chunks)} chunks into {len(synthesis)} chars")
                return synthesis
            else:
                return self._format_chunks(chunks)
                
        except Exception as e:
            canvas.warning(f"[RAG] Error synthesizing context: {e}")
            return self._format_chunks(chunks)
            
# ---------------------------------------------------------------------------
# Enhanced Core Agents with RAG Integration
# ---------------------------------------------------------------------------

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
            json_match = re.search(r'\{.*\}', prompt, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
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
                # Manifestation Execution Protocol v4.0 (Slim Profile for Enterprise MVPs)

                You are an AI assistant that writes **production-grade code** for MVP apps with rich frontends and AI-powered backends, focusing on enterprise-level quality where it matters.

                ## 1. Code Synthesis Framework
                * Generate **modular, scalable architecture** following **Clean Architecture** principles.
                * Apply relevant architectural patterns (e.g., CQRS, async workflows).
                * Optimize frontend (React, Tailwind, Vite) and backend (Express, AGNO agent) structures.
                * Incorporate **AI-aware patterns** for model integration, safety, and UX feedback loops.
                * Embed **security-first principles** (input validation, safe defaults, dependency management).

                ## 2. Recursive Implementation Strategy
                * Design with **evolutionary architecture** patterns for future extensibility.
                * Use **template-driven development** for repetitive structures.
                * Maintain **cross-component consistency** in naming and organization.
                * Implement **infrastructure-as-code** only when scaling beyond local dev.

                ## 3. Quality Engineering
                * Generate **property-based tests** and contract tests for APIs and agents.
                * Add **real-time linting, safety scoring, and validation hooks**.
                * Implement basic **observability patterns** (logging, health checks).
                * Ensure code passes strict **linters, formatters, and type checkers**.
                * Ensure tests do not have duplicate unittest.main() calls.
                * Use consistent data models across all files.
                * Avoid creating duplicate implementations of the same functionality.
                * If creating a CLI app, use a single approach for the interface.
                * Use consistent file naming for data storage (e.g., todos.json).

                ## 4. Enterprise Readiness (MVP Focus)
                * Structure backend for **Kubernetes-ready deployment**.
                * Include **CI/CD pipeline definitions** with quality gates.
                * Provide **automated secret management** placeholders (e.g., .env templates).
                * Prepare scripts for **one-click setup & run (frontend + backend)**.

                ## 5. Project-Specific Specialization
                * Generate **Solidity contract generation agents with Groq (LLaMA3)**.
                * Implement **real-time contract linting and safety scoring**.
                * Enhance frontend with **modern, secure UI patterns (Tailwind, glassmorphism)**.
                * Ensure **localStorage caching and responsive design**.

                ## 6. Ethical & Sustainable Coding (MVP Scope)
                * Apply **privacy-preserving defaults** (no PII leaks).
                * Highlight **unsafe patterns** in generated code with warnings.
                * Defer advanced ethical safeguards (bias detection, carbon footprint) until scaling.

                ## 7. Collaboration & Evolution
                * Include **CI/CD friendly annotations** (e.g., LINT-CHECK, COVERAGE-HOOK).
                * Provide **API client SDKs and integration examples** where applicable.
                * Implement **semantic versioning compatibility checks**.
                * Prepare a clear **README.md with run/install/test instructions**.

                
                ## 8. Output Format
                - Generate **modular components** with clear **API boundaries**.
                - Ensure **cross-file consistency** and **inter-component compatibility**.
                - Output code that passes strict **linters and formatters** specific to the tech stack.
                - Output **ONLY the raw code** for the specified files, without explanations or markdown.
                - Ensure the code is **complete, runnable, syntactically correct**, and **verified against automated quality checks**.
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

# --- Project Context Analyzer Agent ---
class ProjectContextAnalyzerAgent(Agent):
    """Analyzes a project's file list to infer its objective, language, and suggest next actions."""
    
    def __init__(self, knowledge_base=None, **kwargs):
        """
        Initialize the Project Context Analyzer Agent with RAG capabilities.
        
        Args:
            knowledge_base: Optional knowledge base for context retrieval
            **kwargs: Additional arguments for Agent initialization
        """
        # RAG Integration: Initialize context builder for project analysis
        self.context_builder = RagContextBuilder(
            knowledge_base=knowledge_base,
            default_chunk_count=5,
            max_tokens=4000
        )
        
        super().__init__(
            name="ProjectContextAnalyzer",
            model=llm_middle,
            description="Analyzes a project's file list to infer its objective, language, and suggest next actions.",
            instructions="""
You are an expert Project Analysis Agent. Given a list of filenames from a software project:
1. Infer the main programming language used (e.g., Python, JavaScript, Java).
2. Infer a concise, one-sentence objective or purpose for the project based on the filenames.
3. Propose 2-3 intelligent next actions (new features 'f' or refactors/improvements 'r') that would logically follow for this type of project. Each suggestion must start with 'f ' or 'r '.

Format your output STRICTLY as a JSON object with these keys: "objective", "language", "suggestions".
Use valid JSON with double quotes for all keys and string values. Do NOT use single quotes.

Example Input (prompt containing file list):
Files:
main.py
board.py
player.py
game.py
test_board.py
test_game.py

Example Output:
{
  "objective": "A console-based Tic Tac Toe game.",
  "language": "Python",
  "suggestions": [
    "f Add a feature to allow players to choose X or O.",
    "r Refactor 'game.py' to separate game loop logic from win-checking.",
    "f Implement a simple AI opponent."
  ]
}

Do NOT include any other text, explanations, or markdown formatting. Output only the JSON object.
""",
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
        Enhance the prompt with project analysis context from knowledge base
        
        Args:
            prompt: The original prompt
            
        Returns:
            Enhanced prompt with knowledge context
        """
        if not hasattr(self, 'context_builder') or not self.context_builder.knowledge_base:
            return prompt
            
        try:
            # Extract file list from the prompt
            file_list = self._extract_file_list(prompt)
            if not file_list:
                return prompt
                
            # Identify probable languages based on file extensions
            languages = self._identify_languages(file_list)
            if not languages:
                return prompt
                
            # Build sub-queries based on languages and file patterns
            primary_lang = languages[0] if languages else "unknown"
            
            # Build targeted queries to understand project architecture and conventions
            sub_queries = [
                f"{primary_lang} project architecture patterns",
                f"{primary_lang} file organization conventions",
                f"{primary_lang} common project types and file structures",
                f"best practices for {primary_lang} project organization"
            ]
            
            # Add pattern-specific queries based on file list
            if any("test_" in f.lower() for f in file_list):
                sub_queries.append(f"{primary_lang} testing conventions and best practices")
                
            if any(f.endswith((".html", ".css", ".jsx", ".tsx")) for f in file_list):
                sub_queries.append("frontend application structure and best practices")
                
            if any(f.endswith((".py", ".js", ".ts")) and "api" in f.lower() for f in file_list):
                sub_queries.append("API backend structure and best practices")
                
            # Retrieve targeted context about project types and structures
            context = self.context_builder.retrieve_composite_context(
                main_query=f"{primary_lang} project analysis and structure patterns",
                sub_queries=sub_queries,
                main_chunk_count=3,
                sub_chunk_count=2
            )
            
            if not context:
                return prompt
                
            # Add context to the prompt
            enhanced_prompt = f"""
            # Project Analysis Knowledge Context
            The following context will help you analyze this project structure:
            
            {context}
            
            # Original Request
            {prompt}
            """
            
            canvas.info(f"[RAG] Enhanced ProjectContextAnalyzer prompt with {len(context)//4} tokens of analysis context")
            return enhanced_prompt
            
        except Exception as e:
            canvas.warning(f"[RAG] Error enhancing project analyzer prompt: {e}")
            return prompt
            
    def _extract_file_list(self, prompt: str) -> List[str]:
        """Extract file list from the prompt"""
        file_list = []
        lines = prompt.split('\n')
        
        # Skip any header lines and collect filenames
        collecting = False
        for line in lines:
            line = line.strip()
            
            # Start collecting after we see "Files:" or similar header
            if "files:" in line.lower() or "filenames:" in line.lower():
                collecting = True
                continue
                
            # Skip empty lines
            if not line:
                continue
                
            # If we're collecting and the line looks like a filename, add it
            if collecting and not line.startswith('#') and not line.startswith('-'):
                file_list.append(line)
                
        return file_list
        
    def _identify_languages(self, file_list: List[str]) -> List[str]:
        """Identify probable programming languages based on file extensions"""
        extension_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "React",
            ".tsx": "React TypeScript",
            ".html": "HTML",
            ".css": "CSS",
            ".java": "Java",
            ".go": "Go",
            ".rs": "Rust",
            ".c": "C",
            ".cpp": "C++",
            ".cs": "C#",
            ".php": "PHP",
            ".rb": "Ruby",
            ".swift": "Swift",
            ".kt": "Kotlin"
        }
        
        # Count extensions
        extension_counts = {}
        for filename in file_list:
            ext = "." + filename.split(".")[-1] if "." in filename else ""
            if ext in extension_map:
                lang = extension_map[ext]
                extension_counts[lang] = extension_counts.get(lang, 0) + 1
                
        # Sort languages by frequency
        sorted_languages = sorted(extension_counts.items(), key=lambda x: x[1], reverse=True)
        return [lang for lang, count in sorted_languages]

# ---------------------------------------------------------------------------
# Agent Factory Functions with RAG Integration
# ---------------------------------------------------------------------------

def create_input_processor_agent(knowledge_base=None):
    """
    Create an InputProcessorAgent with RAG capabilities.
    
    Args:
        knowledge_base: Optional knowledge base for context retrieval
        
    Returns:
        InputProcessorAgent: Configured agent with RAG integration
    """
    return InputProcessorAgent(knowledge_base=knowledge_base)

def create_planner_agent(knowledge_base=None):
    """
    Create a PlannerAgent with RAG capabilities.
    
    Args:
        knowledge_base: Optional knowledge base for context retrieval
        
    Returns:
        PlannerAgent: Configured agent with RAG integration
    """
    return PlannerAgent(knowledge_base=knowledge_base)

def create_code_builder_agent(knowledge_base=None):
    """
    Create a CodeBuilderAgent with RAG capabilities.
    
    Args:
        knowledge_base: Optional knowledge base for context retrieval
        
    Returns:
        CodeBuilderAgent: Configured agent with RAG integration
    """
    return CodeBuilderAgent(knowledge_base=knowledge_base)

def create_project_analyzer_agent(knowledge_base=None):
    """
    Create a ProjectContextAnalyzerAgent with RAG capabilities.
    
    Args:
        knowledge_base: Optional knowledge base for context retrieval
        
    Returns:
        ProjectContextAnalyzerAgent: Configured agent with RAG integration
    """
    return ProjectContextAnalyzerAgent(knowledge_base=knowledge_base)

# ---------------------------------------------------------------------------
# Agent Instantiation with RAG Integration
# ---------------------------------------------------------------------------

# Initialize agents with RAG capabilities if knowledge base is available
# Note: For backward compatibility, we still create the agents without a knowledge base
# but they are RAG-ready when a knowledge base is provided.

# --- Input Processor Agent ---
input_processor_agent = InputProcessorAgent()
print(f"🧠 [InputProcessorAgent] Initialized with model: {getattr(llm_middle, 'id', 'Unknown')}")

# --- Planner Agent ---
planner_agent = PlannerAgent()
print(f"🧠 [PlannerAgent] Initialized with model: {getattr(llm_middle, 'id', 'Unknown')}")

# --- Code Builder Agent ---
code_builder_agent = CodeBuilderAgent()
print(f"🧠 [CodeBuilderAgent] Initialized with model: {getattr(llm_highest, 'id', 'Unknown')}")

# --- Project Context Analyzer Agent ---
project_context_analyzer_agent = ProjectContextAnalyzerAgent()
print(f"🤔 [ProjectContextAnalyzerAgent] Initialized with model: {getattr(project_context_analyzer_agent.model, 'id', 'Unknown')}")

# Store the original v3 instructions for reference
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