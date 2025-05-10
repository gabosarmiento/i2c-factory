# Handles executing the modification plan steps by calling the CodeModifierAgent.
# src/i2c/workflow/modification/code_executor.py
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Import necessary agent INSTANCES
#from i2c.agents.modification_team import code_modifier_agent
# replace legacy code modifier agent
from i2c.workflow.modification.code_modifier_adapter import apply_modification

# Import RAG retrieval function for per-step context
from .rag_retrieval import retrieve_context_for_step
# Import CLI controller
from i2c.cli.controller import canvas

def execute_modification_steps(
    modification_plan, project_path, db, embed_model
) -> Tuple[Dict[str, str], List[Path]]:
    """
    Iterates through the plan, retrieves context for each step, calls the modifier,
    and collects results.
    """
    canvas.step("Executing modification plan (generating code with step-specific context)...")
    modified_code_map = {}
    files_to_delete = []
    all_steps_succeeded = True  # Assume success initially

    # Check if database has any indexed chunks
    db_has_chunks = False
    try:
        from i2c.db_utils import TABLE_CODE_CONTEXT
        table = db.open_table(TABLE_CODE_CONTEXT)
        df = table.to_pandas()
        db_has_chunks = len(df) > 0
        
        if not db_has_chunks:
            canvas.warning("  ⚠️ Warning: No indexed code chunks found in database. RAG retrieval will be limited.")
            canvas.warning("  ⚠️ Consider running the indexing process for better context-aware modifications.")
    except Exception as e:
        canvas.warning(f"  ⚠️ Warning: Could not verify database chunks: {e}")

    try:
        for step_idx, step in enumerate(modification_plan):
            canvas.info(f"  Step {step_idx+1}/{len(modification_plan)}")
            
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
            canvas.info(f"   -> Retrieving context for '{action}' on '{file_rel_path}': {step.get('what', '')[:40]}...")
            try:
                ctx = retrieve_context_for_step(step, db, embed_model)
            except Exception as e:
                canvas.error(f"   -> Context retrieval error: {e}")
                ctx = ""
                
            # Normalize to a plain string
            if not isinstance(ctx, str):
                ctx = ""
                
            # Report length
            count = len(ctx.split()) if ctx else 0
            if count:
                canvas.info(f"   -> Found relevant context ({count} words)")
            else:
                canvas.info("   -> No specific relevant context found for this step")

            # Use this normalized context for modification
            retrieved_context_step_str = ctx
            # --- End Per-Step RAG Query ---

            # Call modifier agent, passing the specific retrieved context
            try:
                patch_or_err = apply_modification(
                    modification_step=step,
                    project_path=project_path,
                    retrieved_context=retrieved_context_step_str,
                )
    
                # Patch → store unified diff; error dict → raise
                if isinstance(patch_or_err, dict):  # error
                    raise RuntimeError(patch_or_err.get("error"))
                modified_content = patch_or_err.unified_diff
                
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
                # Decision point: should we continue with remaining steps or abort on first failure?
                # For now, let's break the loop on the first failure for predictability
                break

    except Exception as e:
        # Catch errors from the loop orchestration itself
        canvas.error(f"Unexpected error during modification execution loop: {e}")
        all_steps_succeeded = False

    if not all_steps_succeeded:
        # Raise an exception to signal failure to the main cycle orchestrator
        raise RuntimeError("One or more modification steps failed during code generation.")

    return modified_code_map, files_to_delete