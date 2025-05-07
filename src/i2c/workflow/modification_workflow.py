# i2c/workflow/modification_workflow.py
from agno.workflow import Workflow, RunResponse
from pathlib import Path
from typing import Iterator, Dict, Any, List

from i2c.workflow.modification.rag_retrieval import (
    retrieve_context_for_planner,
    retrieve_context_for_step
)
from i2c.workflow.modification.plan_generator import generate_modification_plan
from i2c.workflow.modification.code_executor import execute_modification_steps
from i2c.workflow.modification.test_and_quality import (
    generate_unit_tests,
    run_quality_checks
)
from i2c.workflow.modification.file_operations import (
    write_files_to_disk,
    delete_files
)
from i2c.cli.controller import canvas

class ModificationWorkflow(Workflow):
    """
    Agno workflow for project modification cycle.
    Uses existing agents and follows the same steps as execute_modification_cycle.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_state.setdefault("modification_memory", [])
        
    def run(self, user_request: str, project_path: Path, language: str,
            db, embed_model) -> Iterator[RunResponse]:
        """Execute the modification workflow, yielding responses at each step."""
        canvas.start_process(f"Modification Cycle for: {project_path.name}")
        
        # Initialize session state
        self.session_state["modification_memory"] = []
        self.session_state["language"] = language
        self.session_state["project_path"] = str(project_path)
        self.session_state["user_request"] = user_request
        
        # Start workflow
        yield RunResponse(content=f"🚀 Starting Modification Workflow for: {project_path.name}")
        
        try:
            # Step 1: Validate DB
            if db is None:
                raise ConnectionError("No DB connection passed to modification cycle.")
            canvas.info(f"[DB] Using LanceDBConnection: {type(db)}")
            
            # Step 2: Retrieve Context for Planner
            planner_ctx = retrieve_context_for_planner(
                user_request=user_request,
                db=db,
                embed_model=embed_model
            )
            self.session_state["planner_context"] = planner_ctx
            canvas.info(f"[RAG] Planner context retrieved.")
            yield RunResponse(
                content="📚 Retrieved planner context",
                extra_data={"context_length": len(planner_ctx) if planner_ctx else 0}
            )
            
            # Step 3: Generate Modification Plan
            modification_plan = generate_modification_plan(
                user_request=user_request,
                retrieved_context_plan=planner_ctx,
                project_path=project_path,
                language=language
            )
            if not modification_plan:
                raise RuntimeError("Planning returned no steps.")
            
            self.session_state["modification_plan"] = modification_plan
            canvas.info(f"[Plan] Generated {len(modification_plan)} steps.")
            yield RunResponse(
                content=f"📝 Generated modification plan with {len(modification_plan)} steps",
                extra_data={"plan": modification_plan}
            )
            
            # Step 4: Execute Modification Steps
            modified_code_map, files_to_delete = execute_modification_steps(
                modification_plan=modification_plan,
                project_path=project_path,
                db=db,
                embed_model=embed_model
            )
            self.session_state["modified_code_map"] = modified_code_map
            self.session_state["files_to_delete"] = files_to_delete
            canvas.info(f"[Exec] Applied modifications to {len(modified_code_map)} files.")
            yield RunResponse(
                content=f"🔧 Applied modifications to {len(modified_code_map)} files",
                extra_data={
                    "modified_files": len(modified_code_map),
                    "files_to_delete": len(files_to_delete)
                }
            )
            
            # Step 5: Generate & Run Unit Tests
            final_code_map = generate_unit_tests(modified_code_map)
            self.session_state["final_code_map"] = final_code_map
            canvas.info(f"[Tests] Generated/ran tests for {len(final_code_map)} modules.")
            yield RunResponse(
                content=f"🧪 Generated tests for {len(final_code_map)} modules",
                extra_data={"tests_generated": len(final_code_map)}
            )
            
            # Step 6: Quality Checks
            quality_check_success = run_quality_checks(final_code_map)
            self.session_state["quality_check_success"] = quality_check_success
            if not quality_check_success:
                canvas.warning("[Quality] Some quality checks failed—continuing anyway.")
                yield RunResponse(
                    content="⚠️ Quality checks revealed issues, but continuing",
                    extra_data={"quality_success": False}
                )
            else:
                yield RunResponse(
                    content="✅ Quality checks passed",
                    extra_data={"quality_success": True}
                )
            
            # Step 7: Write Files & Cleanup
            write_files_to_disk(final_code_map, project_path)
            delete_files(files_to_delete, project_path)
            canvas.end_process(f"Modification cycle for {project_path.name} completed successfully.")
            
            # Final response
            yield RunResponse(
                content="✅ Modification workflow completed successfully",
                extra_data={
                    "success": True,
                    "code_map": final_code_map,
                    "language": language
                }
            )
            
        except Exception as e:
            canvas.error(f"Modification cycle failed: {type(e).__name__} - {e}")
            canvas.end_process("Modification cycle aborted.")
            
            # Store error in session state
            self.session_state["error"] = str(e)
            self.session_state["error_type"] = type(e).__name__
            
            yield RunResponse(
                content=f"❌ Modification workflow failed: {e}",
                extra_data={
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )