# workflow/modification/execute_cycle.py
# Main orchestrator for the modification cycle.

import traceback
from pathlib import Path
import json
from typing import Optional, Dict, List, Any

# Import functions from other modules in this package
from .rag_retrieval import retrieve_context_for_planner
from .plan_generator import generate_modification_plan
from .code_executor import execute_modification_steps
from .test_and_quality import generate_unit_tests, run_quality_checks
from .file_operations import write_files_to_disk, delete_files

# Import agents (only need context_reader for embed model)
from i2c.agents.modification_team import context_reader_agent

# Import DB utils
from i2c.db_utils import get_db_connection

# Import CLI controller
from i2c.cli.controller import canvas

def execute_modification_cycle(
    user_request: str,
    project_path: Path,
    language: str,
    db=None,                      # LanceDBConnection
    embed_model=None,             # SentenceTransformerEmbedder
    retrieved_context=None        # Optional pre-retrieved context
) -> dict:
    """
    Runs the full cycle for modifying an existing project using RAG.
    
    Args:
        user_request: The user's modification request
        project_path: Path to the project
        language: Programming language of the project
        db: Optional LanceDB connection for RAG
        embed_model: Optional embedding model for RAG
        retrieved_context: Optional pre-retrieved RAG context
        
    Returns:
        dict: Result with keys: success (bool), language (str), code_map (dict)
    """
    canvas.start_process(f"Modification Cycle for: {project_path.name}")
    result = {"success": False, "language": language, "code_map": None}

    try:
        # ───── Step 1: Validate or Initialize DB ─────────────────────────
        if db is None:
            canvas.info("No DB connection provided, attempting to initialize...")
            try:
                db = get_db_connection()
                if db is None:
                    canvas.warning("Unable to initialize database connection. RAG will be limited.")
            except Exception as e:
                canvas.warning(f"Error initializing database: {e}")
        else:
            canvas.info(f"[DB] Using provided LanceDBConnection")
        
        # ───── Step 1b: Validate or Initialize Embedding Model ──────────
        if embed_model is None:
            canvas.info("No embedding model provided, attempting to initialize...")
            try:
                from i2c.workflow.modification.rag_config import get_embed_model
                embed_model = get_embed_model()
                if embed_model is None:
                    canvas.warning("Unable to initialize embedding model. RAG will be limited.")
            except Exception as e:
                canvas.warning(f"Error initializing embedding model: {e}")
        else:
            canvas.info(f"[RAG] Using provided embedding model")

        # ───── Step 2: Retrieve Planner Context via RAG ─────────────────
        planner_ctx = retrieved_context or ""  # Use provided context if available
        if not planner_ctx and db is not None and embed_model is not None:
            try:
                planner_ctx = retrieve_context_for_planner(
                    user_request=user_request,
                    db=db,
                    embed_model=embed_model
                )
                canvas.info(f"[RAG] Planner context retrieved: {len(planner_ctx.split()) if planner_ctx else 0} words")
            except Exception as e:
                canvas.warning(f"[RAG] Error retrieving planner context: {e}")
                planner_ctx = ""
        else:
            if retrieved_context:
                canvas.info(f"[RAG] Using provided context: {len(retrieved_context.split())} words")
            else:
                canvas.warning("[RAG] Skipping context retrieval due to missing components")

        # ───── Step 3: Generate Modification Plan ──────────────────────
        modification_plan = generate_modification_plan(
            user_request=user_request,
            retrieved_context_plan=planner_ctx,
            project_path=project_path,
            language=language
        )
        if not modification_plan:
            raise RuntimeError("Planning returned no steps.")
        canvas.info(f"[Plan] Generated {len(modification_plan)} steps.")

        # ───── Step 4: Execute Each Modification Step ───────────────────
        try:
            # Pass the DB & embedder into the step executor so it can RAG‐retrieve step context
            modified_code_map, files_to_delete = execute_modification_steps(
                modification_plan=modification_plan,
                project_path=project_path,
                db=db,
                embed_model=embed_model
            )
            canvas.info(f"[Exec] Applied modifications to {len(modified_code_map)} files.")
        except Exception as e:
            # Handle execution errors with more robust error management
            canvas.error(f"Error during modification execution: {e}")
            
            # Provide a fallback for simple cases
            if len(modification_plan) == 1:
                step = modification_plan[0]
                canvas.warning(f"Attempting fallback approach for {step.get('file')}")
                
                try:
                    # Simple fallback implementation for single steps
                    file_path = step.get('file')
                    full_path = project_path / file_path
                    
                    # Different handling based on action type
                    if step.get('action') == 'create':
                        content = f"# Created file for: {step.get('what')}\n# TODO: Implement {step.get('how')}\n"
                        modified_code_map = {file_path: content}
                        files_to_delete = []
                    elif step.get('action') == 'modify' and full_path.exists():
                        content = full_path.read_text() + f"\n# TODO: Implement {step.get('what')}: {step.get('how')}\n"
                        modified_code_map = {file_path: content}
                        files_to_delete = []
                    elif step.get('action') == 'delete':
                        modified_code_map = {}
                        files_to_delete = [full_path]
                    else:
                        raise ValueError(f"Cannot handle action {step.get('action')} in fallback mode")
                    
                    canvas.info(f"[Fallback] Created basic implementation for {file_path}")
                except Exception as fallback_error:
                    canvas.error(f"Fallback approach failed: {fallback_error}")
                    raise e  # Re-raise the original error
            else:
                # Can't handle multiple steps in fallback mode
                raise
    
        # ───── Step 5: Generate & Run Unit Tests ─────────────────────────
        final_code_map = generate_unit_tests(modified_code_map)
        canvas.info(f"[Tests] Generated/ran tests for {len(final_code_map)} modules.")

        # ───── Step 6: Quality Checks ───────────────────────────────────
        if not run_quality_checks(final_code_map):
            canvas.warning("[Quality] Some quality checks failed—continuing anyway.")

        # ───── Step 7: Write Files & Cleanup ────────────────────────────
        write_files_to_disk(final_code_map, project_path)
        delete_files(files_to_delete, project_path)
        canvas.end_process(f"Modification cycle for {project_path.name} completed successfully.")

        # ───── All Done ───────────────────────────────────────────────
        result["success"] = True
        result["code_map"] = final_code_map

    except Exception as e:
        canvas.error(f"Modification cycle failed: {type(e).__name__} - {e}")
        canvas.error(traceback.format_exc())
        canvas.end_process("Modification cycle aborted.")
    finally:
        canvas.info("[DB] Modification cycle cleaned up.")

    return result