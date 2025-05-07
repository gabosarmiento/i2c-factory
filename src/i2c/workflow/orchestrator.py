# In orchestrator.py
from pathlib import Path
import json
import traceback

from i2c.workflow.workflow_controller import WorkflowController
from i2c.cli.controller import canvas
from i2c.workflow.visual_helpers import show_progress, show_file_list

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
        
        if action_type == 'generate':
            # Define steps for visualization
            steps = [
                "Planning files",
                "Generating code",
                "Creating unit tests",
                "Quality checks",
                "Writing files"
            ]
            
            # Show initial progress
            canvas.info(f"\n🚀 Generating project from idea...")
            show_progress("Project Generation", steps, 0)
            
            # Run complete workflow
            success = controller.run_complete_workflow(
                action_type=action_type,
                action_detail=action_detail,
                project_path=current_project_path,
                structured_goal=current_structured_goal
            )
            
            # Show completion and generated files
            if success:
                show_progress("Project Generation", steps, len(steps))
                
                # Show generated files
                generated_files = []
                for file_path in current_project_path.rglob('*'):
                    if file_path.is_file():
                        generated_files.append(file_path)
                
                if generated_files:
                    show_file_list("Generated Files", generated_files, current_project_path)
                
                canvas.success(f"✅ Project generated successfully!")
                
            return success
            
            
        elif action_type == 'modify':
            if action_detail == 'r':
                # Refinement workflow
                canvas.info(f"\n🔄 Refining project...")
                steps = [
                    "Analyzing context",
                    "Planning refinements",
                    "Implementing changes",
                    "Testing & quality",
                    "Saving files"
                ]
            else:
                # Feature addition workflow
                canvas.info(f"\n🛠️ Adding feature: {action_detail[2:]}...")  # Skip 'f ' prefix
                steps = [
                    "Retrieving context",
                    "Planning modifications",
                    "Implementing code",
                    "Running tests",
                    "Finalizing changes"
                ]
                
            # Show initial progress
            show_progress("Modification", steps, 0)
            
            # Get list of files before modification
            files_before = set()
            for file_path in current_project_path.rglob('*'):
                if file_path.is_file():
                    files_before.add(str(file_path))
            
            # Execute with original workflow
            success = controller.run_complete_workflow(
                action_type=action_type,
                action_detail=action_detail,
                project_path=current_project_path,
                structured_goal=current_structured_goal
            )
            
            # Show completion and modified files
            if success:
                show_progress("Modification", steps, len(steps))
                
                # Determine which files were added or modified
                files_after = set()
                for file_path in current_project_path.rglob('*'):
                    if file_path.is_file():
                        files_after.add(str(file_path))
                
                # New files
                new_files = [Path(f) for f in files_after - files_before]
                if new_files:
                    show_file_list("New Files", new_files, current_project_path)
                
                # Modified files (harder to determine accurately without tracking)
                # This is just a placeholder
                canvas.success(f"✅ Modifications completed successfully!")
                
            return success
            
        elif action_type == 'feature_pipeline':
            # Story implementation through feature pipeline
            canvas.info(f"\n📝 Processing user story...")
            steps = [
                "Processing story",
                "Planning implementation",
                "Generating code",
                "Creating tests",
                "Checking quality"
            ]
            
            # Show initial progress
            show_progress("Story Implementation", steps, 0)
            
            # Get list of files before modification
            files_before = set()
            for file_path in current_project_path.rglob('*'):
                if file_path.is_file():
                    files_before.add(str(file_path))
            
            # Here we would integrate with your feature pipeline implementation
            from i2c.workflow.feature_integration import FeatureIntegration
            from i2c.agents.budget_manager import BudgetManagerAgent
            
            # Initialize integration with minimal dependencies
            budget_manager = BudgetManagerAgent(session_budget=None)
            feature_integration = FeatureIntegration(
                project_path=current_project_path,
                budget_manager=budget_manager
            )
            
            # Process the story
            result = feature_integration.handle_feature_request(action_detail)
            
            # Show completion based on result
            if result.get("success", False):
                show_progress("Story Implementation", steps, len(steps))
                
                # Determine which files were added or modified
                files_after = set()
                for file_path in current_project_path.rgloc('*'):
                    if file_path.is_file():
                        files_after.add(str(file_path))
                
                # New files
                new_files = [Path(f) for f in files_after - files_before]
                if new_files:
                    show_file_list("Files Created", new_files, current_project_path)
                
                canvas.success(f"✅ Story implemented successfully!")
                return True
            else:
                canvas.error(f"❌ Story implementation failed: {result.get('error', 'Unknown error')}")
                return False
            
        else:
            canvas.error(f"❌ Unknown action type: {action_type}")
            return False
            
    except Exception as e:
        canvas.error(f"❌ Error during workflow execution: {e}")
        return False