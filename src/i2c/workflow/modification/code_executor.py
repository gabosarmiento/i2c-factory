# Handles executing the modification plan steps by calling the CodeModifierAgent.
# src/i2c/workflow/modification/code_executor.py
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Import necessary agent INSTANCES
#from i2c.agents.modification_team import code_modifier_agent
# replace legacy code modifier agent
# from i2c.workflow.modification.code_modifier_adapter import apply_modification

# Import RAG retrieval function for per-step context
from .rag_retrieval import retrieve_context_for_step
# Import CLI controller
from i2c.cli.controller import canvas

def execute_modification_steps(
    *, 
    modification_plan: List[Dict[str, Any]],
    project_path: Path, 
    db=None, 
    embed_model=None,
    session_state: Dict[str, Any] | None = None,
) -> Tuple[Dict[str, str], List[Path]]:
    print(f"=== EXECUTE_MODIFICATION_STEPS CALLED ===")
    print(f"Plan steps: {len(modification_plan)}")
    """
    Execute all steps in `modification_plan` and return a map of modified files.

    Parameters
    ----------
    session_state
        A **single shared dictionary** created by the orchestrator.  If ``None``
        we create a throw-away dict so unit tests that call this helper in
        isolation still work.
    """
    shared = session_state if session_state is not None else {}
    
    canvas.step("Executing modification plan (generating code with step-specific context)...")
    modified_code_map: Dict[str, str] = {}
    files_to_delete: List[Path] = []
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
                from i2c.agents.modification_team.code_modification_manager_agno import apply_modification
                # Enable retrieval tools
                shared["use_retrieval_tools"]= True
                patch_or_err = apply_modification(
                    modification_step=step,
                    project_path=project_path,
                    retrieved_context=retrieved_context_step_str,
                    session_state=shared,
                )

                # Patch → store unified diff; error dict → raise
                if isinstance(patch_or_err, dict):  # error
                    raise RuntimeError(patch_or_err.get("error"))
                    
                # Extract the unified diff from the patch
                unified_diff = patch_or_err.unified_diff
                
                # Get the full path to the file
                full_file_path = project_path / file_rel_path
                
                # For create action, we can use the diff directly
                if action == 'create':
                    modified_code_map[file_rel_path] = unified_diff
                    canvas.success(f"  - Generated content for '{action}' on {file_rel_path}")
                    shared.setdefault("modified_files", {})[file_rel_path] = unified_diff
                else:
                    # For modify action, we need to apply the diff to the original content
                    try:
                        # Read the original file content
                        if full_file_path.exists():
                            original_content = full_file_path.read_text(encoding='utf-8')
                        else:
                            original_content = ""
                            
                        # Apply the diff to get the modified content
                        if unified_diff:
                            # Check if this is actual diff format or complete content
                            # Diffs typically start with "---" or contain "@@ -" markers
                            is_diff_format = unified_diff.startswith("---") or "@@ -" in unified_diff
                            
                            if is_diff_format:
                                # It's a real diff, apply it
                                modified_content = apply_diff_to_content(original_content, unified_diff)
                            else:
                                # It's the complete content, use it directly
                                modified_content = unified_diff
                                canvas.info(f"  - Using complete content as modification for {file_rel_path}")
                            # Store the result in the code map
                            modified_code_map[file_rel_path] = modified_content
                            shared.setdefault("modified_files", {})[file_rel_path] = modified_content
                            canvas.success(f"  - Modified content for '{action}' on {file_rel_path}")
                           
                        else:
                            # No changes were made, use original content
                            modified_code_map[file_rel_path] = original_content
                            canvas.warning(f"  - No changes detected for {file_rel_path}")
                    except Exception as diff_err:
                        canvas.error(f"  - Failed to apply diff to {file_rel_path}: {diff_err}")
                        canvas.error(f"  - Falling back to using raw diff")
                        # Fall back to using the raw diff
                        modified_code_map[file_rel_path] = unified_diff
                        shared.setdefault("modified_files", {})[file_rel_path] = unified_diff
                
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

def apply_diff_to_content(original_content: str, unified_diff: str) -> str:
    """
    Apply a unified diff to original content to get the modified content.
    This implementation uses only Python standard library.
    
    Args:
        original_content: The original file content
        unified_diff: The unified diff to apply
        
    Returns:
        The modified content after applying the diff
    """
    try:
        # Parse the diff to find hunks
        lines = unified_diff.splitlines()
        
        # Skip the file header lines (--- and +++)
        i = 0
        while i < len(lines) and not lines[i].startswith("@@"):
            i += 1
            
        # If no hunks found, return original content
        if i >= len(lines):
            return original_content
            
        # Process the original content as lines
        original_lines = original_content.splitlines()
        result_lines = original_lines.copy()
        
        # Process each hunk
        while i < len(lines):
            line = lines[i]
            
            # Process a hunk header (like @@ -1,5 +1,6 @@)
            if line.startswith("@@"):
                try:
                    # Parse the hunk header to extract line numbers
                    header_parts = line.split(" ")
                    if len(header_parts) < 3:
                        i += 1
                        continue
                        
                    # Extract source position (e.g., -1,5 means start at line 1, 5 lines)
                    source_pos = header_parts[1]
                    if not source_pos.startswith("-"):
                        i += 1
                        continue
                        
                    # Parse source line start and count
                    source_parts = source_pos[1:].split(",")
                    source_start = int(source_parts[0])
                    source_count = int(source_parts[1]) if len(source_parts) > 1 else 1
                    
                    # Extract target position (e.g., +1,6 means start at line 1, 6 lines)
                    target_pos = header_parts[2]
                    if not target_pos.startswith("+"):
                        i += 1
                        continue
                        
                    # Parse target line start and count
                    target_parts = target_pos[1:].split(",")
                    target_start = int(target_parts[0])
                    target_count = int(target_parts[1]) if len(target_parts) > 1 else 1
                    
                    # Move to the hunk content
                    i += 1
                    
                    # Process the hunk content
                    added_lines = []
                    source_line_used = 0
                    
                    while i < len(lines) and not lines[i].startswith("@@"):
                        content_line = lines[i]
                        
                        if content_line.startswith("+"):
                            # Added line - keep for output
                            added_lines.append(content_line[1:])
                        elif content_line.startswith("-"):
                            # Removed line - skip in output but count it
                            source_line_used += 1
                        elif content_line.startswith(" "):
                            # Context line - keep for output and count it
                            added_lines.append(content_line[1:])
                            source_line_used += 1
                        
                        i += 1
                    
                    # Apply the changes to result_lines
                    # Convert to 0-based indexing
                    source_start_idx = source_start - 1
                    
                    # Remove the specified lines
                    del result_lines[source_start_idx:source_start_idx + source_count]
                    
                    # Insert the new lines
                    result_lines[source_start_idx:source_start_idx] = added_lines
                    
                except Exception as e:
                    print(f"Error processing hunk: {e}")
                    i += 1
            else:
                i += 1
                
        # Convert back to string
        return "\n".join(result_lines)
        
    except Exception as e:
        # Log the error but return the original content to avoid data loss
        print(f"Error applying diff: {e}")
        import traceback
        traceback.print_exc()
        return original_content
    

def debug_modification_step(step, original_content, modified_content):
    import difflib
    diff = difflib.unified_diff(
        original_content.splitlines(), 
        modified_content.splitlines(), 
        fromfile='before', 
        tofile='after'
    )
    with open("modifications_debug.log", "a") as f:
        f.write(f"==== Modification for {step['file']} ====\n")
        f.write(f"What: {step['what']}\n")
        f.write(f"How: {step['how']}\n")
        f.write("Diff:\n")
        f.write("\n".join(diff))
        f.write("\n\n")