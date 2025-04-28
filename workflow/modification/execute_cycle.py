# /workflow/modification/execute_cycle.py
# Main orchestrator for the modification cycle.

from pathlib import Path
import pandas as pd
import json

# Import functions from other modules in this package
from .rag_retrieval import retrieve_context_for_planner, retrieve_context_for_step
from .plan_generator import generate_modification_plan
from .code_executor import execute_modification_steps
from .test_and_quality import generate_unit_tests, run_quality_checks
from .file_operations import write_files_to_disk, delete_files

# Import agents (only need context_reader for embed model)
from agents.modification_team import context_reader_agent

# Import DB utils
from db_utils import get_db_connection, get_or_create_table

# Import CLI controller
from cli.controller import canvas

def execute_modification_cycle(user_request: str, project_path: Path, language: str) -> dict:
    """
    Runs the full cycle for modifying an existing project using RAG.
    """
    canvas.start_process(f"Modification Cycle for: {project_path.name}")
    return_context = {"success": False, "language": language, "code_map": None}
    db = None
    table = None
    embed_model = getattr(context_reader_agent, 'embedding_model', None)
    modification_plan = None
    final_code_map_incl_tests = None

    try:
        # Step 1: DB Connection and Table
        canvas.info("Attempting to connect to vector database for modification...")
        db = get_db_connection()
        # --- <<< Use explicit 'is None' check >>> ---
        if db is None:
            raise ConnectionError("get_db_connection() returned None.")
        # --- <<< End Check >>> ---
        canvas.info(f"   [DB] Connection object obtained: {type(db)}")
        table = get_or_create_table(db)
        if table is None:
            raise ConnectionError("get_or_create_table() returned None.")
        canvas.success("Database connection and table acquired successfully for modification.")

        # Step 2: RAG for Planner
        retrieved_context_plan = retrieve_context_for_planner(user_request, table, embed_model)

        # Step 3: Generate Plan
        modification_plan = generate_modification_plan(
            user_request=user_request,
            retrieved_context_plan=retrieved_context_plan,
            project_path=project_path,
            language=language
        )
        if not modification_plan:
             raise RuntimeError("Modification planning failed or produced empty plan.")

        # Step 4: Execute Modifications
        modified_code_map, files_to_delete = execute_modification_steps(
            modification_plan=modification_plan,
            project_path=project_path,
            table=table,
            embed_model=embed_model
        )

        # Step 5: Unit Tests
        final_code_map_incl_tests = generate_unit_tests(modified_code_map)
        return_context["code_map"] = final_code_map_incl_tests

        # Step 6: Quality Checks
        quality_checks_passed = run_quality_checks(final_code_map_incl_tests)
        if not quality_checks_passed:
             canvas.warning("Proceeding despite SRE Quality Check errors/failures.")

        # Step 7: Write Files
        write_files_to_disk(final_code_map_incl_tests, project_path)

        # Step 8: Deletion
        delete_files(files_to_delete, project_path)

        canvas.end_process(f"Modification cycle for {project_path.name} completed successfully.")
        return_context["success"] = True

    except ConnectionError as db_err: # Catch specific DB errors first
        canvas.error(f"Modification cycle failed due to DB Connection/Table Error: {db_err}")
        canvas.end_process(f"Modification cycle failed.")
    except Exception as e:
        canvas.error(f"Modification cycle failed unexpectedly: {type(e).__name__} - {e}")
        import traceback
        canvas.error(traceback.format_exc()) # Add traceback for unexpected errors
        canvas.end_process(f"Modification cycle failed.")
    finally:
        if db or table:
             canvas.info("   [DB] Modification cycle finished using DB handles.")

    return return_context
