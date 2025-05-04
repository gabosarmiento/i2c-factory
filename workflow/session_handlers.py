# /workflow/session_handlers.py
# Contains handler functions for different actions within the user session.

import json
from pathlib import Path

# Import necessary components (agents, utils, canvas, llms)
from agents.core_agents import input_processor_agent
# <<< Import the new context analyzer agent >>>
from agents.core_agents import project_context_analyzer_agent
from agents.modification_team.context_reader import context_reader_agent
from agents.budget_manager import BudgetManagerAgent
from cli.controller import canvas
from .utils import sanitize_filename, ensure_project_path
from builtins import llm_middle

# Function to safely parse JSON, returning None on failure
def _safe_json_loads(text: str) -> dict | None:
    try:
        # Pre-process potential markdown fences just in case
        text = text.strip()
        if text.startswith("```json"): text = text[len("```json"):].strip()
        if text.startswith("```"): text = text[3:].strip()
        if text.endswith("```"): text = text[:-3].strip()
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        canvas.error(f"DEBUG: Failed to parse JSON: {text[:500]}")
        return None

def handle_get_user_action(current_project_path: Path | None) -> tuple[str | None, str | None]:
    """Gets and parses the user's next action command."""
    # ... (logic remains the same) ...
    if current_project_path:
         project_status = f"Project: '{current_project_path.name}'"
         options = "'f <feature_idea>', 'r' (refine), 'p <path>' (switch project), 'q' (quit)"
         action_prompt = f"{project_status} | Options: {options}:"
    else:
         project_status = "No active project."
         options = "'<your new idea>', 'p <path>' (load existing), 'q' (quit)"
         action_prompt = f"{project_status} | Options: {options}:"

    user_input = canvas.get_user_input(action_prompt).strip()
    command_lower = user_input.lower()

    if command_lower == 'q':
        return 'quit', None
    elif command_lower.startswith('p '):
        path_str = user_input[len('p '):].strip().strip('\'"')
        return 'load_project', path_str
    elif current_project_path: # Actions requiring an active project
        if command_lower == 'r':
            return 'modify', 'r'
        elif command_lower.startswith('f '):
            feature_idea = user_input[len('f '):].strip()
            if not feature_idea:
                 canvas.warning("Please provide a description for the feature.")
                 return None, None # Invalid command
            return 'modify', f'f {feature_idea}'
        elif user_input: # Unrecognized command when project is active
             canvas.warning(f"Unrecognized command '{user_input}'. Use 'f', 'r', 'p', or 'q'.")
             return None, None
        else: # Empty input when project active
             return None, None
    elif user_input: # No project active, assume new idea
        return 'new_idea', user_input
    else: # Empty input when no project active
        return None, None


# <<< MODIFIED to return structured_goal >>>
def handle_load_project(path_str: str) -> tuple[Path | None, dict | None]:
    """Handles loading, indexing, and analyzing an existing project path."""
    potential_path = Path(path_str).expanduser()
    if not potential_path.is_dir():
        canvas.error(f"Invalid path provided: '{path_str}' is not a directory.")
        return None, None

    canvas.info(f"Switching to project path: {potential_path}")
    project_path = potential_path.resolve()
    structured_goal = None # Initialize goal

    # Trigger Indexing
    canvas.step(f"Indexing project context for '{project_path.name}'...")
    index_status = context_reader_agent.index_project_context(project_path)
    if index_status["errors"]:
        canvas.warning(f"Indexing completed with errors: {index_status['errors']}")
    else:
        canvas.success(f"Indexing complete. Indexed: {index_status['files_indexed']}, Skipped: {index_status['files_skipped']}.")

    # --- <<< Call the Project Context Analyzer Agent >>> ---
    canvas.step("Analyzing project structure for objective and suggestions...")
    try:
        # Create a list of file names relative to the project path
        # Filter out hidden files/dirs again for the prompt
        file_list = []
        for p in project_path.rglob('*'):
             if any(part.startswith('.') for part in p.relative_to(project_path).parts) or \
                any(ex in p.relative_to(project_path).parts for ex in ["__pycache__", "node_modules", ".git"]):
                 continue
             if p.is_file():
                  file_list.append(str(p.relative_to(project_path)))

        if not file_list:
             canvas.warning("No files found to analyze in the project directory.")
        else:
            # Limit number of files sent in prompt
            max_files_for_prompt = 100
            prompt = "Files:\n" + "\n".join(file_list[:max_files_for_prompt])
            if len(file_list) > max_files_for_prompt:
                 prompt += "\n... (more files exist)"

            # Use direct run - error handling below
            response = project_context_analyzer_agent.run(prompt)
            analysis_json = response.content if hasattr(response, "content") else str(response)
            analysis_data = _safe_json_loads(analysis_json) # Use safe JSON parsing

            if analysis_data and "objective" in analysis_data and "language" in analysis_data:
                # Store the inferred goal
                structured_goal = {
                    "objective": analysis_data.get("objective", "Objective could not be inferred."),
                    "language": analysis_data.get("language", "Language could not be inferred.")
                }
                canvas.success(f"Inferred Objective: {structured_goal['objective']}")
                canvas.success(f"Inferred Language: {structured_goal['language']}")

                # Display suggestions
                suggestions = analysis_data.get("suggestions", [])
                if suggestions:
                    canvas.info("🔮 Suggestions for next steps:")
                    for idx, suggestion in enumerate(suggestions, 1):
                        canvas.info(f"   {idx}. {suggestion}")
                else:
                    canvas.warning("   No specific next-step suggestions generated.")
            else:
                 canvas.warning("Could not fully analyze project structure from LLM response.")
                 canvas.error(f"Analyzer Raw Response: {analysis_json[:500]}")


    except Exception as e:
        canvas.warning(f"Could not analyze project or generate suggestions: {e}")
    # --- <<< End Analyzer Call >>> ---

    # Return path and the inferred goal (which might be None if analysis failed)
    return project_path, structured_goal


def handle_new_project_idea(raw_idea: str, budget_manager: BudgetManagerAgent, base_output_dir: Path) -> tuple[dict | None, Path | None]:
    """Handles clarifying, naming, and setting up a new project."""
    # ... (Budget check logic remains the same) ...
    budget_description = "New Idea Clarification"
    prompt_for_estimation = raw_idea
    model_id_for_estimation = getattr(llm_middle, 'id', 'Unknown')
    approved = budget_manager.request_approval(
        description=budget_description,
        prompt=prompt_for_estimation,
        model_id=model_id_for_estimation
    )
    if not approved:
        canvas.warning("Action cancelled due to budget rejection.")
        return None, None

    # Clarify Idea
    canvas.step("Clarifying new idea...")
    response_content = None
    processed_goal = None
    try:
        response = input_processor_agent.run(raw_idea)
        response_content = response.content if hasattr(response, 'content') else str(response)
        processed_goal = _safe_json_loads(response_content) # Use safe JSON parsing
        if not isinstance(processed_goal, dict) or "objective" not in processed_goal or "language" not in processed_goal:
             raise ValueError("LLM response for clarification was invalid JSON structure.")
        canvas.success(f"Objective: {processed_goal['objective']}")
        canvas.success(f"Language: {processed_goal['language']}")
    except Exception as e:
        canvas.error(f"Error clarifying idea: {e}")
        if response_content: canvas.error(f"LLM Raw Response: {response_content[:500]}")
        return None, None

    # Get Project Name
    suggested_name = sanitize_filename(processed_goal['objective'])
    name_prompt = f"Enter directory name (suggestion: '{suggested_name}'): "
    project_name_input = canvas.get_user_input(name_prompt).strip()
    final_project_name = sanitize_filename(project_name_input or suggested_name)
    project_path = ensure_project_path(base_output_dir, final_project_name)

    # Index the (currently empty) new project directory
    context_reader_agent.index_project_context(project_path)

    canvas.info(f"Preparing new project generation in: {project_path}")
    return processed_goal, project_path

