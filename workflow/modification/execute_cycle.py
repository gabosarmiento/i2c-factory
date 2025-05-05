# /workflow/modification/execute_cycle.py
# Main orchestrator for the modification cycle.

from pathlib import Path
import pandas as pd
import json
import traceback
# Import functions from other modules in this package
from .rag_retrieval import retrieve_context_for_planner, retrieve_context_for_step
from .plan_generator import generate_modification_plan
from .code_executor import execute_modification_steps
from .test_and_quality import generate_unit_tests, run_quality_checks
from .file_operations import write_files_to_disk, delete_files

# Import agents (only need context_reader for embed model)
from agents.modification_team import context_reader_agent

# Import DB utils
from db_utils import (
    get_db_connection,
    get_or_create_table,
    TABLE_CODE_CONTEXT,
    SCHEMA_CODE_CONTEXT,
)

# Import CLI controller
from cli.controller import canvas

def execute_modification_cycle(
    user_request: str,
    project_path: Path,
    language: str,
    db,                           # LanceDBConnection
    embed_model                  # SentenceTransformerEmbedder
) -> dict:
    """
    Runs the full cycle for modifying an existing project using RAG.
    Returns a dict with keys: success (bool), language (str), code_map (dict).
    """
    canvas.start_process(f"Modification Cycle for: {project_path.name}")
    result = {"success": False, "language": language, "code_map": None}

    try:
        # ───── Step 1: Validate DB ─────────────────────────
        if db is None:
            raise ConnectionError("No DB connection passed to modification cycle.")
        canvas.info(f"[DB] Using LanceDBConnection: {type(db)}")

        # ───── Step 2: Retrieve Planner Context via RAG ─────
        planner_ctx = retrieve_context_for_planner(
            user_request=user_request,
            db=db,
            embed_model=embed_model
        )
        canvas.info(f"[RAG] Planner context retrieved.")

        # ───── Step 3: Generate Modification Plan ──────────
        modification_plan = generate_modification_plan(
            user_request=user_request,
            retrieved_context_plan=planner_ctx,
            project_path=project_path,
            language=language
        )
        if not modification_plan:
            raise RuntimeError("Planning returned no steps.")
        canvas.info(f"[Plan] Generated {len(modification_plan)} steps.")

        # ───── Step 4: Execute Each Modification Step ──────
        # Pass the DB & embedder into the step executor so it can RAG‐retrieve step context
        modified_code_map, files_to_delete = execute_modification_steps(
            modification_plan=modification_plan,
            project_path=project_path,
            db=db,
            embed_model=embed_model
        )
        canvas.info(f"[Exec] Applied modifications to {len(modified_code_map)} files.")

        # ───── Step 5: Generate & Run Unit Tests ──────────
        final_code_map = generate_unit_tests(modified_code_map)
        canvas.info(f"[Tests] Generated/ran tests for {len(final_code_map)} modules.")

        # ───── Step 6: Quality Checks ──────────────────────
        if not run_quality_checks(final_code_map):
            canvas.warning("[Quality] Some quality checks failed—continuing anyway.")

        # ───── Step 7: Write Files & Cleanup ───────────────
        write_files_to_disk(final_code_map, project_path)
        delete_files(files_to_delete, project_path)
        canvas.end_process(f"Modification cycle for {project_path.name} completed successfully.")

        # ───── All Done ────────────────────────────────────
        result["success"]  = True
        result["code_map"] = final_code_map

    except Exception as e:
        canvas.error(f"Modification cycle failed: {type(e).__name__} - {e}")
        canvas.error(traceback.format_exc())
        canvas.end_process("Modification cycle aborted.")
    finally:
        canvas.info("[DB] Modification cycle cleaned up.")

    return result
