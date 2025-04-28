# /workflow/sre_team_workflow.py
# Defines the Agno Workflow for executing the SRE check sequence.
# Defines the Agno Workflow for executing the SRE check sequence with reflective memory.

from typing import Iterator, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime, timezone  # UTC timestamps

from agno.workflow import Workflow, RunResponse

# Import SRE agents
from agents.sre_team import (
    dependency_verifier,
    sandbox_executor,
    integration_checker_agent,
)
# Import analyzer
from agents.quality_team import static_analysis_agent

# CLI controller fallback
try:
    from cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_SRE_WF] {msg}")
        def error(self, msg): print(f"[ERROR_SRE_WF] {msg}")
        def info(self, msg): print(f"[INFO_SRE_WF] {msg}")
        def success(self, msg): print(f"[SUCCESS_SRE_WF] {msg}")
    canvas = FallbackCanvas()


class SRETeamWorkflow(Workflow):
    """
    Agno Workflow for the SRE team with reflective session_state.
    Executes checks in order and records outcomes to session_state['sre_memory'].
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize memory
        self.session_state.setdefault("sre_memory", [])
        self.session_state.setdefault("last_analysis_summary", {})

    def run(self, project_path: Path, language: str = "python") -> Iterator[RunResponse]:
        # Clear then start
        self.session_state["sre_memory"] = []
        yield RunResponse(content="🚀 Starting SRE Workflow...")

        # Phase 1
        yield from self.dependency_check_phase(project_path)
        # Phase 2
        yield from self.syntax_and_test_check_phase(project_path, language)
        # Phase 3
        yield from self.integration_check_phase(project_path)
        # Phase 4
        summary = self.static_analysis_summary_phase(project_path)
        yield summary

        yield RunResponse(
            content="✅ SRE Workflow completed successfully!",
            extra_data={"analysis_summary": self.session_state["last_analysis_summary"]}
        )

    def dependency_check_phase(self, project_path: Path) -> Iterator[RunResponse]:
        ts = datetime.now(timezone.utc).isoformat()
        issues = dependency_verifier.check_dependencies(project_path)
        status = "warn" if issues else "ok"
        # record
        self.session_state["sre_memory"].append({
            "phase": "dependency_check",
            "timestamp": ts,
            "status": status,
            "issue_count": len(issues),
            "issues": issues,
        })
        if issues:
            canvas.warning(f"Dependency issues ({len(issues)}): {issues}")
            yield RunResponse(content="⚠️ Dependency Check completed with issues", extra_data={"dependency_issues": issues})
        else:
            canvas.success("Dependency check passed.")
            yield RunResponse(content="✅ Dependency Check completed.")

    def syntax_and_test_check_phase(self, project_path: Path, language: str) -> Iterator[RunResponse]:
        ts = datetime.now(timezone.utc).isoformat()
        ok, msg = sandbox_executor.execute(project_path, language)
        status = "ok" if ok else "fail"
        self.session_state["sre_memory"].append({
            "phase": "syntax_and_tests",
            "timestamp": ts,
            "status": status,
            "message": msg,
        })
        if not ok:
            canvas.error(f"Syntax/Test failed: {msg}")
            yield RunResponse(content=f"❌ Syntax & Test Check failed: {msg}")
            raise Exception(msg)
        canvas.success("Syntax & tests passed.")
        yield RunResponse(content="✅ Syntax & Test Check completed.", extra_data={"sandbox_message": msg})

    def integration_check_phase(self, project_path: Path) -> Iterator[RunResponse]:
        ts = datetime.now(timezone.utc).isoformat()
        issues = integration_checker_agent.check_integrations(project_path)
        status = "warn" if issues else "ok"
        self.session_state["sre_memory"].append({
            "phase": "integration_check",
            "timestamp": ts,
            "status": status,
            "issue_count": len(issues),
            "issues": issues,
        })
        if issues:
            canvas.warning(f"Integration issues ({len(issues)}): {issues}")
            yield RunResponse(content="⚠️ Integration Check completed with issues", extra_data={"integration_issues": issues})
        else:
            canvas.success("Integration check passed.")
            yield RunResponse(content="✅ Integration Check completed.")

    def static_analysis_summary_phase(self, project_path: Path) -> RunResponse:
        ts = datetime.now(timezone.utc).isoformat()
        summary = static_analysis_agent.get_analysis_summary(project_path)
        status = "warn" if summary.get("errors") else "ok"
        self.session_state["last_analysis_summary"] = summary
        self.session_state["sre_memory"].append({
            "phase": "static_analysis_summary",
            "timestamp": ts,
            "status": status,
            "summary": summary,
        })
        if summary.get("errors"):
            canvas.warning(f"Static analysis errors: {summary['errors']}")
        else:
            canvas.success("Static analysis summary retrieved.")
        return RunResponse(
            content="✅ Static Analysis Summary completed.",
            extra_data={"analysis_summary": summary}
        )
