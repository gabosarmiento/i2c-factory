# i2c/workflow/quality_workflow.py
from agno.workflow import Workflow, RunResponse
from pathlib import Path
from typing import Iterator, Dict, Any, List

from i2c.agents.quality_team import (
    reviewer_agent,
    guardrail_agent,
)
from i2c.agents.quality_team.guardrail_agent import (
    GUARDRAIL_BLOCK, GUARDRAIL_WARN, GUARDRAIL_CONTINUE
)
from i2c.agents.sre_team import (
    dependency_verifier,
    version_controller,
    sandbox_executor
)
from i2c.cli.controller import canvas

class QualityWorkflow(Workflow):
    """
    Agno workflow for post-SRE quality checks.
    Handles review, guardrails, and version control.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_state.setdefault("quality_memory", [])
        
    def run(self, project_path: Path, structured_goal: dict, 
            code_map: dict, analysis_summary: dict) -> Iterator[RunResponse]:
        """Execute the quality workflow, yielding responses at each step."""
        canvas.info(f"--- Running Post-SRE Checks ---")
        
        # Initialize session state
        self.session_state["quality_memory"] = []
        self.session_state["project_path"] = str(project_path)
        self.session_state["structured_goal"] = structured_goal
        self.session_state["code_map"] = code_map
        self.session_state["analysis_summary"] = analysis_summary
        
        # Start workflow
        yield RunResponse(content="🚀 Starting Quality Workflow")
        
        # Step 1: AI Code Review
        yield from self.review_phase(structured_goal, code_map, analysis_summary)
        
        # Step 2: Guardrail Evaluation
        yield from self.guardrail_phase(analysis_summary)
        
        # If guardrails block, return early
        if self.session_state.get("guardrail_decision") == GUARDRAIL_BLOCK:
            yield RunResponse(
                content="🚫 Quality workflow aborted due to guardrail block",
                extra_data={
                    "success": False,
                    "reason": "blocked_by_guardrails",
                    "guardrail_reasons": self.session_state.get("guardrail_reasons", [])
                }
            )
            return
        
        # Step 3: Version Control
        yield from self.version_control_phase(project_path, structured_goal)
        
        # Final response
        yield RunResponse(
            content="✅ Quality workflow completed successfully",
            extra_data={
                "success": True,
                "guardrail_decision": self.session_state.get("guardrail_decision"),
                "review_feedback": self.session_state.get("review_feedback")
            }
        )
    
    def review_phase(self, structured_goal: dict, code_map: dict, 
                    analysis_summary: dict) -> Iterator[RunResponse]:
        """Perform AI Code Review."""
        canvas.step("Performing AI Code Review...")
        
        if not structured_goal:
            canvas.warning("Skipping AI Review: Project goal context missing.")
            yield RunResponse(
                content="⚠️ Skipping AI Review: No project goal context",
                extra_data={"review_skipped": True}
            )
            return
        
        try:
            review_feedback = reviewer_agent.review_code(
                structured_goal=structured_goal,
                code_map=code_map,
                analysis_summary=analysis_summary
            )
            
            # Store in session state
            self.session_state["review_feedback"] = review_feedback
            
            if review_feedback:
                canvas.info("[AI Review Feedback]:")
                for line in review_feedback.splitlines():
                    canvas.info(f"  {line}")
                
                # Save review to file (if the function exists)
                try:
                    from utils.review_storage import save_review_to_file
                    save_review_to_file(Path(self.session_state["project_path"]), review_feedback)
                except ImportError:
                    pass
                
                yield RunResponse(
                    content="📋 AI Review completed",
                    extra_data={"review_feedback": review_feedback}
                )
            else:
                canvas.warning("AI Review Agent failed or produced no feedback.")
                yield RunResponse(
                    content="⚠️ AI Review produced no feedback",
                    extra_data={"review_failed": True}
                )
        except Exception as e:
            canvas.error(f"Error during AI Review: {e}")
            self.session_state["review_error"] = str(e)
            yield RunResponse(
                content=f"❌ AI Review failed: {e}",
                extra_data={"error": str(e)}
            )
    
    def guardrail_phase(self, analysis_summary: dict) -> Iterator[RunResponse]:
        """Perform Guardrail Evaluation."""
        canvas.step("Performing Guardrail Evaluation...")
        
        try:
            # Re-run dependency and syntax checks for guardrail input
            canvas.info("   (Re-running checks for Guardrail input...)")
            project_path = Path(self.session_state["project_path"])
            dep_issues = dependency_verifier.check_dependencies(project_path)
            syntax_test_ok = sandbox_executor.execute(project_path, 
                                                     self.session_state.get("language", "python"))
            
            # Get review feedback from session state
            review_feedback = self.session_state.get("review_feedback")
            
            # Run guardrail evaluation
            guardrail_decision, guardrail_reasons = guardrail_agent.evaluate_results(
                static_analysis_summary=analysis_summary,
                dependency_summary=dep_issues,
                syntax_check_result=syntax_test_ok,
                review_feedback=review_feedback
            )
            
            # Store in session state
            self.session_state["guardrail_decision"] = guardrail_decision
            self.session_state["guardrail_reasons"] = guardrail_reasons
            self.session_state["dependency_issues"] = dep_issues
            self.session_state["syntax_test_ok"] = syntax_test_ok
            
            if guardrail_decision == GUARDRAIL_BLOCK:
                canvas.error("🚦 Guardrails blocked further action:")
                for reason in guardrail_reasons:
                    canvas.error(f"  - {reason}")
                canvas.end_process(f"Action aborted by guardrails.")
                
                yield RunResponse(
                    content="🚫 Guardrails blocked action",
                    extra_data={
                        "guardrail_decision": guardrail_decision,
                        "guardrail_reasons": guardrail_reasons
                    }
                )
            elif guardrail_decision == GUARDRAIL_WARN:
                canvas.warning("🚦 Guardrails issued warnings:")
                for reason in guardrail_reasons:
                    canvas.warning(f"  - {reason}")
                
                yield RunResponse(
                    content="⚠️ Guardrails issued warnings",
                    extra_data={
                        "guardrail_decision": guardrail_decision,
                        "guardrail_reasons": guardrail_reasons
                    }
                )
            else:
                canvas.success("🚦 Guardrail checks passed.")
                yield RunResponse(
                    content="✅ Guardrail checks passed",
                    extra_data={"guardrail_decision": guardrail_decision}
                )
                
        except Exception as e:
            canvas.error(f"Error during Guardrail Evaluation: {e}")
            self.session_state["guardrail_error"] = str(e)
            yield RunResponse(
                content=f"❌ Guardrail evaluation failed: {e}",
                extra_data={"error": str(e)}
            )
    
    def version_control_phase(self, project_path: Path, structured_goal: dict) -> Iterator[RunResponse]:
        """Perform Version Control operations."""
        canvas.step("Performing Version Control...")
        
        try:
            # Construct commit message
            action_type = self.session_state.get("action_type", "modification")
            objective_summary = structured_goal.get("objective", "Unknown Objective")
            
            commit_lines = [f"Completed {action_type} cycle for: {objective_summary[:50]}"]
            
            # Add details to commit message
            if self.session_state.get("review_feedback"):
                commit_lines.append("[AI Review included]")
                
            if self.session_state.get("guardrail_decision") != GUARDRAIL_CONTINUE:
                commit_lines.append(f"[Guardrail Status: {self.session_state.get('guardrail_decision')}]")
                
            dep_issues = self.session_state.get("dependency_issues", [])
            if dep_issues:
                commit_lines.append(f"[Dependency Issues: {len(dep_issues)} found]")
                
            syntax_test_ok = self.session_state.get("syntax_test_ok", (True, ""))
            if not syntax_test_ok[0]:
                commit_lines.append("[Syntax/Test Check Failed]")
                
            # Create commit message
            commit_msg = "\n\n".join(commit_lines)
            
            # Perform git operations
            version_controller.initialize_and_commit(project_path, commit_msg)
            
            # Store in session state
            self.session_state["commit_message"] = commit_msg
            
            yield RunResponse(
                content="📝 Version control operations completed",
                extra_data={"commit_message": commit_msg}
            )
            
        except Exception as e:
            canvas.error(f"Error during Version Control: {e}")
            self.session_state["version_control_error"] = str(e)
            yield RunResponse(
                content=f"❌ Version control failed: {e}",
                extra_data={"error": str(e)}
            )