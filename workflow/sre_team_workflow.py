# /workflow/sre_team_workflow.py
# Defines the Agno Workflow for executing the SRE check sequence.

from typing import Iterator, Dict, Any, List, Tuple
from pathlib import Path

from agno.workflow import Workflow, RunResponse # Import Agno Workflow components

# Import SRE and Quality agent instances
from agents.sre_team import (
    dependency_verifier,
    sandbox_executor,
    integration_checker_agent # Assuming integration checker is in sre_team now
)
from agents.quality_team import (
    static_analysis_agent
)

# Import CLI controller for logging within phases
try:
    from cli.controller import canvas
except ImportError:
    class FallbackCanvas: # Basic fallback logger
        def warning(self, msg): print(f"[WARN_SRE_WF] {msg}")
        def error(self, msg): print(f"[ERROR_SRE_WF] {msg}")
        def info(self, msg): print(f"[INFO_SRE_WF] {msg}")
        def success(self, msg): print(f"[SUCCESS_SRE_WF] {msg}")
    canvas = FallbackCanvas()


class SRETeamWorkflow(Workflow):
    """
    Agno Workflow for the SRE team.
    Executes critical post-generation/modification checks sequentially:
      1) Dependency Check
      2) Syntax & Unit Test Check
      3) Integration Check
      4) Static Analysis Summary Query
    Raises exceptions on critical failures. Returns analysis summary on success.
    """
    # Define agents used by this workflow if needed (optional but good practice)
    # dependency_agent = dependency_verifier
    # sandbox_agent = sandbox_executor
    # integration_agent = integration_checker_agent
    # static_analyzer = static_analysis_agent

    # The main run method orchestrates the phases
    def run(self, project_path: Path, language: str = "python") -> Iterator[RunResponse]:
        """
        Executes the SRE check phases.

        Args:
            project_path: Path to the project directory.
            language: Primary language of the project.

        Yields:
            RunResponse updates for each phase start/end.

        Returns:
            On successful completion, yields a final RunResponse containing
            the static analysis summary dictionary in its 'extra_data'.

        Raises:
            Exception: If any critical check phase fails.
        """
        yield RunResponse(content="🚀 Starting SRE Workflow...")

        # Phase 1: Dependency Check
        yield from self.dependency_check_phase(project_path)

        # Phase 2: Syntax & Unit Test Check
        syntax_test_ok, syntax_test_msg = yield from self.syntax_and_test_check_phase(project_path, language)
        # Decide if failure here is critical
        if not syntax_test_ok:
             # Exception raised within the phase method
             pass # Should already be handled by exception below

        # Phase 3: Integration Check
        integration_issues = yield from self.integration_check_phase(project_path)
        # Decide if integration issues are critical (for now, just log within phase)

        # Phase 4: Static Analysis Summary Query
        analysis_summary = yield from self.static_analysis_summary_phase(project_path)
        # Decide if summary errors are critical

        # If all phases passed without critical exceptions:
        yield RunResponse(
            content="✅ SRE Workflow completed successfully!",
            extra_data={"analysis_summary": analysis_summary} # Pass summary back
        )

    # --- Phase Methods ---

    def dependency_check_phase(self, project_path: Path) -> Iterator[RunResponse]:
        """Runs the dependency check."""
        yield RunResponse(content="📦 Starting Dependency Check Phase...")
        canvas.step("Performing SRE Dependency Check...") # Keep canvas logs too
        try:
            issues = dependency_verifier.check_dependencies(project_path)
            if issues:
                # Decide if this constitutes failure - let's WARN for now
                issues_str = "\n".join(issues)
                canvas.warning(f"Dependency Issues Found:\n{issues_str}")
                yield RunResponse(content=f"⚠️ Dependency Check completed with issues.", extra_data={"dependency_issues": issues})
            else:
                yield RunResponse(content="✅ Dependency Check completed.")
        except Exception as e:
             canvas.error(f"Critical error during Dependency Check: {e}")
             raise Exception(f"Dependency Check Phase Failed: {e}") from e

    def syntax_and_test_check_phase(self, project_path: Path, language: str) -> Iterator[RunResponse]:
        """Runs syntax check and unit tests via SandboxExecutor."""
        yield RunResponse(content="🏃 Starting Syntax & Test Check Phase...")
        canvas.step("Performing SRE Syntax/Compile & Test Check...")
        try:
            success, message = sandbox_executor.execute(project_path, language)
            if not success:
                # Raise exception to halt the workflow on syntax/test failure
                raise Exception(f"Syntax/Test Check Failed: {message}")
            else:
                yield RunResponse(content="✅ Syntax & Test Check completed.", extra_data={"sandbox_message": message})
                # Return tuple for internal use if needed, though yield is primary output
                yield success, message # Yield the result tuple as well
        except Exception as e:
             canvas.error(f"Critical error during Syntax/Test Check: {e}")
             raise Exception(f"Syntax/Test Check Phase Failed: {e}") from e


    def integration_check_phase(self, project_path: Path) -> Iterator[RunResponse]:
        """Runs the integration check."""
        yield RunResponse(content="🔗 Starting Integration Check Phase...")
        canvas.step("Performing SRE Integration Check...")
        try:
            issues = integration_checker_agent.check_integrations(project_path)
            if issues:
                canvas.warning("Potential integration issues found.")
                # Decide if this constitutes failure - WARN for now
                yield RunResponse(content="⚠️ Integration Check completed with issues.", extra_data={"integration_issues": issues})
                yield issues # Yield the issues list as well
            else:
                yield RunResponse(content="✅ Integration Check completed.")
                yield [] # Yield empty list for consistency
        except Exception as e:
             canvas.error(f"Critical error during Integration Check: {e}")
             raise Exception(f"Integration Check Phase Failed: {e}") from e

    def static_analysis_summary_phase(self, project_path: Path) -> Iterator[RunResponse]:
        """Queries static analysis summary from DB."""
        yield RunResponse(content="📊 Starting Static Analysis Summary Phase...")
        canvas.step("Performing SRE Static Analysis Summary...")
        try:
            summary = static_analysis_agent.get_analysis_summary(project_path)
            if summary.get("errors"):
                 # Log errors but don't necessarily fail the workflow for summary errors
                 canvas.warning(f"Static analysis summary encountered errors: {summary['errors']}")
            yield RunResponse(content="✅ Static Analysis Summary completed.", extra_data={"analysis_summary": summary})
            yield summary # Yield the summary dict
        except Exception as e:
             canvas.error(f"Critical error during Static Analysis Summary: {e}")
             raise Exception(f"Static Analysis Summary Phase Failed: {e}") from e

