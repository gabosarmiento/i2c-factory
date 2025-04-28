# /workflow/orchestrator.py
# Routes actions and handles post-cycle SRE checks, review, guardrails, and version control using SRE Workflow.

from pathlib import Path
import json
import traceback

# Cycle execution functions
from .generation import execute_generation_cycle
from .modification import execute_modification_cycle

# --- <<< Import SRE Workflow from correct filename >>> ---
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

# Import sandbox executor to re-run for status if needed (simplification)
# Alternatively, SRE Workflow could return the status tuple
from agents.sre_team import sandbox_executor


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
        canvas.error("Cycle failed or prerequisites missing for post-cycle checks.")
        return False

    # --- 2. Run SRE Workflow ---
    canvas.info(f"--- Running SRE Workflow ---")
    sre_success = False
    analysis_summary = None
    dep_issues = []
    syntax_test_ok = (True, "") # Default to success
    integration_issues = []

    try:
        # Instantiate the SRE Workflow
        sre_workflow = SRETeamWorkflow(session_id=f"sre-{current_project_path.name}-{action_type}")
        final_sre_response = None
        # Iterate through the workflow responses to execute it
        for response in sre_workflow.run(project_path=current_project_path, language=language):
             canvas.info(f"   [SRE_WF] {response.content}") # Log progress
             final_sre_response = response # Keep track of the last response

        # Check final status
        if final_sre_response and "completed successfully" in final_sre_response.content:
             sre_success = True
             analysis_summary = final_sre_response.extra_data.get("analysis_summary", {})
             # Retrieve other results from session state if needed
             sre_memory = sre_workflow.session_state.get("sre_memory", [])
             dep_issues = next((item['issues'] for item in sre_memory if item['phase'] == 'dependency_check'), [])
             integration_issues = next((item['issues'] for item in sre_memory if item['phase'] == 'integration_check'), [])
             syntax_test_record = next((item for item in sre_memory if item['phase'] == 'syntax_and_tests'), None)
             if syntax_test_record:
                  syntax_test_ok = (syntax_test_record['status'] == 'ok', syntax_test_record['message'])

        else:
             canvas.warning("SRE Workflow finished, but final success message not detected.")
             analysis_summary = sre_workflow.session_state.get("last_analysis_summary", {})

    except Exception as e:
         canvas.error(f"SRE Workflow failed with exception: {e}")
         analysis_summary = sre_workflow.session_state.get("last_analysis_summary", {}) # Try to get summary anyway
         sre_success = False

    # We might want to proceed to Review/Guardrail even if SRE workflow had non-critical errors
    # Let's proceed if analysis_summary was retrieved, otherwise fail.
    if analysis_summary is None:
         canvas.error("SRE Workflow failed critically before analysis summary could be retrieved.")
         return False


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
                analysis_summary=analysis_summary # Use summary from SRE workflow state
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
            static_analysis_summary=analysis_summary,
            dependency_summary=dep_issues,
            syntax_check_result=syntax_test_ok,
            review_feedback=review_feedback
            # TODO: Pass integration_issues if needed
        )
        if guardrail_decision == GUARDRAIL_BLOCK:
            canvas.error("🚦 Guardrails blocked further action:")
            for reason in guardrail_reasons: canvas.error(f"  - {reason}")
            canvas.end_process(f"Action '{action_type}' aborted by guardrails.")
            return False # Overall action failed due to block
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
        if integration_issues: commit_lines.append(f"[Integration Issues: {len(integration_issues)} found]")
        if dep_issues: commit_lines.append(f"[Dependency Issues: {len(dep_issues)} found]")
        if not syntax_test_ok[0]: commit_lines.append("[Syntax/Test Check Failed]")

        commit_msg = "\n\n".join(commit_lines)
        version_controller.initialize_and_commit(current_project_path, commit_msg)

        canvas.info(f"--- Post-Cycle Checks Completed ---")
        if guardrail_decision == GUARDRAIL_WARN: canvas.success(f"{action_type.capitalize()} cycle completed with warnings.")
        else: canvas.success(f"{action_type.capitalize()} cycle completed successfully.")
        return True # Overall action considered successful

    except Exception as e:
        canvas.error(f"Error during post-SRE steps (Review/Guardrail/Commit): {e}")
        canvas.error(traceback.format_exc())
        return False # Post-cycle failed critically

