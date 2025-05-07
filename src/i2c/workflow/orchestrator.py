# i2c/workflow/orchestrator.py
# Updated to use WorkflowController for Agno integration

from pathlib import Path
import json
import traceback

from i2c.workflow.workflow_controller import WorkflowController
from i2c.cli.controller import canvas

# Review-storage helper
try:
    from utils.review_storage import save_review_to_file
except ImportError:
    def save_review_to_file(*args, **kwargs): return None

def route_and_execute(
    action_type: str,
    action_detail: any,
    current_project_path: Path,
    current_structured_goal: dict | None
) -> bool:
    """
    Routes action to appropriate workflows using WorkflowController.
    
    Args:
        action_type: "generate" or "modify"
        action_detail: The goal or modification details
        current_project_path: Path to the project directory
        current_structured_goal: Dict with objective and language
        
    Returns:
        bool: Success status
    """
    try:
        # Create workflow controller for this action
        controller = WorkflowController(
            session_id=f"{action_type}-{current_project_path.name}"
        )
        
        # Run complete workflow
        success = controller.run_complete_workflow(
            action_type=action_type,
            action_detail=action_detail,
            project_path=current_project_path,
            structured_goal=current_structured_goal
        )
        
        return success
        
    except Exception as e:
        canvas.error(f"Error during workflow execution: {e}")
        canvas.error(traceback.format_exc())
        return False