# src/i2c/agents/quality_team/quality_team.py

from typing import Dict, Any, List
from pathlib import Path
import asyncio
from builtins import llm_highest, llm_middle

from agno.team import Team
from agno.agent import Agent

# Import existing Quality components
from i2c.agents.quality_team.static_analysis_agent import static_analysis_agent
from i2c.agents.quality_team.reviewer_agent import reviewer_agent
from i2c.agents.quality_team.guardrail_agent import guardrail_agent
from i2c.agents.quality_team.integration_checker_agent import integration_checker_agent

class QualityLeadAgent(Agent):
    """Lead agent for the Quality Team that coordinates quality checks"""
    
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
                "If any quality issues are found, provide clear feedback for correction."
            ],
            **kwargs
        )
        # Initialize team session state if needed
        if self.team_session_state is None:
            self.team_session_state = {}
    
    async def validate_changes(
        self, project_path: Path, modified_files: Dict[str, str], quality_gates: List[str]
    ) -> Dict[str, Any]:
        """
        Validate code changes for quality.
        
        Args:
            project_path: Path to the project directory
            modified_files: Dictionary of modified files (path -> content)
            quality_gates: List of quality gates to check
            
        Returns:
            Dictionary with validation results
        """
        # This function will coordinate the Quality team activities
        try:
            # 1. Static analysis check
            static_analysis_results = await self._run_static_analysis(
                project_path, modified_files, quality_gates
            )
            
            # 2. Code review check
            review_results = await self._run_code_review(
                project_path, modified_files
            )
            
            # 3. Integration check
            integration_results = await self._run_integration_checks(
                project_path, modified_files
            )
            
            # 4. Guardrail check
            guardrail_results = await self._run_guardrail_checks(
                static_analysis_results, review_results, integration_results
            )
            
            # 5. Determine overall pass/fail
            all_passed = guardrail_results.get("decision") == "CONTINUE"
            
            # 6. Collect issues
            issues = []
            issues.extend(static_analysis_results.get("issues", []))
            issues.extend(review_results.get("issues", []))
            issues.extend(integration_results.get("issues", []))
            issues.extend(guardrail_results.get("reasons", []))
            
            # Store results in the team session state
            if self.team_session_state is not None:
                self.team_session_state["validation_results"] = {
                    "passed": all_passed,
                    "static_analysis_results": static_analysis_results,
                    "review_results": review_results,
                    "integration_results": integration_results,
                    "guardrail_results": guardrail_results,
                    "issues": issues
                }
            
            return {
                "passed": all_passed,
                "static_analysis_results": static_analysis_results,
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
    
    async def _run_static_analysis(
        self, project_path: Path, modified_files: Dict[str, str], quality_gates: List[str]
    ) -> Dict[str, Any]:
        """Run static analysis checks"""
        # Use static_analysis_agent to analyze code quality
        # In a real implementation, we'd use static_analysis_agent.get_analysis_summary
        return {
            "passed": True,
            "issues": []
        }
    
    async def _run_code_review(self, project_path: Path, modified_files: Dict[str, str]) -> Dict[str, Any]:
        """Run code review"""
        # Use reviewer_agent to review code
        # In a real implementation, we'd use reviewer_agent.review_code
        return {
            "passed": True,
            "issues": []
        }
    
    async def _run_integration_checks(self, project_path: Path, modified_files: Dict[str, str]) -> Dict[str, Any]:
        """Run integration checks"""
        # Use integration_checker_agent to check integration
        # In a real implementation, we'd use integration_checker_agent.check_integrations
        return {
            "passed": True,
            "issues": []
        }
    
    async def _run_guardrail_checks(
        self, 
        static_analysis_results: Dict[str, Any],
        review_results: Dict[str, Any],
        integration_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run guardrail checks"""
        # Use guardrail_agent to apply guardrails
        # In a real implementation, we'd use guardrail_agent.evaluate_results
        return {
            "decision": "CONTINUE",
            "reasons": []
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
            "Focus on issues that would affect readability, maintainability, or correctness."
        ],
        session_state=session_state
    )
