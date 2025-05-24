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
from i2c.agents.sre_team.multilang_unit_test import unit_test_generator

class SRELeadAgent(Agent):
    """Lead agent for the SRE Team that coordinates operational checks"""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="SRELead",
            model=llm_highest,  
            role="Leads the SRE team to ensure operational excellence",
            instructions=[
                "You are the lead of the SRE Team, responsible for operational checks.",
                "Your job is to coordinate operational validation of code changes.",
                "You must ensure that the code meets operational standards and is safe to deploy.",
                
                # Message parsing instructions
                "You will receive messages in this format:",
                "{",
                "  'instruction': 'Review the proposed code changes for operational risks, performance issues, and deployment readiness.',",
                "  'project_path': '/path/to/project',",
                "  'modified_files': {'file.py': 'content...', 'file2.js': 'content...'}", 
                "}",
                
                # Processing instructions
                "When you receive a message, follow these steps:",
                "1. Identify the project_path and modified_files from the message",
                "2. Detect the programming languages used in the modified files",
                "3. You must call your validate_changes(...) function using the values from the message.",
                "4. Format the response according to the expected structure",
                
                # Operational focus areas
                "Focus on these operational validation areas:",
                "- Syntax validation and test execution (sandbox checks)",
                "- Dependency vulnerability scanning", 
                "- Version control readiness",
                "- Runtime stability and performance risks",
                
                # Resource optimization
                "Be smart about resource usage:",
                "- Only run checks appropriate for the detected languages",
                "- Skip tools that would fail based on missing dependencies",
                "- Prioritize critical operational checks over minor issues",
                
                # Response formatting
                "Return results in this format:",
                "{",
                "  'passed': boolean,  # Overall operational readiness",
                "  'issues': [string],  # List of operational issues found",
                "  'check_results': {  # Results per operational check",
                "    'sandbox': {'passed': boolean, 'issues': [string]},",
                "    'dependencies': {'passed': boolean, 'issues': [string]},", 
                "    'version_control': {'passed': boolean, 'issues': [string]}",
                "  },",
                "  'summary': {  # High-level operational summary",
                "    'total_issues': int,",
                "    'deployment_ready': boolean,",
                "    'operational_score': string",
                "  }",
                "}",
                
                # Detailed process instructions
                "For each validation request:",
                "1. Run sandbox checks for syntax and test execution",
                "2. Check dependencies for security vulnerabilities", 
                "3. Verify version control status and readiness",
                "4. Compile all results and return a structured response",
                "Always return a dictionary as a response, even if validation fails or inputs are incomplete.",
                "If a tool fails, still include it in 'check_results' with 'passed': False and an error message.",
                "If any operational issues are found, provide clear feedback for correction."
            ],
            **kwargs
        )
        # Initialize session state if needed
        if self.team_session_state is None:
            self.team_session_state = {}
    
    def validate_changes(self, project_path: Path, modified_files: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate code changes for operational excellence - SYNCHRONOUS
        
        Args:
            project_path: Path to the project directory
            modified_files: Dictionary of modified files (path -> content)
            
        Returns:
            Dictionary with validation results
        """
        # This function will coordinate the SRE team activities
        try:
            # 1. Sandbox execution check (syntax + tests)
            sandbox_results = self._run_sandbox_checks(project_path, modified_files)
            
            # 2. Dependency vulnerability check
            dependency_results = self._run_dependency_checks(project_path)
            
            # 3. Version control readiness check
            version_control_results = self._run_version_control_checks(project_path)
            
            # 4. Determine overall pass/fail
            all_passed = (
                sandbox_results.get("passed", False) and
                dependency_results.get("passed", False) and
                version_control_results.get("passed", False)
            )
            
            # 5. Collect issues
            issues = []
            issues.extend(sandbox_results.get("issues", []))
            issues.extend(dependency_results.get("issues", []))
            issues.extend(version_control_results.get("issues", []))
            
            # 6. Build check results
            check_results = {
                "sandbox": {
                    "passed": sandbox_results.get("passed", False),
                    "issues": sandbox_results.get("issues", [])
                },
                "dependencies": {
                    "passed": dependency_results.get("passed", False), 
                    "issues": dependency_results.get("issues", [])
                },
                "version_control": {
                    "passed": version_control_results.get("passed", False),
                    "issues": version_control_results.get("issues", [])
                }
            }
            
            # 7. Build summary
            summary = {
                "total_issues": len(issues),
                "deployment_ready": all_passed,
                "checks_run": len(check_results),
                "operational_score": f"{sum(1 for r in check_results.values() if r['passed'])}/{len(check_results)}"
            }
            
            # Store results in the team session state
            if self.team_session_state is not None:
                self.team_session_state["validation_results"] = {
                    "passed": all_passed,
                    "issues": issues,
                    "check_results": check_results,
                    "summary": summary
                }
            
            return {
                "passed": all_passed,
                "issues": issues,
                "check_results": check_results,
                "summary": summary
            }
            
        except Exception as e:
            import traceback
            error_info = {
                "passed": False,
                "error": f"SRE team error: {str(e)}",
                "error_details": traceback.format_exc(),
                "issues": [f"SRE validation error: {str(e)}"],
                "check_results": {},
                "summary": {"total_issues": 1, "deployment_ready": False}
            }
            
            # Store error in the team session state
            if self.team_session_state is not None:
                self.team_session_state["validation_results"] = error_info
                
            return error_info
    
    def _run_sandbox_checks(self, project_path: Path, modified_files: Dict[str, str]) -> Dict[str, Any]:
        """Run sandbox execution checks using sandbox_executor - DIRECT CALL"""
        try:
            # Detect primary language from modified files (use existing method)
            language = self._detect_primary_language(modified_files)
            
            # Direct call to sandbox_executor (no async, no LLM)
            success, message = sandbox_executor.execute(project_path, language)
            
            return {
                "passed": success,
                "issues": [] if success else [f"Sandbox: {message}"],
            }
        except Exception as e:
            return {
                "passed": False,
                "issues": [f"Sandbox error: {str(e)}"],
            }

    def _run_dependency_checks(self, project_path: Path) -> Dict[str, Any]:
        """Run dependency checks using dependency_verifier - DIRECT CALL"""
        try:
            # Direct call to dependency_verifier (no async, no LLM)
            issues_found = dependency_verifier.check_dependencies(project_path)
            
            return {
                "passed": len(issues_found) == 0,
                "issues": [f"Dependency: {issue}" for issue in issues_found],
            }
        except Exception as e:
            return {
                "passed": False,
                "issues": [f"Dependency error: {str(e)}"],
            }

    def _run_version_control_checks(self, project_path: Path) -> Dict[str, Any]:
        """Run version control checks - SIMPLE CHECK"""
        try:
            # Simple git directory check (no LLM calls)
            git_dir = project_path / ".git"
            
            if not git_dir.exists():
                return {
                    "passed": True,  # Not a blocker
                    "issues": [],  # Don't report as issue
                }
            
            return {
                "passed": True,
                "issues": [],
            }
            
        except Exception as e:
            return {
                "passed": False,
                "issues": [f"Version control error: {str(e)}"],
            }
                   
    async def _run_code_quality_checks(self, modified_files: Dict[str, str]) -> Dict[str, Any]:
        """Run code quality checks"""
        # Use code_quality_sentinel to check code quality
        # In a real implementation, we'd use code_quality_sentinel.check_code
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
    if session_state is None:
        session_state = {
            "validation_results": None,
        }
    else:
        # 2️⃣ Add only the keys this team needs (if they are missing)
        session_state.setdefault("validation_results", None)
 
    
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
