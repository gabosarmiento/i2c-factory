# src/i2c/agents/knowledge_team/knowledge_team.py

from typing import Dict, Any, List, Optional
from pathlib import Path
import asyncio
from builtins import llm_highest, llm_middle
from agno.team import Team
from agno.agent import Agent
import traceback

# Import existing knowledge components
from i2c.agents.knowledge.enhanced_knowledge_ingestor import EnhancedKnowledgeIngestorAgent
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
        # Use global session state instead of team_session_state
        if self.session_state is None:
            self.session_state = {}

        # Initialize embedding model and knowledge manager using global keys
        self.embed_model = None
        if self.session_state.get("embed_model") is not None:
            self.embed_model = self.session_state.get("embed_model")
        else:
            try:
                self.embed_model = get_embed_model()
                if self.session_state is not None:
                    self.session_state["embed_model"] = self.embed_model
            except Exception as e:
                canvas.warning(f"Failed to initialize embedding model: {e}")
                
        # Initialize knowledge manager and enhanced ingestor if embed_model is available
        self.knowledge_manager = None
        self.enhanced_ingestor = None
        if self.embed_model:
            try:
                db_path = self.session_state.get("db_path", "./data/lancedb")
                self.knowledge_manager = ExternalKnowledgeManager(
                    embed_model=self.embed_model,
                    db_path=db_path
                )
                
                # Add enhanced ingestor with caching
                from i2c.agents.budget_manager import BudgetManagerAgent
                budget_manager = self.session_state.get("budget_manager") or BudgetManagerAgent()
                knowledge_space = self.session_state.get("knowledge_space", "default")
                
                self.enhanced_ingestor = EnhancedKnowledgeIngestorAgent(
                    budget_manager=budget_manager,
                    knowledge_space=knowledge_space,
                    embed_model=self.embed_model
                )
            except Exception as e:
                canvas.warning(f"Failed to initialize knowledge components: {e}")
                
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

            # Delegate context evolution to AGNO team
            if self.session_state is not None:
                evolved_context = await self._delegate_to_context_evolution_team(context, task)
                self.session_state["retrieved_context"] = evolved_context
                context = evolved_context

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
            if self.session_state is not None:
                self.session_state["retrieved_context"] = error_info
                
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
        
        # DEBUG: Check what knowledge manager we're using
        canvas.info(f"🔍 DEBUG: Knowledge manager available: {self.knowledge_manager is not None}")
        
        # Use the ExternalKnowledgeManager if available
        if self.knowledge_manager:
            try:
                canvas.info(f"🔍 DEBUG: Querying knowledge manager for: {task}")
                
                # Retrieve knowledge for the task
                knowledge_items = self.knowledge_manager.retrieve_knowledge(
                    query=task,
                    limit=5
                )
                
                canvas.info(f"🔍 DEBUG: Knowledge manager returned {len(knowledge_items)} items")
                
                if knowledge_items:
                    for i, item in enumerate(knowledge_items[:2]):
                        if isinstance(item, dict):
                            content_preview = item.get('content', str(item))[:100]
                        else:
                            content_preview = str(item)[:100]
                        canvas.info(f"🔍 DEBUG: Item {i}: {content_preview}...")
                    
                    documentation["references"] = knowledge_items
            except Exception as e:
                canvas.warning(f"Error retrieving documentation: {e}")
                canvas.error(f"🔍 DEBUG: Full error: {traceback.format_exc()}")
                documentation["error"] = str(e)
        else:
            canvas.error("🔍 DEBUG: No knowledge manager available!")
        
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
    
    async def ingest_project_documentation(
        self, 
        project_path: Path, 
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Ingest project documentation with smart caching"""
        
        if not self.enhanced_ingestor:
            canvas.warning("Enhanced ingestor not available")
            return {"success": False, "error": "No ingestor available"}
        
        canvas.info(f"Ingesting documentation from {project_path}")
        
        try:
            # Use the enhanced ingestor with caching
            success, results = self.enhanced_ingestor.execute(
                document_path=project_path,
                document_type="project_documentation",
                metadata={
                    "project_path": str(project_path),
                    "ingested_by": "knowledge_team"
                },
                force_refresh=force_refresh,
                recursive=True
            )
            
            if success:
                canvas.success(f"✅ Ingested {results['successful_files']} files, "
                            f"skipped {results['skipped_files']} (cached)")
            
            return {"success": success, "results": results}
            
        except Exception as e:
            canvas.error(f"Error ingesting documentation: {e}")
            return {"success": False, "error": str(e)}

    def _apply_team_recommendations(self, context: Dict[str, Any], team_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Apply the team's recommendations to evolve context size and content"""
        
        strategy = team_analysis.get('context_evolution_strategy', {})
        target_size = strategy.get('target_context_size', 9000)
        
        canvas.info(f"🧠 Applying team strategy to reduce context size")
        
        # Apply team recommendations:
        # 1. Summarize historical information
        # 2. Prioritize current project state  
        # 3. Discard redundant information
        
        evolved_context = context.copy()
        
        # Reduce documentation references if they're too verbose
        if "documentation" in evolved_context and "references" in evolved_context["documentation"]:
            refs = evolved_context["documentation"]["references"]
            if len(refs) > 3:  # Keep only most relevant
                canvas.info(f"🧠 Reducing documentation references: {len(refs)} → 3")
                evolved_context["documentation"]["references"] = refs[:3]
        
        # Summarize code context if too large
        if "code_context" in evolved_context and "context" in evolved_context["code_context"]:
            code_context = evolved_context["code_context"]["context"]
            if len(code_context) > 2000:  # Summarize if too long
                canvas.info(f"🧠 Summarizing code context: {len(code_context)} chars")
                # Keep first 1000 and last 500 chars (current state)
                evolved_context["code_context"]["context"] = code_context[:1000] + "...[summarized]..." + code_context[-500:]
        
        new_size = len(str(evolved_context))
        canvas.success(f"🧠 Context evolved: {len(str(context))} → {new_size} chars")
        
        return evolved_context

    async def _delegate_to_context_evolution_team(self, new_context: Dict[str, Any], task: str) -> Dict[str, Any]:
        """Delegate context evolution to specialized AGNO team"""
        
        try:
            from i2c.agents.knowledge.context_evolution_team import build_context_evolution_team
            
            # Use the workflow session_state instead of session_state
        
            evolution_team = build_context_evolution_team(session_state=self.session_state)
            
            evolution_request = f"""
            Task: {task}
            New context: {new_context}
            Previous context: {self.session_state.get('retrieved_context', {})}
            
            Team: collaborate on evolving project context intelligently.
            """
            from agno.agent import Message
            result = await evolution_team.arun(Message(role="user", content=evolution_request))
            
            # Extract JSON from team response using existing utility
            if hasattr(result, 'content'):
                try:
                    from i2c.utils.json_extraction import extract_json_with_fallback
                    
                    content = result.content
                    team_analysis = extract_json_with_fallback(content, fallback={})
                    
                    if team_analysis:
                        canvas.info(f"🧠 Context evolved using team strategy")
                        
                        # Extract team recommendations
                        strategy = team_analysis.get('context_evolution_strategy', {})
                        target_size = strategy.get('target_context_size', 9000)
                        
                        canvas.info(f"🧠 Target size: {target_size}")
                        canvas.info(f"🧠 Team consensus: {team_analysis.get('consensus_reached', False)}")
                        
                        # Apply team's recommendations to evolve context
                        current_size = len(str(new_context))
                        if current_size > target_size:
                            canvas.info(f"🧠 Applying size reduction: {current_size} → {target_size} chars")
                            evolved_context = self._apply_team_recommendations(new_context, team_analysis)
                            return evolved_context
                        else:
                            canvas.info(f"🧠 Context size acceptable: {current_size} chars")
                            return new_context
                    else:
                        canvas.warning("No valid JSON found in team response")
                        return new_context
                        
                except Exception as e:
                    canvas.warning(f"Failed to parse team response: {e}")
                    return new_context
            else:
                canvas.warning("Team response has no content")
                return new_context
            
        except Exception as e:
            canvas.warning(f"Context evolution team failed: {e}")
            return new_context
        
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
    if session_state is None:
        session_state = {
            "retrieved_context": None,
            "db_path": "./data/lancedb",
        }
    else:
        # 2️⃣ Add only the keys this team needs (if they are missing)
        session_state.setdefault("retrieved_context", None)
        session_state.setdefault("db_path", "./data/lancedb")
    
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
