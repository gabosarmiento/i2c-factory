# /workflow/modification/code_executor.py
# Handles executing the modification plan steps by calling the CodeModifierAgent.

from pathlib import Path
import pandas as pd # For type hinting if needed, though not used directly here
from typing import Any # For type hinting embed model and table

# Import necessary agent INSTANCES
from agents.modification_team import code_modifier_agent
# Import RAG retrieval function for per-step context
from .rag_retrieval import retrieve_context_for_step
# Import CLI controller
from cli.controller import canvas

def execute_modification_steps(modification_plan: list[dict], project_path: Path, table: Any, embed_model: Any) -> tuple[dict, list]:
    """
    Iterates through the plan, retrieves context for each step, calls the modifier,
    and collects results.

    Args:
        modification_plan: The list of modification steps.
        project_path: Path to the project directory.
        table: LanceDB table instance.
        embed_model: SentenceTransformer model instance.

    Returns:
        A tuple containing:
        - modified_code_map (dict): Map of file paths to their new content.
        - files_to_delete (list): List of Path objects for files to be deleted.
    """
    canvas.step("Executing modification plan (generating code with specific context)...")
    modified_code_map = {}
    files_to_delete = []
    all_steps_succeeded = True # Assume success initially

    try:
        for step in modification_plan:
            action = step.get('action', '').lower()
            file_rel_path = step.get('file')
            if not file_rel_path:
                canvas.warning(f"   Skipping invalid plan step (missing 'file'): {step}")
                continue

            if action == 'delete':
                files_to_delete.append(project_path / file_rel_path)
                canvas.info(f"  - Planned deletion: {file_rel_path}")
                continue

            # --- RAG Query for THIS Specific Step ---
            retrieved_context_step_str = retrieve_context_for_step(step, table, embed_model)
            # --- End Per-Step RAG Query ---

            # Call modifier agent, passing the specific retrieved context
            # Handle potential errors from modify_code directly
            try:
                modified_content = code_modifier_agent.modify_code(
                    modification_step=step,
                    project_path=project_path,
                    retrieved_context=retrieved_context_step_str
                )
                if modified_content is not None:
                    modified_code_map[file_rel_path] = modified_content
                    canvas.success(f"  - Generated content for '{action}' on {file_rel_path}")
                else:
                    # modify_code should raise an exception if it fails permanently
                    # If it returns None unexpectedly, treat as failure
                    raise RuntimeError(f"Code modifier returned None for '{action}' on {file_rel_path}")

            except Exception as mod_err:
                 # Catch error from modify_code call
                 canvas.error(f"  - Failed step '{action}' on {file_rel_path}: {mod_err}")
                 all_steps_succeeded = False
                 # Decide whether to stop the whole process on one step failure
                 # For now, let's break the loop on the first failure
                 break

    except Exception as e:
         # Catch errors from the loop orchestration itself
         canvas.error(f"Unexpected error during modification execution loop: {e}")
         all_steps_succeeded = False


    if not all_steps_succeeded:
         # Raise an exception to signal failure to the main cycle orchestrator
         raise RuntimeError("One or more modification steps failed during code generation.")

    return modified_code_map, files_to_delete
