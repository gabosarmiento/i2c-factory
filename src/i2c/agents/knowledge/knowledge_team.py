# src/i2c/agents/knowledge_team/knowledge_team.py

from typing import Dict, Any, List, Optional
from pathlib import Path
import asyncio
from builtins import llm_highest, llm_middle
from agno.team import Team
from agno.agent import Agent

# Import existing knowledge components
from i2c.agents.knowledge.knowledge_manager import ExternalKnowledgeManager
from i2c.workflow.modification.rag_retrieval import retrieve_context_for_planner
from i2c.workflow.modification.rag_config import get_embed_model
from i2c.db_utils import get_db_connection
from i2c.cli.controller import canvas

class KnowledgeLeadAgent(Agent):
    """Lead agent for the Knowledge Team that coordinates context retrieval and analysis"""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="KnowledgeLead",
            model=llm_middle,  # Using OpenAI's GPT-4o as high-tier LLM
            role="Leads the knowledge team to provide context for code evolution",
            instructions=[
                "You are the lead of the Knowledge Team, responsible for retrieving and analyzing context.",
                "Your job is to coordinate the retrieval of relevant knowledge from various sources.",
                "You must ensure that the context provided is accurate, relevant, and comprehensive.",
                "Work with your team to retrieve code context, documentation, and best practices.",
                "Synthesize all retrieved knowledge into a cohesive context for the other teams."
            ],
            **kwargs
        )
        # Initialize team session state if needed
        if self.team_session_state is None:
            self.team_session_state = {}
        
        # Initialize embedding model and knowledge manager
        self.embed_model = None
        if self.team_session_state.get("embed_model") is not None:
            self.embed_model = self.team_session_state.get("embed_model")
        else:
            try:
                self.embed_model = get_embed_model()
                if self.team_session_state is not None:
                    self.team_session_state["embed_model"] = self.embed_model
            except Exception as e:
                canvas.warning(f"Failed to initialize embedding model: {e}")
                
        # Initialize knowledge manager if embed_model is available
        self.knowledge_manager = None
        if self.embed_model:
            try:
                db_path = self.team_session_state.get("db_path", "./data/lancedb")
                self.knowledge_manager = ExternalKnowledgeManager(
                    embed_model=self.embed_model,
                    db_path=db_path
                )
            except Exception as e:
                canvas.warning(f"Failed to initialize knowledge manager: {e}")
    
    async def analyze_project_context(self, project_path: Path, task: str) -> Dict[str, Any]:
        """
        Analyze the project context for a specific task.
        
        Args:
            project_path: Path to the project directory
            task: Description of the code evolution task
            
        Returns:
            Dictionary with project analysis results
        """
        canvas.info(f"Analyzing project context for task: {task}")
        
        # This function will coordinate the knowledge team activities
        try:
            # 1. Analyze project structure
            project_structure = self._analyze_project_structure(project_path)
            canvas.info(f"Identified {len(project_structure['files'])} files in project")
            
            # 2. Retrieve relevant code context using RAG
            code_context = await self._retrieve_code_context(project_path, task)
            canvas.info(f"Retrieved {len(code_context.get('context', ''))} characters of code context")
            
            # 3. Retrieve relevant documentation using Knowledge Manager
            documentation = await self._retrieve_documentation(task)
            canvas.info(f"Retrieved {len(documentation.get('references', []))} documentation references")
            
            # 4. Identify best practices
            best_practices = await self._identify_best_practices(task, project_structure["languages"])
            canvas.info(f"Identified {len(best_practices)} best practices")
            
            # 5. Synthesize context
            context = {
                "project_structure": project_structure,
                "code_context": code_context,
                "documentation": documentation,
                "best_practices": best_practices,
                "task_analysis": {
                    "description": task,
                    "identified_targets": self._identify_target_files(project_path, task, code_context)
                }
            }
            
            # Store in team session state
            if self.team_session_state is not None:
                self.team_session_state["project_context"] = context
            
            return context
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            canvas.error(f"Knowledge team error: {e}")
            canvas.error(error_details)
            
            error_info = {
                "error": f"Knowledge team error: {str(e)}",
                "error_details": error_details
            }
            
            # Store error in the team session state
            if self.team_session_state is not None:
                self.team_session_state["project_context"] = error_info
                
            return error_info
    
    def _analyze_project_structure(self, project_path: Path) -> Dict[str, Any]:
        """Analyze project structure to identify files, languages, and dependencies"""
        # Basic implementation - extract file structure and languages
        languages = {}
        dependencies = []
        files = []
        
        for file_path in project_path.glob("**/*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(project_path)
                files.append(str(rel_path))
                
                # Map extensions to languages
                ext = file_path.suffix
                if ext:
                    lang = self._map_extension_to_language(ext)
                    if lang:
                        languages[lang] = languages.get(lang, 0) + 1
                
                # Check for dependency files
                if file_path.name in ["requirements.txt", "package.json", "Gemfile", "Cargo.toml"]:
                    dependencies.append(str(rel_path))
        
        return {
            "files": files,
            "languages": languages,
            "dependencies": dependencies
        }
    
    def _map_extension_to_language(self, ext: str) -> Optional[str]:
        """Map file extension to programming language"""
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".cpp": "c++",
            ".hpp": "c++",
            ".c": "c",
            ".h": "c",
            ".rb": "ruby",
            ".go": "go",
            ".rs": "rust",
            ".php": "php",
            ".cs": "csharp",
            ".swift": "swift",
            ".kt": "kotlin",
            ".html": "html",
            ".css": "css",
            ".sql": "sql",
        }
        return mapping.get(ext.lower())
    
    async def _retrieve_code_context(self, project_path: Path, task: str) -> Dict[str, Any]:
        """Retrieve relevant code context for the task using RAG"""
        context = {}
        
        # Use the existing RAG retrieval function if available
        try:
            if self.embed_model:
                db = get_db_connection()
                if db:
                    # Use the existing retrieve_context_for_planner function
                    context_str = retrieve_context_for_planner(
                        user_request=task,
                        db=db,
                        embed_model=self.embed_model
                    )
                    context["context"] = context_str
                    
                    # Try to extract relevant files from the context
                    relevant_files = []
                    for line in context_str.split('\n'):
                        if line.startswith("FILE: "):
                            file_path = line[6:].strip()
                            relevant_files.append(file_path)
                    
                    context["relevant_files"] = relevant_files
        except Exception as e:
            canvas.warning(f"Error retrieving code context: {e}")
            context["error"] = str(e)
        
        return context
    
    async def _retrieve_documentation(self, task: str) -> Dict[str, Any]:
        """Retrieve relevant documentation for the task"""
        documentation = {"references": [], "api_docs": {}}
        
        # Use the ExternalKnowledgeManager if available
        if self.knowledge_manager:
            try:
                # Retrieve knowledge for the task
                knowledge_items = self.knowledge_manager.retrieve_knowledge(
                    query=task,
                    limit=5
                )
                
                if knowledge_items:
                    documentation["references"] = knowledge_items
            except Exception as e:
                canvas.warning(f"Error retrieving documentation: {e}")
                documentation["error"] = str(e)
        
        return documentation
    
    async def _identify_best_practices(self, task: str, languages: Dict[str, int]) -> List[Dict[str, str]]:
        """Identify best practices for the task and languages"""
        best_practices = []
        
        # Determine the primary language
        primary_language = None
        if languages:
            primary_language = max(languages.items(), key=lambda x: x[1])[0]
        
        # Use the knowledge manager to retrieve best practices
        if self.knowledge_manager and primary_language:
            try:
                best_practice_query = f"best practices for {primary_language} {task}"
                best_practice_items = self.knowledge_manager.retrieve_knowledge(
                    query=best_practice_query,
                    limit=3
                )
                
                if best_practice_items:
                    for item in best_practice_items:
                        best_practices.append({
                            "language": primary_language,
                            "practice": item["content"],
                            "source": item["source"]
                        })
            except Exception as e:
                canvas.warning(f"Error identifying best practices: {e}")
        
        return best_practices
    
    def _identify_target_files(
        self, project_path: Path, task: str, code_context: Dict[str, Any]
    ) -> List[str]:
        """Identify target files likely to be modified for the task"""
        target_files = set()
        
        # First, check relevant files from code context
        relevant_files = code_context.get("relevant_files", [])
        for file_path in relevant_files:
            target_files.add(file_path)
        
        # Then, look for files matching task keywords
        keywords = task.lower().split()
        for file_path in project_path.glob("**/*.*"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(project_path))
                
                # Skip if already added
                if rel_path in target_files:
                    continue
                
                # Check filename for keywords
                filename = file_path.name.lower()
                if any(keyword in filename for keyword in keywords):
                    target_files.add(rel_path)
                    continue
                
                # Check file content for keywords
                try:
                    # Only check relatively small files
                    if file_path.stat().st_size < 50000:  # 50KB limit
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        if any(keyword in content.lower() for keyword in keywords):
                            target_files.add(rel_path)
                except Exception:
                    # Skip files that can't be read
                    pass
        
        return list(target_files)

def build_knowledge_team(session_state=None) -> Team:
    """
    Build the knowledge team with a lead agent.
    
    Args:
        session_state: Optional shared session state dict
        
    Returns:
        Team: Configured knowledge team
    """
    # Create the knowledge lead agent
    knowledge_lead = KnowledgeLeadAgent()
    
    # Use shared session if provided, else default
    session_state = session_state or {
        "project_context": None,
        "db_path": "./data/lancedb"
    }
    
    return Team(
        name="KnowledgeTeam",
        members=[knowledge_lead],
        mode="collaborate",
        model=llm_middle,
        instructions=[
            "You are the Knowledge Team, responsible for retrieving and analyzing context.",
            "Follow the lead of the KnowledgeLead agent, who will coordinate your activities.",
            "Ensure that the context you provide is accurate, relevant, and comprehensive.",
            "Focus on retrieving information that will help the other teams perform their tasks."
        ],
        session_state=session_state
    )
