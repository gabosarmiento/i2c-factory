# src/i2c/agents/quality_team/quality_team.py (Updated)

from typing import Dict, Any, List
from pathlib import Path
import asyncio
from builtins import llm_highest, llm_middle

from agno.team import Team
from agno.agent import Agent

# Import CLI for logging
try:
    from i2c.cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_GUARD] {msg}")
        def error(self, msg): print(f"[ERROR_GUARD] {msg}")
        def info(self, msg): print(f"[INFO_GUARD] {msg}")
        def success(self, msg): print(f"[SUCCESS_GUARD] {msg}")
    canvas = FallbackCanvas()


# Import existing Quality components
from i2c.agents.quality_team.static_analysis_agent import static_analysis_agent
from i2c.agents.quality_team.reviewer_agent import reviewer_agent
from i2c.agents.quality_team.guardrail_agent import guardrail_agent
from i2c.agents.quality_team.integration_checker_agent import integration_checker_agent

# Import new Enterprise Static Analyzer
from i2c.agents.quality_team.enterprise_static_analyzer import enterprise_static_analyzer

class QualityLeadAgent(Agent):
    """Lead agent for the Quality Team that coordinates quality checks"""
    
    # Define known quality gates
    ENTERPRISE_QUALITY_GATES = {
        'python': ['flake8', 'black', 'mypy', 'pytest', 'bandit'],
        'javascript': ['eslint'],
        'typescript': ['eslint', 'tsc'],
        'go': ['govet'],
        'java': ['checkstyle'],
        'all': ['flake8', 'black', 'mypy', 'pytest', 'bandit', 'eslint', 'tsc', 'govet', 'checkstyle']
    }
    
    def __init__(self, **kwargs):
        super().__init__(
            name="QualityLead",
            model=llm_middle, 
            role="Leads the quality team to ensure code quality",
            instructions=[
                "You are the lead of the Quality Team, responsible for code quality checks.",
                "Your job is to coordinate quality validation of code changes.",
                "You must ensure that the code meets quality standards and adheres to best practices.",
                "Work with your team to check static analysis, code review, and integration issues.",
                "Apply enterprise-grade quality gates like flake8, black, mypy, pytest, and bandit for Python code.",
                "If any quality issues are found, provide clear feedback for correction."
            ],
            **kwargs
        )
        # Initialize team session state if needed
        if self.team_session_state is None:
            self.team_session_state = {}
    
    async def validate_changes(
        self, project_path: Path, modified_files: Dict[str, str], quality_gates: List[str] = None
    ) -> Dict[str, Any]:
        """
        Validate code changes for quality.
        
        Args:
            project_path: Path to the project directory
            modified_files: Dictionary of modified files (path -> content)
            quality_gates: List of quality gates to check (e.g., 'flake8', 'black', etc.)
                           or preset gate groups like 'python', 'all', etc.
            
        Returns:
            Dictionary with validation results
        """
        # This function will coordinate the Quality team activities
        try:
            # Resolve quality gates to specific tools if preset names are used
            resolved_gates = self._resolve_quality_gates(quality_gates)
            
            # 1. Static analysis check
            static_analysis_results = await self._run_static_analysis(
                project_path, modified_files, resolved_gates
            )
            
            # 2. Enterprise quality gates check (if any gates specified)
            if resolved_gates:
                enterprise_results = await self._run_enterprise_checks(
                    project_path, modified_files, resolved_gates
                )
            else:
                enterprise_results = {"passed": True, "issues": []}
            
            # 3. Code review check
            review_results = await self._run_code_review(
                project_path, modified_files
            )
            
            # 4. Integration check
            integration_results = await self._run_integration_checks(
                project_path, modified_files
            )
            
            # 5. Guardrail check - include enterprise results
            guardrail_results = await self._run_guardrail_checks(
                static_analysis_results, 
                review_results, 
                integration_results,
                enterprise_results
            )
            
            # 6. Determine overall pass/fail
            all_passed = guardrail_results.get("decision") == "CONTINUE"
            
            # 7. Collect issues
            issues = []
            issues.extend(static_analysis_results.get("issues", []))
            issues.extend(review_results.get("issues", []))
            issues.extend(integration_results.get("issues", []))
            issues.extend(enterprise_results.get("issues", []))
            issues.extend(guardrail_results.get("reasons", []))
            
            # Store results in the team session state
            if self.team_session_state is not None:
                self.team_session_state["validation_results"] = {
                    "passed": all_passed,
                    "static_analysis_results": static_analysis_results,
                    "enterprise_results": enterprise_results,
                    "review_results": review_results,
                    "integration_results": integration_results,
                    "guardrail_results": guardrail_results,
                    "issues": issues
                }
            
            return {
                "passed": all_passed,
                "static_analysis_results": static_analysis_results,
                "enterprise_results": enterprise_results,
                "review_results": review_results,
                "integration_results": integration_results,
                "guardrail_results": guardrail_results,
                "issues": issues
            }
            
        except Exception as e:
            import traceback
            error_info = {
                "passed": False,
                "error": f"Quality team error: {str(e)}",
                "error_details": traceback.format_exc(),
                "issues": [f"Quality validation error: {str(e)}"]
            }
            
            # Store error in the team session state
            if self.team_session_state is not None:
                self.team_session_state["validation_results"] = error_info
                
            return error_info
    
    def _resolve_quality_gates(self, quality_gates: List[str] = None) -> List[str]:
        """
        Resolve quality gate preset names to specific tools.
        
        Args:
            quality_gates: List of quality gates or presets
            
        Returns:
            Resolved list of quality gates
        """
        if not quality_gates:
            return []
            
        resolved = []
        for gate in quality_gates:
            if gate in self.ENTERPRISE_QUALITY_GATES:
                # This is a preset, expand it
                resolved.extend(self.ENTERPRISE_QUALITY_GATES[gate])
            else:
                # This is a specific tool
                resolved.append(gate)
                
        # Remove duplicates while preserving order
        seen = set()
        return [x for x in resolved if not (x in seen or seen.add(x))]
    
    async def _run_static_analysis(
        self, project_path: Path, modified_files: Dict[str, str], quality_gates: List[str]
    ) -> Dict[str, Any]:
        """Run static analysis checks"""
        try:
            # Use static_analysis_agent to analyze code quality
            analysis_summary = static_analysis_agent.get_analysis_summary(project_path)
            
            # Convert to the expected format
            return {
                "passed": analysis_summary.get("total_lint_errors", 0) == 0,
                "summary": analysis_summary,
                "issues": [f"Lint error in {file}" for file in analysis_summary.get("files_with_lint_errors", [])]
            }
        except Exception as e:
            canvas.error(f"[QualityLeadAgent] Error in static analysis: {e}")
            return {
                "passed": False,
                "summary": {"errors": [str(e)]},
                "issues": [f"Static analysis error: {str(e)}"]
            }
    
    async def _run_enterprise_checks(
        self, project_path: Path, modified_files: Dict[str, str], quality_gates: List[str]
    ) -> Dict[str, Any]:
        """Run enterprise quality gate checks"""
        try:
            # Use enterprise_static_analyzer to run quality gates
            enterprise_results = enterprise_static_analyzer.analyze_files(modified_files, quality_gates)
            
            # Extract issues into a flat list for easier processing
            issues = []
            if enterprise_results.get("files_with_issues"):
                for file_path in enterprise_results.get("files_with_issues", []):
                    file_issues = enterprise_results.get("issues", {}).get(file_path, {})
                    for gate, gate_result in file_issues.items():
                        for issue in gate_result.get("issues", []):
                            issues.append(f"[{gate}] {file_path}: {issue}")
            
            return {
                "passed": enterprise_results.get("passed", False),
                "summary": enterprise_results.get("summary", {}),
                "issues": issues,
                "detailed_results": enterprise_results
            }
        except Exception as e:
            canvas.error(f"[QualityLeadAgent] Error in enterprise checks: {e}")
            return {
                "passed": False,
                "summary": {"errors": [str(e)]},
                "issues": [f"Enterprise quality check error: {str(e)}"],
                "detailed_results": {}
            }
    
    async def _run_code_review(self, project_path: Path, modified_files: Dict[str, str]) -> Dict[str, Any]:
        """Run code review"""
        try:
            # Use reviewer_agent to review code
            structured_goal = {"objective": "Ensure code quality", "language": "Python"}  # Simplified
            review_feedback = reviewer_agent.review_code(structured_goal, modified_files)
            
            # Simple check for potential issues in the review
            has_issues = False
            if review_feedback:
                # Look for negative keywords in the review
                negative_keywords = ["fail", "error", "incorrect", "missing", "does not align", "issues"]
                review_lower = review_feedback.lower()
                has_issues = any(keyword in review_lower for keyword in negative_keywords)
            
            return {
                "passed": not has_issues,
                "feedback": review_feedback,
                "issues": [review_feedback] if has_issues else []
            }
        except Exception as e:
            canvas.error(f"[QualityLeadAgent] Error in code review: {e}")
            return {
                "passed": False,
                "feedback": f"Error during code review: {str(e)}",
                "issues": [f"Code review error: {str(e)}"]
            }
    
    async def _run_integration_checks(self, project_path: Path, modified_files: Dict[str, str]) -> Dict[str, Any]:
        """Run integration checks"""
        try:
            # Use integration_checker_agent to check integration
            integration_issues = integration_checker_agent.check_integrations(project_path)
            
            return {
                "passed": len(integration_issues) == 0,
                "issues": integration_issues
            }
        except Exception as e:
            canvas.error(f"[QualityLeadAgent] Error in integration checks: {e}")
            return {
                "passed": False,
                "issues": [f"Integration check error: {str(e)}"]
            }
    
    async def _run_guardrail_checks(
        self, 
        static_analysis_results: Dict[str, Any],
        review_results: Dict[str, Any],
        integration_results: Dict[str, Any],
        enterprise_results: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Run guardrail checks"""
        try:
            # Use guardrail_agent to apply guardrails
            # Additional input for dependency_summary and syntax_check_result
            dependency_summary = []  # Placeholder
            syntax_check_result = (enterprise_results.get("passed", True), "")  # Simplified
            
            # Get review feedback from review results
            review_feedback = review_results.get("feedback")
            
            # Run guardrail evaluation
            decision, reasons = guardrail_agent.evaluate_results(
                static_analysis_results.get("summary"),
                dependency_summary,
                syntax_check_result,
                review_feedback
            )
            
            # Add reasons from enterprise checks if they failed
            if enterprise_results and not enterprise_results.get("passed", True):
                summary = enterprise_results.get("summary", {})
                if summary.get("quality_gates_failed", 0) > 0:
                    failed_gates = summary.get("quality_gates_failed", 0)
                    total_issues = summary.get("total_issues", 0)
                    reasons.append(f"Enterprise quality gates: {failed_gates} gates failed with {total_issues} issues")
            
            return {
                "decision": decision,
                "reasons": reasons
            }
        except Exception as e:
            canvas.error(f"[QualityLeadAgent] Error in guardrail checks: {e}")
            return {
                "decision": "BLOCK",
                "reasons": [f"Guardrail check error: {str(e)}"]
            }

def build_quality_team(session_state=None) -> Team:
    """
    Build the quality team with a lead agent and specialized members.
    
    Args:
        session_state: Optional shared session state dictionary.
        
    Returns:
        Team: Configured quality team
    """
    # Create the Quality lead agent
    quality_lead = QualityLeadAgent()
    
    # Use shared session if provided, else initialize defaults
    session_state = session_state or {"validation_results": None}
    
    # Create the team
    return Team(
        name="QualityTeam",
        members=[quality_lead],
        mode="collaborate",
        model=llm_middle,
        instructions=[
            "You are the Quality Team, responsible for code quality.",
            "Follow the lead of the QualityLead agent, who will coordinate your activities.",
            "Ensure that code changes meet quality standards and adhere to best practices.",
            "Apply enterprise-grade quality gates like flake8, black, mypy, pytest, and bandit for Python code.",
            "Focus on issues that would affect readability, maintainability, or correctness."
        ],
        session_state=session_state
    )