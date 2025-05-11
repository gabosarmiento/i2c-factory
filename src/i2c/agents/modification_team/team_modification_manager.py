# team_modification_manager.py
from pathlib import Path
from typing import Dict, Optional, Union, List, Any
import json
import logging

from agno.team import Team
from agno.agent import Agent
from builtins import llm_highest, llm_middle

# Import your existing code 
from i2c.agents.modification_team.code_modification_manager import (
    ModificationRequest, 
    AnalyzerAdapter, 
    ModifierAdapter, 
    DiffingAdapter,
    ValidatorAdapter,
    DocumentationAdapter,
    AnalyzerAgent,
    ModifierAgent,
    ValidatorAgent,
    DiffingAgent,
    DocsAgent
)

from i2c.agents.modification_team.patch import Patch

# Import CLI for logging
from i2c.cli.controller import canvas

# Set up logging
logger = logging.getLogger("team_modification_manager")

class ModificationTeamManager:
    """
    Manages a team of agents for code modification with integrated RAG support.
    """
    
    def __init__(self, project_path: Path, db=None, embed_model=None):
        """
        Initialize the team manager.
        
        Args:
            project_path: Path to the project
            db: Database connection (optional)
            embed_model: Embedding model (optional)
        """
        self.project_path = project_path
        self.db = db
        self.embed_model = embed_model
        
        # Load dependencies if not provided
        if self.db is None:
            from i2c.db_utils import get_db_connection
            self.db = get_db_connection()
            
        if self.embed_model is None:
            from i2c.workflow.modification.rag_config import get_embed_model
            self.embed_model = get_embed_model()
        
        # Create the team
        self.team = self._build_modification_team()
        
    def _build_modification_team(self) -> Team:
        """
        Build the agent team with integrated RAG capabilities.
        """
        # Create individual agents
        analyzer = AnalyzerAgent()
        modifier = ModifierAgent()
        validator = ValidatorAgent()
        diffing = DiffingAgent()
        docs = DocsAgent()
        
        # Create coordinator agent
        coordinator = Agent(
            name="ModificationCoordinator",
            model=llm_highest,
            description="Coordinates the code modification process with RAG context",
            instructions=[
                "You are the modification coordinator responsible for orchestrating the code modification process.",
                "Your task is to guide the team through the following steps:",
                "1. Analyze the code with the Analyzer to understand what needs to change",
                "2. Retrieve relevant context from the vector database",
                "3. Generate the modified code with the Modifier",
                "4. Validate the changes with the Validator",
                "5. Create a unified diff with the Diffing agent",
                "6. Document the changes with the Documentation agent",
                "You should collect the output from each step and provide it to the next agent.",
                "Your final output must be a valid JSON with the structure:",
                "{ \"file_path\": \"...\", \"unified_diff\": \"...\", \"validation\": {...} }"
            ]
        )
        
        # Create semantic graph tool for code analysis
        try:
            from i2c.tools.neurosymbolic.semantic_tool import SemanticGraphTool
            semantic_tool = SemanticGraphTool(project_path=self.project_path)
        except ImportError:
            semantic_tool = None
            logger.warning("SemanticGraphTool not available - some analyses will be limited")
        
        # Create the team
        team = Team(
            name="Code Modification Team",
            mode="coordinate",  # Coordinator manages workflow
            model=llm_highest,  # Team default model
            members=[
                coordinator,  # Team leader
                analyzer,
                modifier,
                validator,
                diffing,
                docs
            ],
            instructions=[
                "This team is responsible for modifying code based on user requests.",
                "The coordinator will guide the process, ensuring each agent has the context it needs.",
                "The team must analyze the code, retrieve relevant context, generate modifications,",
                "validate the changes, create a diff, and document the changes."
            ],
            session_state={
                "project_path": str(self.project_path),
                "db": self.db,
                "embed_model": self.embed_model,
                "semantic_tool": semantic_tool
            },
            enable_agentic_context=True,
            show_members_responses=True,
        )
        
        return team
    
    def apply_modification(
        self, 
        modification_step: Dict, 
        project_path: Path,
        retrieved_context: Optional[str] = None
    ) -> Union[Patch, Dict]:
        """
        Apply a modification using the team-based approach.
        
        Args:
            modification_step: Dict with modification details
            project_path: Project path
            retrieved_context: Optional RAG context
            
        Returns:
            Patch object or error dict
        """
        canvas.info(f"Applying modification using team approach: {modification_step.get('what', 'Unknown modification')}")
        
        # Create input for the team
        team_input = {
            "modification_step": modification_step,
            "project_path": str(project_path),
            "retrieved_context": retrieved_context or ""
        }
        
        try:
            # Execute the team
            response = self.team.run(json.dumps(team_input))
            
            # Process the response
            if response and hasattr(response, 'content'):
                content = response.content
                
                # Try to parse as JSON
                try:
                    result = json.loads(content)
                    
                    # Extract the unified diff
                    if "unified_diff" in result:
                        # Create and return the patch
                        return Patch(
                            file_path=result.get("file_path", "unknown.py"),
                            unified_diff=result.get("unified_diff", "")
                        )
                    else:
                        return {"error": f"Missing unified_diff in response: {content[:100]}..."}
                        
                except json.JSONDecodeError:
                    # Not JSON, check if it looks like a diff
                    if content.startswith("--- ") or content.startswith("diff --git"):
                        # It's a raw diff, extract file path if possible
                        file_path = modification_step.get("file", "unknown.py")
                        return Patch(file_path=file_path, unified_diff=content)
                    else:
                        return {"error": f"Could not parse response as JSON or diff: {content[:100]}..."}
            else:
                return {"error": "Team returned empty response"}
                
        except Exception as e:
            canvas.error(f"Error in team execution: {e}")
            return {"error": f"Team execution error: {e}"}