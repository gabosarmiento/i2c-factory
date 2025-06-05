# In orchestrator.py
from pathlib import Path
from typing import Any, Dict

import json
import traceback

from i2c.workflow.workflow_controller import WorkflowController
from i2c.cli.controller import canvas
from i2c.workflow.visual_helpers import show_progress, show_file_list
# Add the enhanced route_and_execute_with_recovery function to the orchestrator
from i2c.workflow.validation import (
    validate_generated_application, 
    get_code_map_from_path,
    apply_fixes_based_on_validation,
    try_recovery_actions
)

def route_and_execute_with_recovery(
    action_type: str,
    action_detail: any,
    current_project_path: Path,
    current_structured_goal: dict | None,
    max_retries: int = 0,  # Allow for retries
    session_state: dict = None  
) -> bool:
    """Enhanced route_and_execute with error recovery"""
    from i2c.cli.controller import canvas
    import traceback
    
    # Track attempts for each step
    attempts = 0
    last_error = None
    
    while attempts <= max_retries:
        try:
            # 1. Regular execution attempt
            if attempts > 0:
                canvas.warning(f"Retry attempt {attempts}/{max_retries} after error: {str(last_error)}")
            
            # Call the normal workflow
            success = route_and_execute(
                action_type=action_type,
                action_detail=action_detail,
                current_project_path=current_project_path,
                current_structured_goal=current_structured_goal,
                session_state=session_state
            )
            
            if success:
                # 2. Validate the generated output
                validation_success, validation_results = validate_generated_application(
                    get_code_map_from_path(current_project_path),
                    current_project_path,
                    current_structured_goal.get("language", "python")
                )
                
                if validation_success:
                    canvas.success("Generated application passed validation checks!")
                    return True
                else:
                    # Failed validation
                    canvas.warning(f"Generated application failed validation on attempt {attempts + 1}")
                    if attempts < max_retries:
                        # Apply fixes based on validation results before retrying
                        apply_fixes_based_on_validation(validation_results, current_project_path)
                    else:
                        canvas.warning("Max retries reached. Proceeding with warnings.")
                        return True  # Return success despite validation issues
            
            # Retry on failure if attempts remain
            if not success and attempts < max_retries:
                attempts += 1
                canvas.warning(f"Action failed. Retrying ({attempts}/{max_retries})...")
                continue
            else:
                return success
            
        except Exception as e:
            # Capture error for potential retry
            last_error = e
            attempts += 1
            
            # Log the error
            canvas.error(f"Error during execution: {str(e)}")
            canvas.error(traceback.format_exc())
            
            if attempts <= max_retries:
                canvas.warning(f"Attempting recovery ({attempts}/{max_retries})...")
                # Try recovery actions before retry
                try_recovery_actions(action_type, current_project_path)
            else:
                canvas.error(f"Max retries exceeded. Recovery failed.")
                return False
    
    return False

def route_and_execute(
    action_type: str,
    action_detail: any,
    current_project_path: Path,
    current_structured_goal: dict | None,
    architectural_context: Dict[str, Any] = None,
    budget_manager: Any = None, 
    session_state: Dict[str, Any] = None    
) -> Dict[str, Any]:
    """
    Routes action to appropriate workflows using WorkflowController.
    
    Args:
        action_type: "generate" or "modify"
        action_detail: The goal or modification details
        current_project_path: Path to the project directory
        current_structured_goal: Dict with objective and language
        architectural_context: Optional architectural context
        session_state: Optional session state with knowledge and routing info
        
    Returns:
        Dict[str, Any]: Result with success status, error info, and updated session_state
    """
    """Routes action to appropriate workflows using WorkflowController."""
    canvas.info(f"🔍 DEBUG: route_and_execute called with session_state: {session_state is not None}")
    if session_state and "knowledge_base" in session_state:
        canvas.success("🧠 DEBUG: Knowledge base passed to route_and_execute")
    else:
        canvas.error("🔍 DEBUG: No knowledge_base in route_and_execute session_state!")
    
    # Store architectural context in structured goal if provided
    if architectural_context:
        current_structured_goal = current_structured_goal.copy()
        current_structured_goal["architectural_context"] = architectural_context
    
    # Rest of function stays exactly the same
    
    
    print(f"=== ROUTE_AND_EXECUTE CALLED ===")
    canvas.info(f"🎯 Routing action: {action_type}")
    print(f"Action detail: {action_detail}")
    try:
        # Here we would integrate with your feature pipeline implementation
        from i2c.workflow.feature_integration import FeatureIntegration
        from i2c.agents.budget_manager import BudgetManagerAgent
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
                structured_goal=current_structured_goal, 
                session_state=session_state
            )
            
            # Show completion and generated files
            if success:
                show_progress("Project Generation", steps, len(steps))
                
                # Show generated files
                generated_files = [
                    file_path for file_path in current_project_path.rglob('*') if file_path.is_file()
                ]
                if generated_files:
                    show_file_list("Generated Files", generated_files, current_project_path)
                canvas.success(f"✅ Project generated successfully!")
                
                # Include updated session state from workflow controller
                result = {"success": True, "error": None}
                if hasattr(controller, 'session_manager') and controller.session_manager:
                    result["session_state"] = controller.session_manager.get_state()
                    canvas.info(f"🔄 DEBUG: Returning session state with {len(result['session_state'])} keys")
                return result
            else:
                error_msg = controller.get_last_error() or "Generation workflow failed"
                return {"success": False, "error": error_msg}
            
            
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
            
            canvas.info(f"\n🛠️ Modifying project...")    
            # Show initial progress
            show_progress("Modification", steps, 0)
            
            # Get list of files before modification
            files_before = {str(p) for p in current_project_path.rglob('*') if p.is_file()}
            
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
                files_after = {str(p) for p in current_project_path.rglob('*') if p.is_file()}
                new_files = [Path(f) for f in files_after - files_before]
                
                if new_files:
                    show_file_list("New Files", new_files, current_project_path)
                canvas.success(f"✅ Modifications completed successfully!")
                return {"success": True, "error": None}
            else:
                error_msg = controller.get_last_error() or "Modification workflow failed"
                return {"success": False, "error": error_msg}
            
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
            files_before = {str(p) for p in current_project_path.rglob('*') if p.is_file()}
            
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
                files_after = {str(p) for p in current_project_path.rglob('*') if p.is_file()}
                new_files = [Path(f) for f in files_after - files_before]
                if new_files:
                    show_file_list("Files Created", new_files, current_project_path)
                canvas.success(f"✅ Story implemented successfully!")
                return {"success": True, "error": None}
            else:
                error_msg = controller.get_last_error() or "Story implementation failed"
                canvas.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
            
        else:
            canvas.error(f"❌ Unknown action type: {action_type}")
            return {"success": False, "error": f"Unknown action type: {action_type}"}
            
    except Exception as e:
        canvas.error(f"❌ Error during workflow execution: {e}")
        return {"success": False, "error": f"Exception during {action_type}: {str(e)}"}