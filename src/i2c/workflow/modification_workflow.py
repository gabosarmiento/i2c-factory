# ── src/i2c/workflow/modification_workflow.py ────────────────────────────
"""AGNO‑style workflow that wraps the modification cycle but remains fully
session‑state aware: one mutable dict (`self.session_state`) is updated at every
phase and passed into helpers so downstream agents (Quality, Retry Planner,
etc.) see the same information.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterator, List

from agno.workflow import RunResponse, Workflow
from i2c.cli.controller import canvas

# Phase helpers --------------------------------------------------------------
from i2c.workflow.modification.rag_retrieval import (
    retrieve_context_for_planner,
)
from i2c.workflow.modification.plan_generator import generate_modification_plan
from i2c.workflow.modification.code_executor import execute_modification_steps
from i2c.workflow.modification.test_and_quality import (
    generate_unit_tests,
    run_quality_checks,
)
from i2c.workflow.modification.file_operations import delete_files, write_files_to_disk

# Reflective add‑ons ---------------------------------------------------------
from i2c.workflow.reflective_validation import ReflectiveValidator
from i2c.workflow.retry_planner import RetryPlanner


class ModificationWorkflow(Workflow):
    """High‑level AGNO workflow equivalent to `execute_modification_cycle`."""

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # guarantee the dict exists
        self.session_state.setdefault("modification_memory", [])

    # ------------------------------------------------------------------
    # Core run method
    # ------------------------------------------------------------------
    def run(
        self,
        user_request: str,
        project_path: Path,
        language: str,
        db,
        embed_model,
    ) -> Iterator[RunResponse]:
        """Execute the workflow step by step, yielding `RunResponse`s."""
        canvas.start_process(f"Modification Cycle for: {project_path.name}")

        # seed shared state -------------------------------------------------
        self.session_state.update(
            {
                "language": language,
                "project_path": str(project_path),
                "user_request": user_request,
            }
        )

        yield RunResponse(content=f"🚀 Starting Modification Workflow for: {project_path.name}")

        try:
            # ── 1. Validate DB ------------------------------------------------
            if db is None:
                raise ConnectionError("No DB connection passed to modification cycle.")
            canvas.info(f"[DB] Using LanceDBConnection: {type(db)}")

            # ── 2. Planner‑level RAG context --------------------------------
            planner_ctx = retrieve_context_for_planner(
                user_request=user_request,
                db=db,
                embed_model=embed_model,
            )
            self.session_state["planner_context"] = planner_ctx
            canvas.info("[RAG] Planner context retrieved.")
            yield RunResponse(
                content="📚 Retrieved planner context",
                extra_data={"context_length": len(planner_ctx) if planner_ctx else 0},
            )

            # ── 3. Generate modification plan ------------------------------
            modification_plan = generate_modification_plan(
                user_request=user_request,
                retrieved_context_plan=planner_ctx,
                project_path=project_path,
                language=language,
            )
            if not modification_plan:
                raise RuntimeError("Planning returned no steps.")
            self.session_state["modification_plan"] = modification_plan
            canvas.info(f"[Plan] Generated {len(modification_plan)} steps.")
            yield RunResponse(
                content=f"📝 Generated modification plan with {len(modification_plan)} steps",
                extra_data={"plan": modification_plan},
            )

            # ── 4. Execute modification steps ------------------------------
            modified_code_map, files_to_delete = execute_modification_steps(
                modification_plan=modification_plan,
                project_path=project_path,
                db=db,
                embed_model=embed_model,
                session_state=self.session_state,  # ← pass pointer
            )
            self.session_state["modified_code_map"] = modified_code_map
            self.session_state["files_to_delete"] = files_to_delete
            canvas.info(f"[Exec] Applied modifications to {len(modified_code_map)} files.")
            yield RunResponse(
                content=f"🔧 Applied modifications to {len(modified_code_map)} files",
                extra_data={
                    "modified_files": len(modified_code_map),
                    "files_to_delete": len(files_to_delete),
                },
            )

            # ── 5. Generate & run unit tests ------------------------------
            final_code_map = generate_unit_tests(modified_code_map)
            self.session_state["final_code_map"] = final_code_map
            canvas.info(f"[Tests] Generated/ran tests for {len(final_code_map)} modules.")
            yield RunResponse(
                content=f"🧪 Generated tests for {len(final_code_map)} modules",
                extra_data={"tests_generated": len(final_code_map)},
            )

            # ── 6. Quality checks ----------------------------------------
            quality_check_success = run_quality_checks(final_code_map)
            self.session_state["quality_check_success"] = quality_check_success
            if not quality_check_success:
                canvas.warning("[Quality] Some quality checks failed—continuing anyway.")
                yield RunResponse(
                    content="⚠️ Quality checks revealed issues, but continuing",
                    extra_data={"quality_success": False},
                )
            else:
                yield RunResponse(
                    content="✅ Quality checks passed",
                    extra_data={"quality_success": True},
                )

            # ── 7. Persist changes ---------------------------------------
            write_files_to_disk(final_code_map, project_path)
            delete_files(files_to_delete, project_path)
            canvas.end_process(
                f"Modification cycle for {project_path.name} completed successfully."
            )

            # final success response -------------------------------------
            yield RunResponse(
                content="✅ Modification workflow completed successfully",
                extra_data={
                    "success": True,
                    "code_map": final_code_map,
                    "language": language,
                },
            )

        except Exception as e:
            canvas.error(f"Modification cycle failed: {type(e).__name__} – {e}")
            canvas.end_process("Modification cycle aborted.")

            self.session_state.update({
                "error": str(e),
                "error_type": type(e).__name__,
            })
            yield RunResponse(
                content=f"❌ Modification workflow failed: {e}",
                extra_data={
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )


# == Reflective validation add‑on ============================================

def run_reflective_validation_if_needed(project_path: Path) -> bool:
    validator = ReflectiveValidator(project_path)
    result = validator.validate_project()
    if not result.success:
        print("[REFLECTIVE VALIDATION] Code validation failed:")
        print(f"Failure type: {result.failure_type}")
        print(f"Message: {result.message}")
        print("Suggestions:")
        for suggestion in result.suggestions:
            print(f" • {suggestion}")

        retry_planner = RetryPlanner(project_path)
        plan = retry_planner.plan_retry(result)

        print("[RETRY PLAN]")
        for action in plan["actions"]:
            print(f"↻ {action}")
        return False
    print("[REFLECTIVE VALIDATION] Code validated successfully.")
    return True


def run_modification_workflow(scenario_path: str) -> None:
    from i2c.workflow.scenario_processor import run_scenario

    run_scenario(scenario_path)
