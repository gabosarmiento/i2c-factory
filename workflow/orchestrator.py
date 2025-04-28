# /workflow/orchestrator.py
# Routes actions and handles post-cycle SRE checks, review, guardrails, and version control using SRE Workflow.

from pathlib import Path
import json
import traceback

# Cycle execution functions
from .generation import execute_generation_cycle
from .modification import execute_modification_cycle

# --- <<< Import SRE Workflow >>> ---
from .sre_team_workflow import SRETeamWorkflow

# Import only agents needed AFTER SRE workflow (Quality, Version Control)
from agents.sre_team import version_controller # Keep VC here
from agents.quality_team import (
    reviewer_agent,
    guardrail_agent,
)
# Import Guardrail decision constants
from agents.quality_team.guardrail_agent import GUARDRAIL_BLOCK, GUARDRAIL_WARN, GUARDRAIL_CONTINUE

# CLI controller
from cli.controller import canvas

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
    Routes the user's action to the correct execution cycle, runs the SRE Workflow,
    then runs Review, Guardrail, and Version Control.
    """
    cycle_success = False
    language = current_structured_goal.get("language") if current_structured_goal else "python"
    final_code_map = None

    # --- 0. Execute main generation or modification cycle ---
    canvas.info(f"--- Starting {action_type.capitalize()} Cycle ---")
    try:
        if action_type == "generate":
            if isinstance(action_detail, dict):
                result = execute_generation_cycle(action_detail, current_project_path)
                cycle_success = result.get("success", False)
                language = result.get("language") or language
                final_code_map = result.get("code_map")
            else: raise ValueError("Missing structured goal for generation.")
        elif action_type == "modify":
            if isinstance(action_detail, str) and language:
                result = execute_modification_cycle(action_detail, current_project_path, language)
                cycle_success = result.get("success", False)
                language = result.get("language") or language
                final_code_map = result.get("code_map")
            else: raise ValueError("Invalid detail or missing language for modification.")
        else: raise ValueError(f"Unknown action type: {action_type}")
    except Exception as e:
         canvas.error(f"Error during '{action_type}' cycle: {e}")
         return False

    # --- 1. Check Cycle Success ---
    if not (cycle_success and isinstance(language, str) and final_code_map is not None):
        canvas.error("Main cycle failed or prerequisites missing for post-cycle checks.")
        return False

    # --- 2. Run SRE Workflow --- <<< MODIFIED BLOCK >>>
    canvas.info(f"--- Running SRE Workflow ---")
    sre_success = False
    analysis_summary = None # Initialize
    dep_issues = [] # Initialize
    syntax_test_ok = (True, "") # Initialize
    integration_issues = [] # Initialize

    try:
        sre_workflow = SRETeamWorkflow(session_id=f"sre-{current_project_path.name}") # Give it a session ID
        # Iterate through the workflow responses
        final_sre_response = None
        for response in sre_workflow.run(project_path=current_project_path, language=language):
             canvas.info(f"   [SRE_WF] {response.content}") # Log workflow progress
             # Collect results from extra_data if needed (optional)
             if response.extra_data:
                  if "dependency_issues" in response.extra_data:
                       dep_issues = response.extra_data["dependency_issues"]
                  if "integration_issues" in response.extra_data:
                       integration_issues = response.extra_data["integration_issues"]
                  # We get analysis_summary from the final response
             final_sre_response = response # Keep track of the last response

        # Check final status (assuming last response indicates completion)
        if final_sre_response and "completed successfully" in final_sre_response.content:
             sre_success = True
             analysis_summary = final_sre_response.extra_data.get("analysis_summary", {})
             # Extract other results if needed (e.g., syntax status)
             # Note: This relies on the workflow yielding results correctly.
             # A more robust way might be to store results in workflow state.
             # For now, we assume success if no exception was raised.
             # We still need syntax_ok for the guardrail - get it from sandbox directly?
             # Let's call sandbox again here just for the status - slightly redundant but simpler for now
             syntax_test_ok = sandbox_executor.execute(current_project_path, language)

        else:
             # Workflow might have finished but not reported success clearly
             canvas.warning("SRE Workflow finished, but final success message not detected.")
             # Attempt to get summary anyway if it exists
             analysis_summary = final_sre_response.extra_data.get("analysis_summary", {}) if final_sre_response else {}


    except Exception as e:
         canvas.error(f"SRE Workflow failed with exception: {e}")
         # Attempt to get any partial analysis summary if possible
         # analysis_summary = getattr(sre_workflow, 'last_analysis_summary', {}) # Requires modification to SREWorkflow
         sre_success = False # Mark as failed

    if not sre_success:
         canvas.error("SRE Workflow did not complete successfully. Aborting post-cycle actions.")
         return False
    # --- <<< END SRE Workflow Block >>> ---


    # --- 3. Post-SRE Workflow Steps (Review, Guardrail, Commit) ---
    canvas.info(f"--- Running Post-SRE Checks ---")
    review_feedback: str | None = None

    try:
        # Step 3.1: AI Code Review
        canvas.step("Performing AI Code Review...")
        if current_structured_goal:
            review_feedback = reviewer_agent.review_code(
                structured_goal=current_structured_goal,
                code_map=final_code_map,
                analysis_summary=analysis_summary # Use summary from SRE workflow
            )
            if review_feedback:
                canvas.info("[AI Review Feedback]:")
                for line in review_feedback.splitlines(): canvas.info(f"  {line}")
                save_review_to_file(current_project_path, review_feedback)
            else: canvas.warning("AI Review Agent failed or produced no feedback.")
        else: canvas.warning("Skipping AI Review: Project goal context missing.")

        # Step 3.2: Guardrail Evaluation
        canvas.step("Performing Guardrail Evaluation...")
        guardrail_decision, guardrail_reasons = guardrail_agent.evaluate_results(
            static_analysis_summary=analysis_summary, # Use summary from SRE workflow
            dependency_summary=dep_issues, # Use issues collected during SRE workflow (if yielded correctly)
            syntax_check_result=syntax_test_ok, # Use result from SRE workflow (or re-run)
            review_feedback=review_feedback
            # TODO: Pass integration_issues if yielded by SRE workflow
        )
        if guardrail_decision == GUARDRAIL_BLOCK:
            canvas.error("🚦 Guardrails blocked further action:")
            for reason in guardrail_reasons: canvas.error(f"  - {reason}")
            canvas.end_process(f"Action '{action_type}' aborted by guardrails.")
            return False
        if guardrail_decision == GUARDRAIL_WARN:
            canvas.warning("🚦 Guardrails issued warnings:")
            for reason in guardrail_reasons: canvas.warning(f"  - {reason}")

        # Step 3.3: Version Control Commit (Only if not blocked)
        canvas.step("Performing Version Control...")
        objective_summary = action_detail if isinstance(action_detail, str) else action_detail.get("objective", "Unknown Objective")
        # Construct detailed commit message (same as before)
        commit_lines = [f"Completed {action_type} cycle for: {objective_summary[:50]}"]
        if review_feedback: commit_lines.append("[AI Review included]")
        if guardrail_decision != GUARDRAIL_CONTINUE: commit_lines.append(f"[Guardrail Status: {guardrail_decision}]")
        # Add SRE results to commit message if available
        if integration_issues: commit_lines.append(f"[Integration Issues: {len(integration_issues)} found]")
        if dep_issues: commit_lines.append(f"[Dependency Issues: {len(dep_issues)} found]")
        if not syntax_test_ok[0]: commit_lines.append("[Syntax/Test Check Failed]")

        commit_msg = "\n\n".join(commit_lines)
        version_controller.initialize_and_commit(current_project_path, commit_msg)

        canvas.info(f"--- Post-Cycle Checks Completed ---")
        if guardrail_decision == GUARDRAIL_WARN: canvas.success(f"{action_type.capitalize()} cycle completed with warnings.")
        else: canvas.success(f"{action_type.capitalize()} cycle completed successfully.")
        return True # Overall action succeeded

    except Exception as e:
        canvas.error(f"Error during post-SRE steps (Review/Guardrail/Commit): {e}")
        canvas.error(traceback.format_exc())
        return False # Post-cycle failed critically

