# i2c/workflow/workflow_controller.py
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from i2c.workflow.session_manager import WorkflowSessionManager
from i2c.workflow.generation_workflow import GenerationWorkflow
from i2c.workflow.modification_workflow import ModificationWorkflow
from i2c.workflow.quality_workflow import QualityWorkflow
from i2c.workflow.self_healing_controller import SelfHealingController
from i2c.workflow.sre_team_workflow import SRETeamWorkflow
from agno.embedder.sentence_transformer import SentenceTransformerEmbedder
from i2c.db_utils import get_db_connection
from i2c.cli.controller import canvas
import builtins

# Get the global budget manager
if hasattr(builtins, 'global_budget_manager'):
    budget_manager = builtins.global_budget_manager
else:
    # Create a default one if not available
    from i2c.agents.budget_manager import BudgetManagerAgent
    budget_manager = BudgetManagerAgent(session_budget=None)
    
class WorkflowController:
    """
    Controls workflow execution with recovery capabilities.
    Manages the execution of different Agno workflows and maintains shared state.
    """
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"wfc-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.session_manager = WorkflowSessionManager(self.session_id)
        self.recovery_log = []
        self.last_error = None  
    
    def get_last_error(self) -> Optional[str]:
        """Get the last error message from workflow execution"""
        return self.last_error

    def _set_error(self, error_message: str):
        """Set the last error message"""
        self.last_error = error_message
        canvas.error(f"[WorkflowController] {error_message}")
        
    def run_workflow_with_recovery(self, workflow, max_attempts: int = 1, **kwargs) -> bool:
        """
        Run a workflow with basic recovery attempts.
        
        Args:
            workflow: An Agno Workflow instance
            max_attempts: Maximum number of recovery attempts
            **kwargs: Arguments to pass to the workflow's run method
            
        Returns:
            bool: Success status
        """
        workflow_name = workflow.__class__.__name__
        canvas.info(f"🚀 [WorkflowController] Running {workflow_name}...")
        
        # Store initial parameters in session state
        for key, value in kwargs.items():
            if key != 'db' and key != 'embed_model':  # Skip DB/embedder objects
                self.session_manager.update_state(**{key: value})
        
        # First attempt
        success = False
        final_response = None
        error_message = None
        
        try:
            # Run workflow and collect responses
            for response in workflow.run(**kwargs):
                # Update session with any extra_data from response
                if hasattr(response, 'extra_data') and response.extra_data:
                    self.session_manager.update_state(**response.extra_data)
                final_response = response
            
            # Check if final response indicates success
            if final_response and hasattr(final_response, 'extra_data'):
                success = final_response.extra_data.get('success', False)
            else:
                success = False
                
        except Exception as e:
            error_message = str(e)
            canvas.error(f"❌ [WorkflowController] {workflow_name} failed: {e}")
            self.recovery_log.append({
                "workflow": workflow_name,
                "attempt": 0,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
        
        # Recovery attempts if needed
        attempt = 1
        while not success and attempt <= max_attempts and error_message:
            canvas.warning(f"🔄 [WorkflowController] Recovery attempt {attempt} for {workflow_name}...")
            
            try:
                # Create a fresh workflow instance for recovery
                recovery_workflow = workflow.__class__(
                    session_id=f"{self.session_id}-recovery{attempt}"
                )
                
                # Run the recovery workflow
                for response in recovery_workflow.run(**kwargs):
                    if hasattr(response, 'extra_data') and response.extra_data:
                        self.session_manager.update_state(**response.extra_data)
                    final_response = response
                
                # Check recovery success
                if final_response and hasattr(final_response, 'extra_data'):
                    success = final_response.extra_data.get('success', False)
                
                # Log recovery attempt
                self.recovery_log.append({
                    "workflow": workflow_name,
                    "attempt": attempt,
                    "success": success,
                    "timestamp": datetime.now().isoformat()
                })
                
                if success:
                    canvas.success(f"✅ [WorkflowController] Recovery attempt {attempt} succeeded!")
                    break
                    
            except Exception as e:
                error_message = str(e)
                canvas.error(f"❌ [WorkflowController] Recovery attempt {attempt} failed: {e}")
                self.recovery_log.append({
                    "workflow": workflow_name,
                    "attempt": attempt,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
            
            attempt += 1
            
        # Final status
        if success:
            canvas.success(f"✅ [WorkflowController] {workflow_name} completed successfully!")
        else:
            canvas.error(f"❌ [WorkflowController] {workflow_name} failed after {attempt} attempt(s).")
            
        return success
            
    def run_generation_cycle(self, structured_goal: dict, project_path: Path, session_state: dict = None) -> bool:
        """
        Run the generation cycle workflow with recovery.
        
        Args:
            structured_goal: Dict with objective and language
            project_path: Path to the project directory
            
        Returns:
            bool: Success status
        """
        # Update session state
        self.session_manager.update_state(
            action_type="generate",
            structured_goal=structured_goal,
            project_path=str(project_path),
            language=structured_goal.get("language")
        )
        
        # Create and run workflow
        workflow = GenerationWorkflow(session_id=f"{self.session_id}-gen")
        workflow.session_state.update({
            "action_type": "generate",
            "structured_goal": structured_goal,
            "project_path": str(project_path),
            "language": structured_goal.get("language")
        })

        # Merge in the passed session_state (contains knowledge_base)
        if session_state:
            workflow.session_state.update(session_state)
            canvas.info(f"🔍 DEBUG: Merged session_state into GenerationWorkflow: {'knowledge_base' in session_state}")
            
            # Verify knowledge_base is now in workflow session_state
            if 'knowledge_base' in workflow.session_state:
                canvas.success("✅ DEBUG: Knowledge base successfully passed to GenerationWorkflow")
            else:
                canvas.error("❌ DEBUG: Knowledge base missing after merge")
        
        success = self.run_workflow_with_recovery(
            workflow, 
            max_attempts=1,
            structured_goal=structured_goal,
            project_path=project_path
        )
        
        return success
    
    def run_modification_cycle(self, user_request: str, project_path: Path, language: str) -> bool:
        """
        Run the modification cycle workflow with recovery.
        
        Args:
            user_request: The modification request
            project_path: Path to the project directory
            language: The programming language
            
        Returns:
            bool: Success status
        """
        # Update session state
        self.session_manager.update_state(
            action_type="modify",
            user_request=user_request,
            project_path=str(project_path),
            language=language
        )
        
        # Initialize RAG resources
        db = get_db_connection()
        embed_model = SentenceTransformerEmbedder()
        
        # Create and run workflow
        workflow = ModificationWorkflow(session_id=f"{self.session_id}-mod")
        success = self.run_workflow_with_recovery(
            workflow,
            max_attempts=1,
            user_request=user_request,
            project_path=project_path,
            language=language,
            db=db,
            embed_model=embed_model
        )
        
        return success
    
    def run_sre_workflow(self, project_path: Path, language: str) -> bool:
        """
        Run the SRE workflow with the existing SelfHealingController.
        
        Args:
            project_path: Path to the project directory
            language: The programming language
            
        Returns:
            bool: Success status
        """
        # Update session state
        self.session_manager.update_state(
            project_path=str(project_path),
            language=language
        )
        
        # Use the existing SelfHealingController
        canvas.info("🔍 [WorkflowController] Running SRE Workflow via SelfHealingController...")
        
        try:
            import asyncio
            # Create controller and run workflow
            healing_controller = SelfHealingController(
                session_id=f"{self.session_id}-sre"
            )
            success, results = asyncio.run(healing_controller.run_with_recovery(
                project_path=project_path,
                language=language
            ))
            
            # Extract analysis summary for later use
            if "analysis_summary" in results:
                self.session_manager.update_state(
                    analysis_summary=results["analysis_summary"]
                )
            
            if success:
                canvas.success("✅ [WorkflowController] SRE Workflow completed successfully!")
            else:
                canvas.error("❌ [WorkflowController] SRE Workflow failed.")
                
            return success
            
        except Exception as e:
            canvas.error(f"❌ [WorkflowController] Error running SRE Workflow: {e}")
            return False
    
    def run_quality_workflow(self, project_path: Path, structured_goal: dict) -> bool:
        """
        Run the quality workflow with recovery.
        
        Args:
            project_path: Path to the project directory
            structured_goal: Dict with objective and language
            
        Returns:
            bool: Success status
        """
        # Get code_map and analysis_summary from session state
        code_map = self.session_manager.get_value("code_map", {})
        analysis_summary = self.session_manager.get_value("analysis_summary", {})
        
        if not code_map:
            canvas.warning("⚠️ [WorkflowController] No code map available for quality workflow.")
            return False
        
        # Create and run workflow
        workflow = QualityWorkflow(session_id=f"{self.session_id}-quality")
        success = self.run_workflow_with_recovery(
            workflow,
            max_attempts=1,
            project_path=project_path,
            structured_goal=structured_goal,
            code_map=code_map,
            analysis_summary=analysis_summary
        )
        
        return success
    
    def run_complete_workflow(self, action_type: str, action_detail: Any, 
                            project_path: Path, structured_goal: dict, 
                            session_state: dict = None) -> bool:
        """
        Run the complete workflow sequence (main cycle, SRE, quality).
        
        Args:
            action_type: "generate" or "modify"
            action_detail: Structured goal or user request
            project_path: Path to the project directory
            structured_goal: Dict with objective and language
            
        Returns:
            bool: Overall success status
        """
        # Update session state with initial values
        self.session_manager.update_state(
            action_type=action_type,
            project_path=str(project_path),
            structured_goal=structured_goal,
            language=structured_goal.get("language") if structured_goal else "python"
        )
        
        # 1. Run main cycle (generation or modification)
        if action_type == "generate":
            canvas.info(f"🏭 [WorkflowController] Starting Generation Cycle...")
            # Pass session_state to generation cycle
            if session_state:
                canvas.info(f"🔍 DEBUG: Passing session_state to generation cycle: {'knowledge_base' in session_state}")
            main_cycle_success = self.run_generation_cycle(
                structured_goal=action_detail,
                project_path=project_path,
                session_state=session_state  # ADD THIS
            )
        elif action_type == "modify":
            canvas.info(f"🏭 [WorkflowController] Starting Modification Cycle...")
            main_cycle_success = self.run_modification_cycle(
                user_request=action_detail,
                project_path=project_path,
                language=structured_goal.get("language", "python")
            )
        else:
            canvas.error(f"❌ [WorkflowController] Unknown action type: {action_type}")
            return False
        
        # Check main cycle success
        if not main_cycle_success:
            canvas.error(f"❌ [WorkflowController] Main cycle failed.")
            return False
        
        # 2. Run SRE workflow
        sre_success = self.run_sre_workflow(
            project_path=project_path,
            language=structured_goal.get("language", "python")
        )
        
        # Check SRE success
        if not sre_success:
            canvas.error(f"❌ [WorkflowController] SRE workflow failed.")
            return False
        
        # 3. Run quality workflow
        quality_success = self.run_quality_workflow(
            project_path=project_path,
            structured_goal=structured_goal
        )
        
        # Final status
        # Resilient success logic - don't fail entire workflow for quality/SRE issues
        overall_success = main_cycle_success  # Main generation must succeed

        # Capture specific error messages
        error_details = []
        
        if not main_cycle_success:
            error_msg = "Main generation cycle failed"
            error_details.append(error_msg)
            self._set_error(error_msg)
        
        # Log quality and SRE results without failing entire workflow
        if not quality_success:
            error_msg = "Quality validation failed"  
            error_details.append(error_msg)
            canvas.warning(f"⚠️ [WorkflowController] {error_msg} but continuing...")
            
        if not sre_success:
            error_msg = "SRE validation failed"
            error_details.append(error_msg)
            canvas.warning(f"⚠️ [WorkflowController] {error_msg} but continuing...")

        # Set combined error message if any failures
        if error_details:
            self._set_error("; ".join(error_details))
            
        # Report detailed status
        if overall_success:
            if quality_success and sre_success:
                canvas.success(f"🎉 [WorkflowController] Complete workflow succeeded with all validations!")
            else:
                canvas.success(f"✅ [WorkflowController] Generation succeeded (quality: {'✅' if quality_success else '⚠️'}, SRE: {'✅' if sre_success else '⚠️'})")
        else:
            canvas.error(f"❌ [WorkflowController] Main generation failed.")

        return overall_success