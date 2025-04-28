# /agents/quality_team/static_analysis_agent.py
# Agent responsible for querying and summarizing static analysis results from LanceDB.

from pathlib import Path
import pandas as pd
from typing import Dict, List, Any
from db_utils import get_db_connection, get_or_create_table

# Import CLI for logging
try:
    from cli.controller import canvas
except ImportError:
    class FallbackCanvas: # Basic fallback logger
        def warning(self, msg): print(f"[WARN_SA_AGENT] {msg}")
        def error(self, msg): print(f"[ERROR_SA_AGENT] {msg}")
        def info(self, msg): print(f"[INFO_SA_AGENT] {msg}")
        def success(self, msg): print(f"[SUCCESS_SA_AGENT] {msg}")
    canvas = FallbackCanvas()


class StaticAnalysisAgent:
    """
    Queries LanceDB to retrieve and summarize stored static analysis metadata
    (lint errors, dependencies) for a given project path.
    """
    def __init__(self):
        print("📊 [StaticAnalysisAgent] Initialized.")

    def get_analysis_summary(self, project_path: Path) -> Dict[str, Any]:
        """
        Queries LanceDB for static analysis data and returns a summary.
        """
        canvas.info(f"🤖 [StaticAnalysisAgent] Retrieving analysis summary for: {project_path}")
        summary = {
            "total_lint_errors": 0, "files_with_lint_errors": [],
            "all_dependencies": set(), "errors": []
        }
        db = None
        table = None

        try:
            # --- Connect to DB and Table ---
            if not get_db_connection or not get_or_create_table:
                 summary["errors"].append("DB utility functions not imported correctly.")
                 raise ConnectionError("DB Utils not available.") # Raise error to stop

            canvas.info("   Connecting to vector database for analysis...")
            db = get_db_connection()
            if db is None: 
                raise ConnectionError("DB connection failed.")
            canvas.info(f"   [DB] Connection object obtained: {type(db)}")
            table = get_or_create_table(db)
            if table is None: raise ConnectionError("DB table acquisition failed.")
            canvas.success("   Database connection and table acquired successfully for analysis.")

            # --- Query LanceDB for relevant data ---
            canvas.info("   Querying LanceDB for analysis metadata...")
            # Pull the full table, then subset the columns you care about
            full_df = table.to_pandas()
            if {"path", "lint_errors", "dependencies"}.issubset(full_df.columns):
                results_df = full_df[["path", "lint_errors", "dependencies"]]
            else:
                # Fallback if schema changed—just take everything
                results_df = full_df
            # results_df = table.to_pandas(columns=["path", "lint_errors", "dependencies"])
            canvas.info(f"   Retrieved metadata for {len(results_df)} chunks from DB.")

            if results_df.empty:
                canvas.warning("   No analysis data found in LanceDB for this project.")
                summary["all_dependencies"] = []
                return summary # Return early if no data

            # --- Aggregate Results ---
            files_with_errors_set = set()
            for _, row in results_df.iterrows():
                 # Aggregate Lint Errors
                 lint_errors = row.get("lint_errors")
                 if isinstance(lint_errors, list) and lint_errors:
                      actual_errors = [err for err in lint_errors if isinstance(err, str) and "Ruff command not found" not in err]
                      if actual_errors:
                           summary["total_lint_errors"] += len(actual_errors)
                           file_path = row.get("path")
                           if file_path: files_with_errors_set.add(file_path)

                 # Aggregate Dependencies
                 dependencies = row.get("dependencies")
                 if isinstance(dependencies, list):
                      valid_deps = {dep for dep in dependencies if isinstance(dep, str) and dep}
                      summary["all_dependencies"].update(valid_deps)

            summary["files_with_lint_errors"] = sorted(list(files_with_errors_set))
            summary["all_dependencies"] = sorted(list(summary["all_dependencies"]))
            canvas.success("   Static analysis summary aggregated successfully.")

        except ConnectionError as db_err: # Catch specific DB errors
            summary["errors"].append(f"DB Error: {db_err}")
            canvas.error(f"   ❌ Failed DB operation for analysis: {db_err}")
            # Ensure dependencies list exists even on error
            if "all_dependencies" in summary and isinstance(summary["all_dependencies"], set):
                 summary["all_dependencies"] = sorted(list(summary["all_dependencies"]))
        except Exception as e:
            error_msg = f"Error querying or processing analysis data from LanceDB: {e}"
            summary["errors"].append(error_msg)
            canvas.error(f"   ❌ {error_msg}")
            # Ensure dependencies list exists even on error
            if "all_dependencies" in summary and isinstance(summary["all_dependencies"], set):
                 summary["all_dependencies"] = sorted(list(summary["all_dependencies"]))
        finally:
            # --- <<< Indicate DB handle usage finished for this analysis >>> ---
            if db or table:
                 canvas.info("   [DB] Static analysis finished using DB handles.")
            # Explicit close attempt (optional)
            # if db and hasattr(db, 'close') and callable(db.close):
            #     try: db.close()
            #     except: pass
            # --- <<< End Final Block >>> ---


        # Log summary results before returning
        canvas.info(f"   [Static Analysis Summary Result]:")
        canvas.info(f"     - Total Lint Issues: {summary['total_lint_errors']}")
        if summary['files_with_lint_errors']:
            canvas.info(f"     - Files with Issues: {', '.join(summary['files_with_lint_errors'])}")
        canvas.info(f"     - Detected Dependencies: {summary['all_dependencies'] if summary['all_dependencies'] else 'None'}")
        if summary["errors"]:
             canvas.warning(f"     - Query/Processing Errors: {summary['errors']}")

        return summary

# Instantiate the agent globally for easy import
static_analysis_agent = StaticAnalysisAgent()
