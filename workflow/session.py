# /workflow/session.py
# Manages the user interaction loop, state, and calls the orchestrator.

import os
from pathlib import Path
import json

# Import agent instances needed
from agents.core_agents import input_processor_agent
from agents.budget_manager import BudgetManagerAgent
from agents.modification_team.context_reader.context_reader_agent import context_reader_agent

# Import orchestrator function
from .orchestrator import route_and_execute
# Import CLI controller and utils
from cli.controller import canvas
from .utils import sanitize_filename, ensure_project_path
# Import LLM instances for model IDs/fallbacks
from llm_providers import llm_small, llm_xs, llm_middle, llm_highest
# Import handlers from the sibling module
from .session_handlers import (
    handle_get_user_action,
    handle_load_project,
    handle_new_project_idea # We might inline parts of this now
)


# --- Configuration ---
DEFAULT_OUTPUT_DIR_BASE = Path("./output")

def run_session():
    """Manages the overall user session and interaction loop."""
    canvas.info("Initializing Session...")
    budget_manager = BudgetManagerAgent(session_budget=None)

    # Session state variables
    current_project_path: Path | None = None
    last_raw_idea: str | None = None
    current_structured_goal: dict | None = None

    while True:
        canvas.step("Ready for next action")
        command_type, command_detail = handle_get_user_action(current_project_path)

        # --- Process Command ---
        if command_type == 'quit':
            canvas.info("Exiting session.")
            final_tokens, final_cost = budget_manager.get_session_consumption()
            canvas.info(f"Session Summary: Consumed ~{final_tokens} tokens (~${final_cost:.6f})")
            break # Exit the while loop

        elif command_type == 'load_project':
            loaded_path, inferred_goal = handle_load_project(command_detail)
            if loaded_path:
                current_project_path = loaded_path
                current_structured_goal = inferred_goal
                last_raw_idea = f"Loaded project: {command_detail}"
                if not current_structured_goal:
                     canvas.warning("Could not infer project objective/language.")
            # Loop back immediately after loading/indexing
            print("-" * 30); continue

        elif command_type == 'new_idea':
            # --- Handle New Idea Inline & Auto-Trigger ---
            raw_idea = command_detail
            last_raw_idea = raw_idea

            # 1. Budget Check for Clarification
            budget_description_clarify = "New Idea Clarification"
            model_id_clarify = getattr(llm_middle, 'id', 'Unknown')
            approved_clarify = budget_manager.request_approval(
                description=budget_description_clarify,
                prompt=raw_idea,
                model_id=model_id_clarify
            )
            if not approved_clarify:
                canvas.warning("Clarification cancelled due to budget rejection.")
                print("-" * 30); continue # Ask for input again

            # 2. Clarify Idea
            canvas.step("Clarifying new idea...")
            response_content = None
            processed_goal = None
            try:
                response = input_processor_agent.run(raw_idea)
                response_content = response.content if hasattr(response, 'content') else str(response)
                processed_goal = json.loads(response_content)
                if not isinstance(processed_goal, dict) or "objective" not in processed_goal or "language" not in processed_goal:
                     raise ValueError("LLM response for clarification was invalid JSON structure.")
                current_structured_goal = processed_goal # Set goal immediately
                canvas.success(f"Objective: {current_structured_goal['objective']}")
                canvas.success(f"Language: {current_structured_goal['language']}")
            except Exception as e:
                canvas.error(f"Error clarifying idea: {e}")
                if response_content: canvas.error(f"LLM Raw Response: {response_content[:500]}")
                print("-" * 30); continue # Ask for input again if clarification fails

            # 3. Get Project Name
            suggested_name = sanitize_filename(current_structured_goal['objective'])
            name_prompt = f"Enter directory name (suggestion: '{suggested_name}'): "
            project_name_input = canvas.get_user_input(name_prompt).strip()
            final_project_name = sanitize_filename(project_name_input or suggested_name)
            project_path_for_action = ensure_project_path(DEFAULT_OUTPUT_DIR_BASE, final_project_name)
            current_project_path = project_path_for_action # Set path immediately

            # 4. Index (empty dir)
            context_reader_agent.index_project_context(current_project_path)
            canvas.info(f"Preparing new project generation in: {current_project_path}")

            # 5. Budget Check for Generation Planning
            budget_description_gen = "Initial Project Generation (Planning Step)"
            prompt_for_gen_est = current_structured_goal.get("objective", "")
            model_id_gen_est = getattr(llm_middle, 'id', 'Unknown')
            approved_gen = budget_manager.request_approval(
                description=budget_description_gen,
                prompt=prompt_for_gen_est,
                model_id=model_id_gen_est
            )

            # 6. Auto-Trigger Orchestrator if Approved
            if approved_gen:
                success = route_and_execute(
                    action_type='generate',
                    action_detail=current_structured_goal,
                    current_project_path=current_project_path,
                    current_structured_goal=current_structured_goal
                )
                if not success:
                     canvas.error("Action 'generate' failed. Please review logs.")
                # State is now set for the next loop iteration
            else:
                 canvas.warning("Generation cancelled due to budget rejection.")
                 # Reset project path/goal if generation cancelled? Or leave as is?
                 # Let's leave it as is, user can try 'r' or 'f' next time.

            # --- End New Idea Block ---

        elif command_type == 'modify':
            # --- Handle Modify ---
            if not current_project_path or not current_structured_goal:
                 canvas.warning("Cannot modify without an active project context (objective/language). Load ('p') or create a project first.")
                 print("-" * 30); continue

            action_type = 'modify'
            action_detail_for_orchestrator = command_detail # 'r' or 'f <desc>'

            # Budget Check for Modification Planning
            budget_description_mod = f"Project Modification Planning ({action_detail_for_orchestrator})"
            prompt_for_mod_est = action_detail_for_orchestrator
            model_id_mod_est = getattr(llm_highest, 'id', 'Unknown')
            approved_mod = budget_manager.request_approval(
                description=budget_description_mod,
                prompt=prompt_for_mod_est,
                model_id=model_id_mod_est
            )

            if approved_mod:
                # Call Orchestrator
                success = route_and_execute(
                    action_type=action_type,
                    action_detail=action_detail_for_orchestrator,
                    current_project_path=current_project_path,
                    current_structured_goal=current_structured_goal
                )
                if not success:
                     canvas.error(f"Action '{action_type}' failed. Please review logs.")
            else:
                 canvas.warning("Action cancelled due to budget rejection.")
            # --- End Modify Block ---

        else: # Invalid command type from handler, or empty input
            print("-" * 30)
            continue # Loop back to prompt

        # Print separator only if we didn't already continue or break
        print("-" * 30)

    # Final summary printed when 'q' is entered
    canvas.end_process("Session ended.")


# This function is called by main.py
def start_factory_session():
    run_session()

