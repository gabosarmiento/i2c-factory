# /workflow/self_healing_controller.py
# Manages SRE workflow execution with basic self-healing retry logic.

from pathlib import Path
from typing import Tuple, Dict, Any
from datetime import datetime, timezone

# Import the SRE Workflow class
try:
    from .sre_team_workflow import SRETeamWorkflow
except ImportError: # Fallback if run directly or structure differs
    try:
        from workflow.sre_team_workflow import SRETeamWorkflow
    except ImportError:
        print("❌ Critical Error: Cannot import SRETeamWorkflow in self_healing_controller.py")
        # Define dummy class to avoid crashing later if import fails
        class SRETeamWorkflow:
            def __init__(self, *args, **kwargs): pass
            def run(self, *args, **kwargs):
                 print("ERROR: Dummy SRETeamWorkflow run called!")
                 yield type("obj", (object,), {"content": "Dummy SRE WF Response", "extra_data": {}})() # Dummy response

# Import CLI controller
try:
    from cli.controller import canvas
except ImportError:
    class FallbackCanvas: # Basic fallback logger
        def warning(self, msg): print(f"[WARN_HEAL] {msg}")
        def error(self, msg): print(f"[ERROR_HEAL] {msg}")
        def info(self, msg): print(f"[INFO_HEAL] {msg}")
        def success(self, msg): print(f"[SUCCESS_HEAL] {msg}")
    canvas = FallbackCanvas()

class SelfHealingController:
    """
    Executes the SRE Workflow with basic self-healing:
    - Detects critical failure patterns (syntax/test failure via exception).
    - Performs 1 basic retry if the initial run fails.
    - Records recovery attempts.
    - Returns success status and key results (like analysis summary).
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.recovery_attempted = False
        self.recovery_log = [] # Stores info about recovery attempts
        self.last_analysis_summary = {} # Store summary from successful run

    def _run_sre_workflow_instance(self, workflow_instance: SRETeamWorkflow, project_path: Path, language: str) -> bool:
        """ Helper to run a workflow instance and iterate through responses. """
        final_response = None
        for response in workflow_instance.run(project_path=project_path, language=language):
            # Log progress using canvas (already done within SRE workflow phases)
            # canvas.info(f"   [SRE_WF_RUN] {response.content}")
            final_response = response # Keep track of the last response

        # Store analysis summary from the workflow's state
        self.last_analysis_summary = workflow_instance.session_state.get("last_analysis_summary", {})

        # Check if the last response indicates success
        if final_response and "completed successfully" in final_response.content:
            return True
        else:
            # If no final success message, assume failure based on exception handling below
            # Or check workflow state if it sets a specific success flag
            return False


    def run_with_recovery(self, project_path: Path, language: str = "python") -> Tuple[bool, Dict[str, Any]]:
        """
        Runs the SRE workflow, attempts recovery if critical failure detected.

        Args:
            project_path: Path to the project directory.
            language: Primary language of the project.

        Returns:
            A tuple: (success: bool, results: Dict[str, Any])
                     where results contains keys like 'analysis_summary'.
        """
        # Fresh instance of SRE workflow for the first attempt
        # Use unique session IDs for each run attempt if needed for Agno state isolation
        initial_workflow = SRETeamWorkflow(session_id=f"{self.session_id}-initial")
        sre_success = False

        try:
            canvas.info("🚀 [HealingController] Running SRE Workflow (Initial Attempt)...")
            sre_success = self._run_sre_workflow_instance(initial_workflow, project_path, language)
            if sre_success:
                canvas.success("✅ [HealingController] Initial SRE Workflow completed successfully.")
                # Return success and the analysis summary collected by the helper
                return True, {"analysis_summary": self.last_analysis_summary}

        except Exception as e:
            canvas.warning(f"⚠️ [HealingController] Initial SRE Workflow failed with error: {e}")
            # Log initial failure before attempting recovery
            self.recovery_log.append({
                "attempt": 0, # Initial attempt
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "strategy": "initial run failed",
            })

            if not self.recovery_attempted:
                canvas.warning("🛠️ [HealingController] Attempting Recovery (Basic Retry)...")
                self.recovery_attempted = True
                recovery_workflow = SRETeamWorkflow(session_id=f"{self.session_id}-recovery1")

                try:
                    sre_success = self._run_sre_workflow_instance(recovery_workflow, project_path, language)
                    if sre_success:
                        canvas.success("✅ [HealingController] Recovery attempt succeeded!")
                        self.recovery_log.append({
                            "attempt": 1, "timestamp": datetime.now(timezone.utc).isoformat(),
                            "error": None, "strategy": "basic retry succeeded",
                        })
                        # Return success and the summary from the recovery run
                        return True, {"analysis_summary": self.last_analysis_summary}
                    else:
                         # Workflow ran but didn't report success in final message
                         canvas.error("❌ [HealingController] Recovery attempt ran but did not report success.")
                         self.recovery_log.append({
                             "attempt": 1, "timestamp": datetime.now(timezone.utc).isoformat(),
                             "error": "Recovery workflow did not complete successfully.",
                             "strategy": "basic retry failed (no success message)",
                         })

                except Exception as recovery_error:
                    canvas.error(f"❌ [HealingController] Recovery attempt failed with error: {recovery_error}")
                    self.recovery_log.append({
                        "attempt": 1, "timestamp": datetime.now(timezone.utc).isoformat(),
                        "error": str(recovery_error), "strategy": "basic retry failed (exception)",
                    })
            else:
                 # Should not happen if recovery_attempted is managed correctly
                 canvas.error("❌ [HealingController] Recovery already attempted. Cannot retry again.")


        # If initial run failed and recovery wasn't attempted or also failed
        canvas.error("💥 [HealingController] SRE Workflow failed permanently, even after recovery attempt.")
        # Return failure and the last known analysis summary (which might be empty or from a failed run)
        return False, {"analysis_summary": self.last_analysis_summary}

