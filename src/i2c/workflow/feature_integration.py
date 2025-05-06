# workflow/feature_integration.py
"""Integration module for Feature Pipeline with existing i2c Factory"""

from pathlib import Path
from typing import Dict, Optional

from i2c.workflow.feature_pipeline import FeaturePipeline
from i2c.story_manager import StoryManager
from i2c.agents.knowledge.knowledge_manager import ExternalKnowledgeManager
from i2c.agents.budget_manager import BudgetManagerAgent
from i2c.cli.controller import canvas
from i2c.cli.rich_output import rich_output
from i2c.db_utils import get_db_connection
import os

# Add these missing imports
from i2c.models.user_story import UserStory, StoryStatus, StoryPriority, AcceptanceCriteria


class FeatureIntegration:
    """Integrates Feature Pipeline with existing i2c Factory workflow"""
    
    def __init__(self, project_path: Path, budget_manager: BudgetManagerAgent):
        self.project_path = project_path
        self.budget_manager = budget_manager
        
        # Initialize embedding model
        try:
            from sentence_transformers import SentenceTransformer
            self.embed_model = SentenceTransformer(os.getenv('EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2'))
        except ImportError:
            canvas.error("sentence-transformers not installed")
            self.embed_model = None
        
        # Initialize components
        self.db_connection = get_db_connection()
        self.knowledge_manager = ExternalKnowledgeManager(embed_model=self.embed_model)
        self.story_manager = StoryManager(
            storage_path=project_path / "user_stories",
            knowledge_manager=self.knowledge_manager
        )
        
        # Initialize pipeline
        self.pipeline = FeaturePipeline(
            project_path=project_path,
            story_manager=self.story_manager,
            budget_manager=budget_manager,
            embed_model=self.embed_model,
            db_connection=self.db_connection
        )
    
    def handle_feature_request(self, raw_input: str) -> Dict:
        """Handle a feature request from raw user input"""
        canvas.start_process("Processing Feature Request")
        
        try:
            # Parse input to create user story
            story = self._parse_feature_request(raw_input)
            if not story:
                return {"success": False, "error": "Failed to parse feature request"}
            
            # Create and store story
            story_id = self.story_manager.create_story(story)
            
            # Update to READY status
            self.story_manager.update_story_status(story_id, StoryStatus.READY)
            
            # Process through pipeline
            success, result = self.pipeline.process_story(story_id)
            
            canvas.end_process(f"Feature request {'completed' if success else 'failed'}")
            return {
                "success": success,
                "story_id": story_id,
                "result": result
            }
            
        except Exception as e:
            canvas.error(f"Error handling feature request: {e}")
            canvas.end_process("Feature request failed")
            return {"success": False, "error": str(e)}
    
    def _parse_feature_request(self, raw_input: str) -> Optional[UserStory]:
        """Parse raw input into a UserStory object"""
        # In production, this would use an LLM to parse natural language
        # For now, we'll use a simple format: "As a <role>, I want <feature>, so that <benefit>"
        
        parts = raw_input.split(",")
        if len(parts) < 3:
            canvas.warning("Invalid feature request format")
            return None
        
        as_a = parts[0].strip().replace("As a ", "").replace("as a ", "")
        i_want = parts[1].strip().replace("I want ", "").replace("i want ", "")
        so_that = parts[2].strip().replace("so that ", "").replace("So that ", "")
        
        # Create basic story
        story = UserStory(
            title=f"Feature: {i_want[:50]}",
            description=raw_input,
            as_a=as_a,
            i_want=i_want,
            so_that=so_that,
            acceptance_criteria=[
                AcceptanceCriteria(description=f"The feature '{i_want}' is implemented")
            ],
            priority=StoryPriority.MEDIUM
        )
        
        return story
    
    def integrate_with_session(self, session):
        """Integrate with existing session workflow"""
        # Add feature pipeline as a new command option
        original_get_action = session.handle_get_user_action
        
        def enhanced_get_action(current_project_path):
            """Enhanced action handler with feature pipeline option"""
            if current_project_path:
                project_status = f"Project: '{current_project_path.name}'"
                options = "'f <feature_idea>', 'r' (refine), 'story <user_story>' (feature pipeline), 'p <path>' (switch project), 'q' (quit)"
                action_prompt = f"{project_status} | Options: {options}:"
            else:
                return original_get_action(current_project_path)
            
            user_input = canvas.get_user_input(action_prompt).strip()
            
            # Handle new story command
            if user_input.lower().startswith('story '):
                story_text = user_input[len('story '):].strip()
                return 'feature_pipeline', story_text
            
            # Fall back to original handler
            return original_get_action(current_project_path)
        
        # Patch the session handler
        session.handle_get_user_action = enhanced_get_action
        
        # Add feature pipeline handling to route_and_execute
        original_route = session.route_and_execute
        
        def enhanced_route(action_type, action_detail, current_project_path, current_structured_goal):
            """Enhanced router with feature pipeline support"""
            if action_type == 'feature_pipeline':
                result = self.handle_feature_request(action_detail)
                return result["success"]
            
            # Fall back to original router
            return original_route(action_type, action_detail, current_project_path, current_structured_goal)
        
        # Patch the router
        session.route_and_execute = enhanced_route
        
        canvas.success("Feature Pipeline integrated with session workflow")


# Usage example in main workflow
def enhance_workflow_with_features():
    """Enhance the main workflow with feature pipeline capabilities"""
    from i2c.workflow.session import run_session
    
    # Create wrapper function
    def enhanced_run_session():
        # Get budget manager from session
        budget_manager = BudgetManagerAgent(session_budget=None)
        
        # Get project path from environment or default
        project_path = Path(os.getenv("DEFAULT_PROJECT_ROOT", "./output"))
        
        # Initialize feature integration
        feature_integration = FeatureIntegration(project_path, budget_manager)
        
        # Patch session with feature pipeline
        import i2c.workflow.session as session_module
        feature_integration.integrate_with_session(session_module)
        
        # Run enhanced session
        run_session()
    
    return enhanced_run_session