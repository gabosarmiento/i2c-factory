# /workflow/session.py
# Manages the user interaction loop, state, and calls the orchestrator.

import os
from pathlib import Path
import json

# Import agent instances needed for session logic
from agents.core_agents import input_processor_agent
# Import Budget Manager
from agents.budget_manager import BudgetManagerAgent # <<< IMPORT BUDGET MANAGER >>>
# Import orchestrator function
from .orchestrator import route_and_execute
# Import CLI controller and utils
from cli.controller import canvas
from .utils import sanitize_filename, ensure_project_path
# Import LLM instances for model IDs (needed for budget estimation)
from llm_providers import llm_middle, llm_highest # Import relevant models

# --- Configuration ---
DEFAULT_OUTPUT_DIR_BASE = Path("./output")

def run_session():
    """Manages the overall user session and interaction loop."""
    canvas.info("Initializing Session...")

    # --- Instantiate Budget Manager --- <<< ADDED >>>
    # TODO: Potentially get session_budget from command line args later
    budget_manager = BudgetManagerAgent(session_budget=None) # No overall budget for now

    # Session state variables
    current_project_path: Path | None = None
    last_raw_idea: str | None = None
    current_structured_goal: dict | None = None # Includes 'objective' and 'language'

    while True:
        canvas.step("Ready for next action")
        if current_project_path:
             action_prompt = f"Project: '{current_project_path.name}'. Next action ('f <feature_idea>', 'r' to refine last, 'q' to quit):"
        else:
             action_prompt = "Enter project idea (or 'q' to quit):"

        user_input = canvas.get_user_input(action_prompt).strip()
        command_lower = user_input.lower()

        # Reset variables for this loop iteration
        action_type = None
        action_detail = None
        project_path_for_action = current_project_path
        perform_action = False # Flag to control if action should proceed AFTER parsing and budget check
        prompt_for_budget_estimation = "" # Text to estimate cost from
        model_id_for_budget_estimation = "" # Model used for the estimated step
        budget_description = "" # Description for the budget request

        # --- Parse User Command ---
        if command_lower == 'q':
            canvas.info("Exiting session.")
            # Display final consumption before breaking
            final_tokens, final_cost = budget_manager.get_session_consumption()
            canvas.info(f"Session Summary: Consumed ~{final_tokens} tokens (~${final_cost:.6f})")
            break

        # --- Handle actions REQUIRING an active project ---
        elif current_project_path and current_structured_goal:
            if command_lower == 'r':
                if not last_raw_idea:
                    canvas.warning("Cannot refine without the last raw idea context.")
                    continue
                action_type = 'modify'
                action_detail = 'r'
                perform_action = True
                budget_description = "Project Refinement (Planning Step)"
                # Estimate based on planner prompt using last idea and context summary length?
                # Simplification: Estimate based on the request string itself for planning
                prompt_for_budget_estimation = action_detail
                model_id_for_budget_estimation = getattr(llm_highest, 'id', 'Unknown') # Planner uses highest
                canvas.info(f"Preparing refinement for project '{current_project_path.name}'...")

            elif command_lower.startswith('f '):
                feature_idea = user_input[len('f '):].strip()
                if not feature_idea:
                     canvas.warning("Please provide a description for the feature.")
                     continue
                action_type = 'modify'
                action_detail = f'f {feature_idea}'
                perform_action = True
                budget_description = f"Feature Addition Planning ({feature_idea[:20]}...)"
                # Estimate based on feature request string for planning
                prompt_for_budget_estimation = action_detail
                model_id_for_budget_estimation = getattr(llm_highest, 'id', 'Unknown') # Planner uses highest
                canvas.info(f"Preparing feature for project '{current_project_path.name}'...")

            elif user_input: # Any other input when project is active
                 canvas.warning(f"Unrecognized command '{user_input}' for active project '{current_project_path.name}'. Use 'f', 'r', or 'q'.")
                 continue

        # --- Handle actions when NO project is active (or input wasn't r/f/q) ---
        elif not current_project_path:
             if command_lower == 'r' or command_lower.startswith('f '):
                  canvas.warning("No active project. Please enter a new project idea first.")
                  continue
             elif user_input: # Treat as new idea
                raw_idea = user_input
                last_raw_idea = raw_idea

                # --- Budget Check BEFORE Clarification --- <<< ADDED >>>
                budget_description = "New Idea Clarification"
                prompt_for_budget_estimation = raw_idea
                model_id_for_budget_estimation = getattr(llm_middle, 'id', 'Unknown') # Processor uses middle
                approved = budget_manager.request_approval(
                    description=budget_description,
                    prompt=prompt_for_budget_estimation,
                    model_id=model_id_for_budget_estimation
                )
                if not approved:
                    canvas.warning("Action cancelled due to budget rejection.")
                    continue # Skip clarification and loop back
                # --- End Budget Check ---

                # Proceed with clarification only if budget approved
                canvas.step("Clarifying new idea...")
                response_content = None
                try:
                    response = input_processor_agent.run(raw_idea) # Direct call
                    response_content = response.content if hasattr(response, 'content') else str(response)

                    processed_goal = json.loads(response_content)
                    if not isinstance(processed_goal, dict) or "objective" not in processed_goal or "language" not in processed_goal:
                         canvas.error("LLM response for clarification was invalid JSON structure.")
                         canvas.error(f"Parsed Value: {processed_goal}")
                         continue
                    current_structured_goal = processed_goal
                    canvas.success(f"Objective: {current_structured_goal['objective']}")
                    canvas.success(f"Language: {current_structured_goal['language']}")

                except json.JSONDecodeError as json_err:
                     canvas.error(f"Failed to parse clarification response from LLM: {json_err}")
                     canvas.error(f"LLM Raw Response: {response_content[:500]}")
                     continue
                except Exception as e:
                    canvas.error(f"Error clarifying idea: {e}")
                    continue

                # If clarification succeeded, set up for generation cycle
                suggested_name = sanitize_filename(current_structured_goal['objective'])
                name_prompt = f"Enter directory name (suggestion: '{suggested_name}'): "
                project_name_input = canvas.get_user_input(name_prompt).strip()
                final_project_name = sanitize_filename(project_name_input or suggested_name)

                project_path_for_action = ensure_project_path(DEFAULT_OUTPUT_DIR_BASE, final_project_name)
                current_project_path = project_path_for_action
                action_type = 'generate'
                action_detail = current_structured_goal
                perform_action = True # Mark for budget check before generation
                canvas.info(f"Preparing new project generation in: {current_project_path}")

             # else: empty input when no project active, loop continues naturally

        # --- Safety check ---
        elif user_input:
             canvas.warning(f"Unrecognized input state. Input: '{user_input}', Project Active: {bool(current_project_path)}")
             continue


        # --- Budget Check before Orchestration (for Generate/Modify Planning) ---
        # This check happens *after* clarification for new ideas, but *before* planning for modifications
        if perform_action and action_type and action_detail:
            # Recalculate description, prompt, model for this specific check if needed
            # (It might differ slightly from the initial check for 'generate')
            if action_type == 'generate':
                budget_description = "Initial Project Generation (Planning Step)"
                prompt_for_budget_estimation = action_detail.get("objective", "")
                model_id_for_budget_estimation = getattr(llm_middle, 'id', 'Unknown') # Planner uses middle
            elif action_type == 'modify':
                # Description and prompt already set during command parsing
                 pass # Use values set earlier
            else:
                 budget_description = "Unknown Action"

            if budget_description != "Unknown Action" and model_id_for_budget_estimation:
                approved = budget_manager.request_approval(
                    description=budget_description,
                    prompt=prompt_for_budget_estimation,
                    model_id=model_id_for_budget_estimation
                )
                if not approved:
                    perform_action = False # Cancel the action
                    canvas.warning("Action cancelled due to budget rejection.")
            else:
                 perform_action = False

        # --- Call Orchestrator ---
        if perform_action and action_type and action_detail and project_path_for_action:
            # Orchestrator calls cycles, which use direct .run() within try/except
            success = route_and_execute(
                action_type=action_type,
                action_detail=action_detail,
                current_project_path=project_path_for_action,
                current_structured_goal=current_structured_goal
                # Pass budget_manager if orchestrator needs it for per-step checks later
                # budget_manager=budget_manager
            )
            if not success:
                 canvas.error(f"Action '{action_type}' failed. Please review logs.")
            # If action failed, should we reset current_project_path? Maybe not yet.

        print("-" * 30) # Separator

    # Final summary is printed when 'q' is entered

    canvas.end_process("Session ended.") # This line might not be reached if loop breaks


# This function is called by main.py
def start_factory_session():
    run_session()
