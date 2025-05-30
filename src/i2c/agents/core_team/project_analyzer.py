# src/i2c/agents/core_team/project_analyzer.py
from typing import List
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

def create_project_analyzer_agent(knowledge_base=None):
    """Create a ProjectContextAnalyzerAgent with RAG capabilities."""
    return ProjectContextAnalyzerAgent(knowledge_base=knowledge_base)