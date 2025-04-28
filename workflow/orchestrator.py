# /workflow/orchestrator.py
# Routes actions and handles post-cycle SRE checks, review, guardrails, and version control.

from pathlib import Path
import json

# Import cycle execution functions
from .generation import execute_generation_cycle
from .modification import execute_modification_cycle

# Import SRE and Quality agent instances
from agents.sre_team import (
    dependency_verifier,
    sandbox_executor,
    version_controller
)
from agents.quality_team import (
    static_analysis_agent,
    reviewer_agent,
    guardrail_agent # <<< Import Guardrail >>>
)
# Import CLI controller
from cli.controller import canvas
# Import Review Storage Utility
try:
    from utils.review_storage import save_review_to_file
except ImportError:
    # Define dummy function
    def save_review_to_file(*args, **kwargs): return None

# Import Guardrail decision constants
from agents.quality_team.guardrail_agent import GUARDRAIL_CONTINUE, GUARDRAIL_WARN, GUARDRAIL_BLOCK


def route_and_execute(action_type: str, action_detail: any, current_project_path: Path, current_structured_goal: dict | None) -> bool:
    """
    Routes the user's action to the correct execution cycle and runs post-cycle steps.
    """
    cycle_success = False
    language = current_structured_goal.get("language") if current_structured_goal else "python"
    final_code_map = None

    # --- Execute the appropriate cycle ---
    try:
        if action_type == 'generate':
            if isinstance(action_detail, dict):
                generation_result = execute_generation_cycle(action_detail, current_project_path)
                cycle_success = generation_result.get("success", False)
                language = generation_result.get("language") or language
                final_code_map = generation_result.get("code_map")
            else: raise ValueError("Structured goal missing for generation.")

        elif action_type == 'modify':
            if isinstance(action_detail, str) and language:
                modification_result = execute_modification_cycle(action_detail, current_project_path, language)
                cycle_success = modification_result.get("success", False)
                language = modification_result.get("language") or language
                final_code_map = modification_result.get("code_map")
            else: raise ValueError("Invalid detail or language missing for modification.")
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    except Exception as e:
         canvas.error(f"Error during {action_type} cycle execution: {e}")
         return False

    # --- Post-Cycle SRE Checks, Review, Guardrail & Actions ---
    if cycle_success and isinstance(language, str) and final_code_map is not None:
        canvas.info(f"Running post-{action_type} SRE checks, Review & Guardrails...")
        analysis_summary = None
        review_feedback = None
        dep_issues = []
        syntax_check_result = (True, "Not run") # Default to success if not run

        try: # Wrap all post-cycle steps
            # 1. Static Analysis Summary
            canvas.step("Performing SRE Static Analysis Summary...")
            analysis_summary = static_analysis_agent.get_analysis_summary(current_project_path)
            # Log errors but don't stop for now
            if analysis_summary["errors"]: canvas.warning(f"Static analysis summary errors: {analysis_summary['errors']}")
            else: canvas.success("Static analysis summary retrieved.")

            # 2. Dependency Check
            canvas.step("Performing SRE Dependency Check...")
            dep_issues = dependency_verifier.check_dependencies(current_project_path) # Store issues
            if dep_issues: canvas.warning(f"Dependency issues found: {len(dep_issues)}")
            else: canvas.success("Dependency checks passed.")

            # 3. Sandbox Check (Syntax/Compile)
            canvas.step("Performing SRE Syntax/Compile Check...")
            syntax_check_result = sandbox_executor.execute(current_project_path, language) # Store result tuple
            if syntax_check_result[0]: canvas.success("Syntax/Compile check passed.")
            else: canvas.error(f"Syntax/Compile check failed: {syntax_check_result[1]}")

            # 4. AI Code Review
            canvas.step("Performing AI Code Review...")
            if current_structured_goal:
                review_feedback = reviewer_agent.review_code(
                    structured_goal=current_structured_goal,
                    code_map=final_code_map,
                    analysis_summary=analysis_summary
                )
                if review_feedback:
                    canvas.info("[AI Review Feedback]:")
                    for line in review_feedback.split('\n'): canvas.info(f"  {line}")
                    # Save Review Feedback
                    save_review_to_file(current_project_path, review_feedback)
                else:
                    canvas.warning("AI Review Agent failed or produced no feedback.")
            else:
                canvas.warning("Skipping AI Review: Project goal context is missing.")

            # --- <<< 5. Guardrail Check >>> ---
            canvas.step("Performing Guardrail Evaluation...")
            guardrail_decision, guardrail_reasons = guardrail_agent.evaluate_results(
                static_analysis_summary=analysis_summary,
                dependency_summary=dep_issues, # Pass collected dependency issues
                syntax_check_result=syntax_check_result, # Pass syntax check result
                review_feedback=review_feedback
            )

            if guardrail_decision == GUARDRAIL_BLOCK:
                 canvas.error("Guardrails blocked further action due to critical issues:")
                 for reason in guardrail_reasons:
                      canvas.error(f"  - {reason}")
                 # Do not proceed to commit
                 return False # Indicate overall action failure due to guardrail
            elif guardrail_decision == GUARDRAIL_WARN:
                 canvas.warning("Guardrails issued warnings:")
                 for reason in guardrail_reasons:
                      canvas.warning(f"  - {reason}")
                 # Proceed to commit but with warnings logged
            # else: GUARDRAIL_CONTINUE - proceed normally
            # --- <<< End Guardrail Check >>> ---


            # 6. Version Control (Only if not blocked)
            canvas.step("Performing Version Control...")
            commit_objective = action_detail if isinstance(action_detail, str) else action_detail.get('objective', 'Unknown objective')
            review_note = "\n\n[AI Review included]" if review_feedback else ""
            guardrail_note = f"\n\n[Guardrail Status: {guardrail_decision}]" if guardrail_decision != GUARDRAIL_CONTINUE else ""
            commit_msg = f"Completed {action_type} cycle for: {commit_objective[:50]}{review_note}{guardrail_note}"
            version_controller.initialize_and_commit(current_project_path, commit_msg)

            return True # Overall action considered successful (even with warnings)

        except Exception as e:
             canvas.error(f"Error during post-cycle steps: {e}")
             return False # Post-cycle failed critically

    # Handle cases where cycle failed or prerequisites missing
    elif not cycle_success: return False
    elif not isinstance(language, str): canvas.error("Invalid language type."); return False
    elif final_code_map is None: canvas.error("Code map missing."); return False
    return False # Default failure

