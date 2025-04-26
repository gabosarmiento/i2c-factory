# /workflow.py
# Manages the overall user session, interaction loop, and coordinates calls
# to generation cycles and post-processing agents.

import os
import sys
from pathlib import Path
import re
import json # Needed for processing agent output

# Import the generation cycle function
from generation_cycle import run_generation_cycle

# Import necessary agent INSTANCES
from agents.core_agents import input_processor_agent # Need processor here now
from agents.sre_team import (
    version_controller,
    dependency_verifier,
    sandbox_executor
)
# Import CLI controller
from cli.controller import canvas # Handles user interaction

# --- Configuration ---
DEFAULT_OUTPUT_DIR_BASE = Path("./output") # Base directory for projects

def sanitize_filename(name: str) -> str:
    """Removes or replaces characters unsafe for filenames/directory names."""
    name = name.strip()
    name = re.sub(r'[\\/*?:"<>|\s]+', '_', name)
    name = re.sub(r'[^\w\-_]', '', name)
    return name[:50] or "untitled_project"


def run_session():
    """Manages the overall user session and interaction loop."""
    canvas.info("Initializing Session...")

    # Agents are imported instances, instantiation happens in their respective modules

    # Session state variables
    current_project_path: Path | None = None
    last_idea: str | None = None
    # Store the structured goal (objective & language) for the current project context
    current_structured_goal: dict | None = None

    while True: # Main interaction loop
        canvas.step("Ready for next action")

        # Determine the prompt based on whether a project context exists
        if current_project_path:
             action_prompt = f"Project: '{current_project_path.name}'. Next action ('f <feature_idea>', 'r' to refine last, 'q' to quit):"
        else:
             action_prompt = "Enter project idea (or 'q' to quit):"

        user_input = canvas.get_user_input(action_prompt).strip()
        command = user_input.lower()
        idea_for_cycle = None
        structured_goal_for_cycle = None # Goal to pass to generation cycle
        perform_generation = False

        # --- Parse User Command ---
        if command == 'q':
            canvas.info("Exiting session.")
            break
        elif command == 'r' and last_idea:
            if not current_project_path or not current_structured_goal:
                canvas.warning("Cannot refine without an active project context (idea and language). Please start a new idea.")
                continue
            # For refinement, reuse the last structured goal
            structured_goal_for_cycle = current_structured_goal
            perform_generation = True
            canvas.info(f"Refining project '{current_project_path.name}' based on last objective.")
            # TODO: Implement actual refinement logic (might need different prompts/agents)

        elif command.startswith('f ') and current_project_path:
             feature_idea = user_input[2:].strip()
             if not feature_idea:
                 canvas.warning("Please provide a description for the feature.")
                 continue
             if not current_structured_goal:
                  canvas.warning("Cannot add feature without project context (language unknown).")
                  continue

             # Create a new objective for the feature, keeping the language
             # This might need more sophisticated handling (e.g., asking LLM to integrate objectives)
             objective_for_feature = f"Add feature to existing project: {feature_idea}"
             structured_goal_for_cycle = {
                 "objective": objective_for_feature,
                 "language": current_structured_goal["language"] # Reuse language
             }
             perform_generation = True
             canvas.info(f"Adding feature to project '{current_project_path.name}'.")
             # TODO: Feature addition logic needs context handling (reading files etc.)

        elif not current_project_path and command == 'r':
             canvas.warning("No previous idea to refine. Please enter a new project idea.")
             continue
        elif not current_project_path and command.startswith('f '):
             canvas.warning("No active project to add features to. Please start a new project idea.")
             continue
        elif command: # Treat any other non-empty input as a new idea
            raw_idea = user_input
            last_idea = raw_idea # Store raw idea

            # --- Call Input Processor for New Idea --- <<< MOVED HERE >>>
            canvas.step("Clarifying new idea...")
            try:
                response = input_processor_agent.run(raw_idea)
                processed_goal = json.loads(response.content)
                if not isinstance(processed_goal, dict) or "objective" not in processed_goal or "language" not in processed_goal:
                     canvas.error("Failed to get valid structured goal from Input Processor.")
                     continue # Ask for input again
                current_structured_goal = processed_goal # Store for session
                structured_goal_for_cycle = current_structured_goal
                canvas.success(f"Objective: {current_structured_goal['objective']}")
                canvas.success(f"Language: {current_structured_goal['language']}")
            except Exception as e:
                canvas.error(f"Error clarifying idea: {e}")
                continue # Ask for input again
            # --- End Input Processor Call ---

            # --- Project Naming Logic ---
            suggested_name = sanitize_filename(current_structured_goal['objective'])
            name_prompt = f"Enter directory name (suggestion: '{suggested_name}'): "
            project_name_input = canvas.get_user_input(name_prompt).strip()
            final_project_name = sanitize_filename(project_name_input or suggested_name)

            current_project_path = DEFAULT_OUTPUT_DIR_BASE / final_project_name
            perform_generation = True
            canvas.info(f"Starting new project in: {current_project_path}")

        else:
            # Empty input, just re-prompt
            continue


        # --- Execute Generation & Post-Processing ---
        if perform_generation and structured_goal_for_cycle and current_project_path:
            # --- Run Generation Cycle ---
            # Pass the specific goal for this cycle
            generation_result = run_generation_cycle(structured_goal_for_cycle, current_project_path)
            generation_success = generation_result.get("success", False)
            # Use the language returned by the cycle (originally from the structured goal)
            language = generation_result.get("language")

            # --- Post-Generation SRE Checks & Actions (only if generation succeeded) ---
            if generation_success and language: # Ensure language is available
                # --- Dependency Check ---
                canvas.step("Performing SRE Dependency Check...")
                dep_issues = dependency_verifier.check_dependencies(current_project_path)
                if dep_issues:
                    canvas.warning("Dependency issues found:")
                    for issue in dep_issues: canvas.warning(f"  - {issue}")
                else:
                    canvas.success("Dependency checks passed.")

                # --- Sandbox Execution Check (Syntax/Compile Check) ---
                canvas.step("Performing SRE Syntax/Compile Check...")
                # Pass the CORRECT language retrieved from the cycle result
                exec_success, exec_msg = sandbox_executor.execute(current_project_path, language)
                if exec_success:
                    canvas.success("Syntax/Compile check passed.")
                else:
                    canvas.error("Syntax/Compile check failed.")
                    canvas.error(f"Details:\n{exec_msg}")

                # --- Version Control ---
                canvas.step("Performing Version Control...")
                # Use the objective from the cycle's goal for the commit message
                commit_msg = f"Completed cycle for objective: {structured_goal_for_cycle['objective'][:60]}"
                version_controller.initialize_and_commit(current_project_path, commit_msg)

            elif not generation_success:
                canvas.error("Generation cycle failed. Please review errors. Skipping post-generation steps.")
            elif not language:
                 canvas.error("Could not determine language after generation cycle. Skipping post-generation steps.")


        elif not perform_generation:
             canvas.warning("No generation action taken in this cycle.")


        print("-" * 30) # Separator for the loop

    canvas.end_process("Session ended.")


# This function is called by main.py
def start_factory_session():
    run_session()
