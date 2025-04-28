# /workflow/orchestrator.py
# Routes actions and handles post-cycle SRE checks, review, guardrails, and version control using SelfHealingController.

from pathlib import Path
import json
import traceback

# Cycle execution functions
from .generation import execute_generation_cycle
from .modification import execute_modification_cycle

# --- <<< Import SelfHealingController >>> ---
from .self_healing_controller import SelfHealingController
# --- <<< Remove direct SRE Workflow import >>> ---
# from .sre_team_workflow import SRETeamWorkflow

# Import only agents needed AFTER SRE workflow
from agents.sre_team import version_controller # Keep VC here
from agents.quality_team import (
    reviewer_agent,
    guardrail_agent,
    # static_analysis_agent, dependency_verifier etc are used *within* SRE Workflow now
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

# Import sandbox executor only to get status if needed AFTER healing controller runs
# Alternatively, healing controller could return this status too
from agents.sre_team import sandbox_executor


def route_and_execute(
    action_type: str,
    action_detail: any,
    current_project_path: Path,
    current_structured_goal: dict | None
) -> bool:
    """
    Routes action to generation/modification cycle, runs SRE checks via
    SelfHealingController, then runs Review, Guardrail, and Version Control.
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

    # --- 2. Run SRE Workflow via SelfHealingController --- <<< MODIFIED BLOCK >>>
    canvas.info(f"--- Running SRE Workflow (with Self-Healing Controller) ---")
    sre_check_overall_success = False
    analysis_summary = None # Initialize
    # Other results like dep_issues, syntax_ok are now internal to SRE workflow / healing controller state

    try:
        # Instantiate and run the controller
        healing_controller = SelfHealingController(session_id=f"sre-{current_project_path.name}-{action_type}")
        sre_check_overall_success, sre_results = healing_controller.run_with_recovery(
            project_path=current_project_path, language=language
        )

        # Extract results needed later (analysis summary)
        analysis_summary = sre_results.get("analysis_summary", {})

        if not sre_check_overall_success:
            canvas.error("SRE Workflow could not be recovered after failure.")
            # Optionally inspect healing_controller.recovery_log here
            # Decide if we should still proceed to Review/Guardrail? Probably not.
            return False # SRE checks failed critically

    except Exception as e:
        canvas.error(f"Critical error during Healing-Controlled SRE Workflow execution: {e}")
        canvas.error(traceback.format_exc())
        return False # Critical failure in controller/SRE workflow
    # --- <<< END MODIFIED BLOCK >>> ---


    # --- 3. Post-SRE Workflow Steps (Review, Guardrail, Commit) ---
    # Only proceed if SRE checks passed (or recovered)
    canvas.info(f"--- Running Post-SRE Checks ---")
    review_feedback: str | None = None
    guardrail_decision = GUARDRAIL_CONTINUE # Default
    guardrail_reasons: list[str] = []

    try:
        # Step 3.1: AI Code Review
        canvas.step("Performing AI Code Review...")
        if current_structured_goal:
            # Pass the analysis summary retrieved from the healing controller result
            review_feedback = reviewer_agent.review_code(
                structured_goal=current_structured_goal,
                code_map=final_code_map,
                analysis_summary=analysis_summary
            )
            if review_feedback:
                canvas.info("[AI Review Feedback]:")
                for line in review_feedback.splitlines(): canvas.info(f"  {line}")
                save_review_to_file(current_project_path, review_feedback)
            else: canvas.warning("AI Review Agent failed or produced no feedback.")
        else: canvas.warning("Skipping AI Review: Project goal context missing.")

        # Step 3.2: Guardrail Evaluation
        canvas.step("Performing Guardrail Evaluation...")
        # We need dep_issues and syntax_ok for the guardrail.
        # These are currently logged inside SRETeamWorkflow state.
        # For simplicity now, let's re-run the checks quickly here.
        # TODO: Refactor SRETeamWorkflow to return these details reliably.
        canvas.info("   (Re-running checks for Guardrail input...)")
        dep_issues = dependency_verifier.check_dependencies(current_project_path)
        syntax_test_ok = sandbox_executor.execute(current_project_path, language)
        # integration_issues = integration_checker_agent.check_integrations(current_project_path) # If needed by guardrail

        guardrail_decision, guardrail_reasons = guardrail_agent.evaluate_results(
            static_analysis_summary=analysis_summary, # From healing controller result
            dependency_summary=dep_issues, # From re-run
            syntax_check_result=syntax_test_ok, # From re-run
            review_feedback=review_feedback
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
        # Construct detailed commit message
        commit_lines = [f"Completed {action_type} cycle for: {objective_summary[:50]}"]
        if review_feedback: commit_lines.append("[AI Review included]")
        if guardrail_decision != GUARDRAIL_CONTINUE: commit_lines.append(f"[Guardrail Status: {guardrail_decision}]")
        # if integration_issues: commit_lines.append(f"[Integration Issues: {len(integration_issues)} found]") # Get from re-run if needed
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

