# /workflow/orchestrator.py
# Routes actions and handles post-cycle SRE checks, review, guardrails, integration checks, and version control.
# Refined and final version based on user input.

from pathlib import Path
import json
import traceback # For detailed error logging

# Cycle execution functions
from .generation import execute_generation_cycle
from .modification import execute_modification_cycle

# SRE agents
from agents.sre_team import dependency_verifier, sandbox_executor, version_controller

# Quality & integration agents
from agents.quality_team import (
    static_analysis_agent,
    integration_checker_agent,
    reviewer_agent,
    guardrail_agent,
)
# Guardrail decision constants
from agents.quality_team.guardrail_agent import GUARDRAIL_BLOCK, GUARDRAIL_WARN, GUARDRAIL_CONTINUE

# CLI controller
from cli.controller import canvas

# Review-storage helper (optional)
try:
    from utils.review_storage import save_review_to_file
except ImportError:
    # Define dummy function if util not found
    def save_review_to_file(*args, **kwargs):
        canvas.warning("[Orchestrator] save_review_to_file utility not found.")
        return None


def route_and_execute(
    action_type: str,
    action_detail: any,
    current_project_path: Path,
    current_structured_goal: dict | None
) -> bool:
    """
    Routes the user's action to the correct execution cycle, then runs:
      1. Static analysis summary query
      2. Dependency check
      3. Syntax/compile check
      4. Integration AST check
      5. AI code review
      6. Guardrail evaluation
      7. Version control commit (if not blocked)

    Returns True only if the cycle succeeded and was not blocked by guardrails.
    """
    cycle_success = False
    # Determine language, default to python if not specified in goal
    language = current_structured_goal.get("language") if current_structured_goal else "python"
    final_code_map = None # Will hold the generated/modified code

    # --- 0. Execute main generation or modification cycle ---
    canvas.info(f"--- Starting {action_type.capitalize()} Cycle ---")
    try:
        if action_type == "generate":
            if isinstance(action_detail, dict):
                result = execute_generation_cycle(action_detail, current_project_path)
                cycle_success = result.get("success", False)
                language = result.get("language") or language # Update language if cycle returns it
                final_code_map = result.get("code_map")
            else:
                raise ValueError("Missing structured goal for generation.")

        elif action_type == "modify":
            if isinstance(action_detail, str) and language:
                result = execute_modification_cycle(action_detail, current_project_path, language)
                cycle_success = result.get("success", False)
                language = result.get("language") or language # Update language
                final_code_map = result.get("code_map")
            else:
                raise ValueError("Invalid detail or missing language for modification.")
        else:
            raise ValueError(f"Unknown action type: {action_type}")

    except Exception as e:
        canvas.error(f"Error during '{action_type}' cycle: {e}")
        return False # Cycle itself failed

    # --- 1. Post-cycle checks ---
    if not (cycle_success and isinstance(language, str) and final_code_map is not None):
        canvas.error("Cycle failed or prerequisites missing for post-cycle checks.")
        return False # Cannot proceed

    canvas.info(f"--- Running Post-{action_type.capitalize()} Checks ---")

    # Initialize results from checks
    analysis_summary = {}
    dep_issues: list = []
    syntax_ok: tuple[bool, str] = (True, "") # Default to success
    integration_issues: list[str] = []
    review_feedback: str | None = None
    guardrail_decision = GUARDRAIL_CONTINUE # Default
    guardrail_reasons: list[str] = []

    try: # Wrap all post-cycle steps
        # Step 1: Static Analysis Summary
        canvas.step("Performing SRE Static Analysis Summary...")
        analysis_summary = static_analysis_agent.get_analysis_summary(current_project_path)
        if analysis_summary.get("errors"):
            canvas.warning(f"Static analysis summary errors: {analysis_summary['errors']}")
        else:
            canvas.success("Static analysis summary retrieved.")

        # Step 2: Dependency Check
        canvas.step("Performing SRE Dependency Check...")
        dep_issues = dependency_verifier.check_dependencies(current_project_path)
        if dep_issues:
            canvas.warning(f"Dependency issues found: {len(dep_issues)}")
        else:
            canvas.success("Dependency checks passed.")

        # Step 3: Syntax/Compile Check (using SandboxExecutor)
        canvas.step("Performing SRE Syntax/Compile & Test Check...") # Renamed step slightly
        syntax_ok = sandbox_executor.execute(current_project_path, language) # sandbox now includes tests
        if syntax_ok[0]:
            canvas.success("Syntax/Compile & Tests check passed (or no tests found).")
        else:
            canvas.error(f"Syntax/Compile or Tests check failed: {syntax_ok[1]}")

        # Step 4: Integration AST Check
        canvas.step("Performing SRE Integration Check...")
        integration_issues = integration_checker_agent.check_integrations(current_project_path)
        if integration_issues:
            canvas.warning("Potential integration issues found:")
            for issue in integration_issues:
                canvas.warning(f"  - {issue}")
        else:
            canvas.success("Basic integration checks passed.")

        # Step 5: AI Code Review
        canvas.step("Performing AI Code Review...")
        if current_structured_goal: # Review needs goal context
            review_feedback = reviewer_agent.review_code(
                structured_goal=current_structured_goal,
                code_map=final_code_map,
                analysis_summary=analysis_summary
                # TODO: Pass other check results (syntax_ok, dep_issues, integration_issues) to reviewer?
            )
            if review_feedback:
                canvas.info("[AI Review Feedback]:")
                for line in review_feedback.splitlines(): canvas.info(f"  {line}")
                # Save the review
                save_review_to_file(current_project_path, review_feedback)
            else:
                canvas.warning("AI Review Agent failed or produced no feedback.")
        else:
            canvas.warning("Skipping AI Review: Project goal context missing.")

        # Step 6: Guardrail Evaluation
        canvas.step("Performing Guardrail Evaluation...")
        guardrail_decision, guardrail_reasons = guardrail_agent.evaluate_results(
            static_analysis_summary=analysis_summary,
            dependency_summary=dep_issues,
            syntax_check_result=syntax_ok, # Pass tuple from sandbox_executor
            review_feedback=review_feedback
            # TODO: Pass integration_issues to guardrail?
        )
        if guardrail_decision == GUARDRAIL_BLOCK:
            canvas.error("🚦 Guardrails blocked further action:")
            for reason in guardrail_reasons: canvas.error(f"  - {reason}")
            canvas.end_process(f"Action '{action_type}' aborted by guardrails.")
            return False # Overall action failed due to block
        if guardrail_decision == GUARDRAIL_WARN:
            canvas.warning("🚦 Guardrails issued warnings:")
            for reason in guardrail_reasons: canvas.warning(f"  - {reason}")

        # Step 7: Version Control Commit (Only if not blocked)
        canvas.step("Performing Version Control...")
        # Determine objective for commit message
        objective_summary = "Unknown Objective"
        if isinstance(action_detail, str): # For 'r' or 'f ...'
            objective_summary = action_detail
        elif isinstance(action_detail, dict): # For 'generate'
            objective_summary = action_detail.get("objective", "Unknown Objective")

        # Construct detailed commit message
        commit_lines = [f"Completed {action_type} cycle for: {objective_summary[:50]}"]
        if review_feedback: commit_lines.append("[AI Review included]")
        if guardrail_decision != GUARDRAIL_CONTINUE: commit_lines.append(f"[Guardrail Status: {guardrail_decision}]")
        if integration_issues: commit_lines.append(f"[Integration Issues: {len(integration_issues)} found]")
        if dep_issues: commit_lines.append(f"[Dependency Issues: {len(dep_issues)} found]")
        if not syntax_ok[0]: commit_lines.append("[Syntax/Test Check Failed]") # Updated check name

        commit_msg = "\n\n".join(commit_lines)
        version_controller.initialize_and_commit(current_project_path, commit_msg)

        canvas.info(f"--- Post-Cycle Checks Completed ---")
        # Use a clearer success message here
        if guardrail_decision == GUARDRAIL_WARN:
            canvas.success(f"{action_type.capitalize()} cycle completed with warnings.")
        else:
            canvas.success(f"{action_type.capitalize()} cycle completed successfully.")
        return True # Overall action considered successful (even with warnings)

    except Exception as e:
        canvas.error(f"Error during post-cycle steps: {e}")
        canvas.error(traceback.format_exc()) # Log full traceback
        return False # Post-cycle failed critically

