# src/i2c/agents/sre_team/sre_team.py

from typing import Dict, Any, List, Optional
from pathlib import Path
import asyncio
from builtins import llm_highest, llm_middle
from agno.team import Team
from agno.agent import Agent

# Import existing SRE components
from i2c.agents.sre_team.code_quality import code_quality_sentinel
from i2c.agents.sre_team.dependency import dependency_verifier
from i2c.agents.sre_team.sandbox import sandbox_executor
from i2c.agents.sre_team.version_control import version_controller
from i2c.agents.sre_team.unit_test import unit_test_generator

class SRELeadAgent(Agent):
    """Lead agent for the SRE Team that coordinates operational checks"""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="SRELead",
            model=llm_middle,  # Using OpenAI's GPT-4o as high-tier LLM
            role="Leads the SRE team to ensure operational excellence",
            instructions=[
                "You are the lead of the SRE Team, responsible for operational checks.",
                "Your job is to coordinate operational validation of code changes.",
                "You must ensure that the code meets operational standards and is safe to deploy.",
                "Work with your team to check code quality, dependencies, and execute tests.",
                "If any issues are found, provide clear feedback for correction."
            ],
            **kwargs
        )
        # Initialize session state if needed
        if self.team_session_state is None:
            self.team_session_state = {}
    
    async def validate_changes(self, project_path: Path, modified_files: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate code changes for operational excellence.
        
        Args:
            project_path: Path to the project directory
            modified_files: Dictionary of modified files (path -> content)
            
        Returns:
            Dictionary with validation results
        """
        # This function will coordinate the SRE team activities
        try:
            # 1. Sandbox execution check
            sandbox_results = await self._run_sandbox_checks(project_path, modified_files)
            
            # 2. Code quality check
            quality_results = await self._run_code_quality_checks(modified_files)
            
            # 3. Dependency check
            dependency_results = await self._run_dependency_checks(project_path)
            
            # 4. Unit test check 
            test_results = await self._run_unit_tests(project_path, modified_files)
            
            # 5. Determine overall pass/fail
            all_passed = (
                sandbox_results.get("passed", False) and
                quality_results.get("passed", False) and
                dependency_results.get("passed", False) and
                test_results.get("passed", False)
            )
            
            # 6. Collect issues
            issues = []
            issues.extend(sandbox_results.get("issues", []))
            issues.extend(quality_results.get("issues", []))
            issues.extend(dependency_results.get("issues", []))
            issues.extend(test_results.get("issues", []))
            
            # Store results in the team session state
            if self.team_session_state is not None:
                self.team_session_state["validation_results"] = {
                    "passed": all_passed,
                    "sandbox_results": sandbox_results,
                    "quality_results": quality_results,
                    "dependency_results": dependency_results,
                    "test_results": test_results,
                    "issues": issues
                }
            
            return {
                "passed": all_passed,
                "sandbox_results": sandbox_results,
                "quality_results": quality_results,
                "dependency_results": dependency_results,
                "test_results": test_results,
                "issues": issues
            }
            
        except Exception as e:
            import traceback
            error_info = {
                "passed": False,
                "error": f"SRE team error: {str(e)}",
                "error_details": traceback.format_exc(),
                "issues": [f"SRE validation error: {str(e)}"]
            }
            
            # Store error in the team session state
            if self.team_session_state is not None:
                self.team_session_state["validation_results"] = error_info
                
            return error_info
    
    async def _run_sandbox_checks(self, project_path: Path, modified_files: Dict[str, str]) -> Dict[str, Any]:
        """Run sandbox execution checks"""
        # Use sandbox_executor to check syntax and run tests
        language = self._detect_primary_language(modified_files)
        
        # Write modified files to a temporary sandbox
        # This is a placeholder - in a real implementation, we'd use a proper sandbox
        sandbox_dir = project_path
        
        # Run sandbox checks
        # In a real implementation, we'd use sandbox_executor.execute
        return {
            "passed": True,
            "issues": []
        }
    
    async def _run_code_quality_checks(self, modified_files: Dict[str, str]) -> Dict[str, Any]:
        """Run code quality checks"""
        # Use code_quality_sentinel to check code quality
        # In a real implementation, we'd use code_quality_sentinel.check_code
        return {
            "passed": True,
            "issues": []
        }
    
    async def _run_dependency_checks(self, project_path: Path) -> Dict[str, Any]:
        """Run dependency checks"""
        # Use dependency_verifier to check dependencies
        # In a real implementation, we'd use dependency_verifier.check_dependencies
        return {
            "passed": True,
            "issues": []
        }
    
    async def _run_unit_tests(self, project_path: Path, modified_files: Dict[str, str]) -> Dict[str, Any]:
        """Run unit tests"""
        # Use unit_test_generator to generate and run tests
        # In a real implementation, we'd use unit_test_generator.generate_tests
        return {
            "passed": True,
            "issues": []
        }
    
    def _detect_primary_language(self, modified_files: Dict[str, str]) -> str:
        """Detect the primary language of the modified files"""
        extensions = {}
        for file_path in modified_files:
            ext = Path(file_path).suffix
            if ext:
                extensions[ext] = extensions.get(ext, 0) + 1
        
        if not extensions:
            return "unknown"
        
        # Find the most common extension
        most_common_ext = max(extensions.items(), key=lambda x: x[1])[0]
        
        # Map to language
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".cpp": "c++",
            ".c": "c",
            ".rb": "ruby",
            ".go": "go",
            ".rs": "rust",
            ".php": "php",
            ".cs": "csharp",
        }
        
        return language_map.get(most_common_ext, "unknown")

def build_sre_team(session_state=None) -> Team:
    """
    Build the SRE team with a lead agent and specialized members.
    
    Args:
        session_state: Optional shared session state dictionary.
        
    Returns:
        Team: Configured SRE team
    """
    # Create the SRE lead agent
    sre_lead = SRELeadAgent()
    
    # Use shared session if provided, else initialize defaults
    session_state = session_state or {"validation_results": None}
    
    # Create the team
    return Team(
        name="SRETeam",
        members=[sre_lead],
        mode="collaborate",
        model=llm_middle,
        instructions=[
            "You are the SRE Team, responsible for operational excellence.",
            "Follow the lead of the SRELead agent, who will coordinate your activities.",
            "Ensure that code changes meet operational standards and are safe to deploy.",
            "Focus on issues that would affect stability, performance, or security in production."
        ],
        session_state=session_state
    )
