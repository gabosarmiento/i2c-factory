# src/i2c/agents/sre_team/sre_team.py
# Phase 5: Enhanced Docker-Integrated SRE Pipeline

from typing import Dict, Any, List, Optional
from pathlib import Path
import asyncio
from builtins import llm_highest, llm_middle, llm_middle_alt
from agno.team import Team
from agno.agent import Agent

# Import enhanced SRE components with Docker integration
from i2c.agents.sre_team.code_quality import code_quality_sentinel
from i2c.agents.sre_team.docker import DockerConfigAgent   
from i2c.agents.sre_team.dependency import DependencyVerifierAgent
from i2c.agents.sre_team.sandbox import SandboxExecutorAgent
from i2c.agents.sre_team.version_control import version_controller
from i2c.agents.sre_team.multilang_unit_test import unit_test_generator
# Import CLI for logging and user input
try:
    from i2c.cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_SANDBOX] {msg}")
        def error(self, msg): print(f"[ERROR_SANDBOX] {msg}")
        def info(self, msg): print(f"[INFO_SANDBOX] {msg}")
        def success(self, msg): print(f"[SUCCESS_SANDBOX] {msg}")
    canvas = FallbackCanvas()

class SRELeadAgent(Agent):
    """Enhanced Lead agent for the SRE Team with Docker-integrated operational checks"""
    
    def __init__(self, *, project_path: Path, session_state: dict[str,Any], **kwargs):
        instructions = [
                "You are the lead of the enhanced SRE Team with Docker-integrated operational pipeline.",
                "Your job is to coordinate the complete Docker-aware validation workflow:",
                "1. Generate dependency manifests (requirements.txt, package.json)",
                "2. Generate Docker configurations (Dockerfile, docker-compose.yml)",
                "3. Run container-based testing for production-like validation",
                "4. Execute container-aware security scanning",
                "5. Perform version control readiness checks",
                
                # Docker-specific workflow instructions
                "DOCKER-INTEGRATED WORKFLOW:",
                "- Always generate manifests before Docker configs",
                "- Use container-based testing when Docker configs are available",
                "- Run security scans inside containers to match production environment",
                "- Fallback to local execution only when Docker is unavailable",
                
                # Simple coordination instructions
                "You coordinate the SRE team to ensure deployment readiness.",
                "Work with your team members to:",
                "1. Check if dependency files exist, generate if missing",
                "2. Create Docker configurations for the project architecture",
                "3. Test code changes (prefer Docker, fallback to local)",
                "4. Check for obvious deployment blockers",
                "",
                "Focus on the essentials - can this app be deployed and run via Docker?",
                
                # Enhanced response formatting
                "Return results in this enhanced format:",
                "{",
                "  'passed': boolean,  # Overall operational readiness",
                "  'issues': [string],  # List of operational issues found",
                "  'check_results': {  # Results per operational check",
                "    'manifest_generation': {'passed': boolean, 'files_created': [string], 'issues': [string]},",
                "    'docker_configuration': {'passed': boolean, 'files_created': [string], 'issues': [string]},",
                "    'container_testing': {'passed': boolean, 'issues': [string]},",
                "    'container_security': {'passed': boolean, 'issues': [string]},", 
                "    'version_control': {'passed': boolean, 'issues': [string]}",
                "  },",
                "  'summary': {  # High-level operational summary",
                "    'total_issues': int,",
                "    'deployment_ready': boolean,",
                "    'docker_ready': boolean,",
                "    'operational_score': string",
                "  },",
                "  'docker_pipeline': {  # Docker-specific results",
                "    'manifests_generated': [string],",
                "    'docker_configs_created': [string],",
                "    'container_tests_run': boolean,",
                "    'container_security_scanned': boolean",
                "  }",
                "}"
        ]

        super().__init__(
            name="SRELead",
            model=llm_middle_alt,  
            role="Leads the SRE team to ensure operational excellence with Docker-integrated pipeline",
            instructions=instructions,
            **kwargs
        )   
        self.project_path = Path(project_path)
        self.team_session_state = session_state
        
        # Initialize enhanced Docker-aware agents
        self.docker_agent = DockerConfigAgent(project_path=self.project_path)
        self.dependency_agent = DependencyVerifierAgent(
            project_path=self.project_path, 
            session_state=session_state
        )
        self.sandbox_agent = SandboxExecutorAgent(project_path=self.project_path)
    
    def validate_changes(self, project_path: Path, modified_files: Dict[str, str]) -> Dict[str, Any]:
        """
        Enhanced Docker-integrated validation workflow
        
        Args:
            project_path: Path to the project directory
            modified_files: Dictionary of modified files (path -> content)
            
        Returns:
            Dictionary with comprehensive validation results including Docker pipeline status
        """
        try:
            # Phase 1: Generate dependency manifests
            manifest_results = self._run_manifest_generation(project_path, modified_files)
            
            # Phase 2: Generate Docker configurations  
            docker_config_results = self._run_docker_configuration(project_path, modified_files)
            
            # Phase 3: Container-based testing
            container_test_results = self._run_container_testing(project_path, modified_files)
            
            # Phase 4: Container-aware security scanning
            container_security_results = self._run_container_security_scanning(project_path)
            
            # Phase 5: Version control readiness
            version_control_results = self._run_version_control_checks(project_path)
            
            # Determine overall pass/fail with Docker-specific considerations
            all_passed = (
                manifest_results.get("passed", False) and
                docker_config_results.get("passed", False) and
                container_test_results.get("passed", False) and
                container_security_results.get("passed", False) and
                version_control_results.get("passed", False)
            )
            
            # Collect all issues
            issues = []
            issues.extend(manifest_results.get("issues", []))
            issues.extend(docker_config_results.get("issues", []))
            issues.extend(container_test_results.get("issues", []))
            issues.extend(container_security_results.get("issues", []))
            issues.extend(version_control_results.get("issues", []))
            
            # Build comprehensive check results
            check_results = {
                "manifest_generation": {
                    "passed": manifest_results.get("passed", False),
                    "files_created": manifest_results.get("files_created", []),
                    "issues": manifest_results.get("issues", [])
                },
                "docker_configuration": {
                    "passed": docker_config_results.get("passed", False),
                    "files_created": docker_config_results.get("files_created", []),
                    "issues": docker_config_results.get("issues", [])
                },
                "container_testing": {
                    "passed": container_test_results.get("passed", False),
                    "issues": container_test_results.get("issues", [])
                },
                "container_security": {
                    "passed": container_security_results.get("passed", False), 
                    "issues": container_security_results.get("issues", [])
                },
                "version_control": {
                    "passed": version_control_results.get("passed", False),
                    "issues": version_control_results.get("issues", [])
                }
            }
            
            # Determine Docker readiness
            docker_ready = (
                manifest_results.get("passed", False) and
                docker_config_results.get("passed", False)
            )
            
            # Build enhanced summary
            summary = {
                "total_issues": len(issues),
                "deployment_ready": all_passed,
                "docker_ready": docker_ready,
                "checks_run": len(check_results),
                "operational_score": f"{sum(1 for r in check_results.values() if r['passed'])}/{len(check_results)}"
            }
            
            # Build Docker pipeline status
            docker_pipeline = {
                "manifests_generated": manifest_results.get("files_created", []),
                "docker_configs_created": docker_config_results.get("files_created", []),
                "container_tests_run": container_test_results.get("container_based", False),
                "container_security_scanned": container_security_results.get("container_based", False)
            }
            
            # Store comprehensive results in session state
            if self.team_session_state is not None:
                self.team_session_state["validation_results"] = {
                    "passed": all_passed,
                    "issues": issues,
                    "check_results": check_results,
                    "summary": summary,
                    "docker_pipeline": docker_pipeline
                }
            
            return {
                "passed": all_passed,
                "issues": issues,
                "check_results": check_results,
                "summary": summary,
                "docker_pipeline": docker_pipeline
            }
            
        except Exception as e:
            import traceback
            error_info = {
                "passed": False,
                "error": f"Enhanced SRE pipeline error: {str(e)}",
                "error_details": traceback.format_exc(),
                "issues": [f"SRE validation error: {str(e)}"],
                "check_results": {},
                "summary": {"total_issues": 1, "deployment_ready": False, "docker_ready": False},
                "docker_pipeline": {
                    "manifests_generated": [],
                    "docker_configs_created": [],
                    "container_tests_run": False,
                    "container_security_scanned": False
                }
            }
            
            if self.team_session_state is not None:
                self.team_session_state["validation_results"] = error_info
                
            return error_info

    def _run_manifest_generation(self, project_path: Path, modified_files: Dict[str, str]) -> Dict[str, Any]:
        """Phase 1: Generate dependency manifests based on architectural intelligence"""
        try:
            print("🔄 Phase 1: Generating dependency manifests...")
            
            # Detect architectural context from modified files
            architectural_context = self._analyze_architectural_context(project_path, modified_files)
            
            # Generate manifests using dependency agent
            manifest_result = self.dependency_agent.generate_requirements_manifest(
                project_path, architectural_context
            )
            
            files_created = manifest_result.get("manifests_created", [])
            
            if files_created:
                print(f"   ✅ Generated {len(files_created)} manifest file(s): {', '.join(files_created)}")
                return {
                    "passed": True,
                    "files_created": files_created,
                    "issues": []
                }
            else:
                return {
                    "passed": True,  # Not having manifests isn't necessarily a failure
                    "files_created": [],
                    "issues": ["No manifest files were generated"]
                }
                
        except Exception as e:
            print(f"   ❌ Manifest generation failed: {e}")
            return {
                "passed": False,
                "files_created": [],
                "issues": [f"Manifest generation error: {str(e)}"]
            }

    def _run_docker_configuration(self, project_path: Path, modified_files: Dict[str, str]) -> Dict[str, Any]:
        """Phase 2: Generate Docker configurations"""
        try:
            print("🔄 Phase 2: Generating Docker configurations...")
            
            # Generate Docker configs using docker agent
            docker_result = asyncio.run(self.docker_agent.run())
            
            files_created = docker_result.get("files_created", [])
            
            if docker_result.get("passed", False):
                print(f"   ✅ Generated {len(files_created)} Docker config file(s): {', '.join(files_created)}")
                return {
                    "passed": True,
                    "files_created": files_created,
                    "issues": []
                }
            else:
                return {
                    "passed": False,
                    "files_created": files_created,
                    "issues": docker_result.get("issues", ["Docker configuration generation failed"])
                }
                
        except Exception as e:
            print(f"   ❌ Docker configuration failed: {e}")
            return {
                "passed": False,
                "files_created": [],
                "issues": [f"Docker configuration error: {str(e)}"]
            }

    def _run_container_testing(self, project_path: Path, modified_files: Dict[str, str]) -> Dict[str, Any]:
        """Phase 3: Run container-based testing"""
        try:
            print("🔄 Phase 3: Running container-based testing...")
            
            # Detect primary language
            language = self._detect_primary_language(modified_files)
            
            # Run container-based tests using enhanced sandbox agent
            test_result = asyncio.run(self.sandbox_agent.run())
            
            if test_result.get("passed", False):
                print("   ✅ Container-based tests passed")
                return {
                    "passed": True,
                    "container_based": True,
                    "issues": []
                }
            else:
                issues = test_result.get("issues", ["Container testing failed"])
                print(f"   ❌ Container tests failed: {', '.join(issues)}")
                return {
                    "passed": False,
                    "container_based": True,
                    "issues": [f"Container test: {issue}" for issue in issues]
                }
                
        except Exception as e:
            print(f"   ❌ Container testing error: {e}")
            return {
                "passed": False,
                "container_based": False,
                "issues": [f"Container testing error: {str(e)}"]
            }

    def _run_container_security_scanning(self, project_path: Path) -> Dict[str, Any]:
        """Phase 4: Run container-aware security scanning"""
        try:
            print("🔄 Phase 4: Running container-aware security scanning...")
            
            # Run enhanced dependency security scanning
            security_result = asyncio.run(self.dependency_agent.run())
            
            issues_found = security_result.get("issues", [])
            
            if security_result.get("passed", False):
                print("   ✅ Container security scan passed")
                return {
                    "passed": True,
                    "container_based": True,
                    "issues": []
                }
            else:
                print(f"   ❌ Container security scan found {len(issues_found)} issue(s)")
                return {
                    "passed": False,
                    "container_based": True,
                    "issues": [f"Security: {issue}" for issue in issues_found]
                }
                
        except Exception as e:
            print(f"   ❌ Container security scanning error: {e}")
            return {
                "passed": False,
                "container_based": False,
                "issues": [f"Security scanning error: {str(e)}"]
            }

    def _run_version_control_checks(self, project_path: Path) -> Dict[str, Any]:
        """Phase 5: Version control readiness checks"""
        try:
            print("🔄 Phase 5: Checking version control readiness...")
            
            # Simple git directory check
            git_dir = project_path / ".git"
            
            if not git_dir.exists():
                print("   ⚪ No git repository detected (not blocking)")
                return {
                    "passed": True,  # Not a blocker
                    "issues": [],
                }
            
            print("   ✅ Git repository detected")
            return {
                "passed": True,
                "issues": [],
            }
            
        except Exception as e:
            print(f"   ❌ Version control check error: {e}")
            return {
                "passed": False,
                "issues": [f"Version control error: {str(e)}"],
            }

    def _analyze_architectural_context(self, project_path: Path, modified_files: Dict[str, str]) -> Dict[str, Any]:
        """Analyze project architecture to guide manifest generation"""
        
        # Detect system type based on file structure and content
        has_frontend = any(
            file_path.startswith("frontend/") or file_path.endswith((".jsx", ".js", ".ts", ".tsx"))
            for file_path in modified_files.keys()
        )
        
        has_backend = any(
            file_path.startswith("backend/") or file_path.endswith(".py")
            for file_path in modified_files.keys()
        )
        
        # Determine system type
        if has_frontend and has_backend:
            system_type = "fullstack_web_app"
        elif has_frontend:
            system_type = "frontend_app"
        elif has_backend:
            system_type = "backend_app"
        else:
            system_type = "unknown"
        
        # Build module structure
        modules = {}
        if has_backend:
            modules["backend"] = {
                "languages": ["python"],
                "responsibilities": ["API endpoints", "business logic", "data access"]
            }
        
        if has_frontend:
            modules["frontend"] = {
                "languages": ["javascript", "typescript"],
                "responsibilities": ["user interface", "client-side logic"]
            }
        
        return {
            "system_type": system_type,
            "modules": modules,
            "project_structure": {
                "has_frontend": has_frontend,
                "has_backend": has_backend,
                "files": list(modified_files.keys())
            }
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
            ".jsx": "javascript",
            ".tsx": "typescript",
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


def build_sre_team(
    *,
    project_path: Path | None = None,
    session_state: Dict[str, Any] | None = None
) -> Team:
    """
    Build the enhanced SRE team with Docker-integrated pipeline
    
    Args:
        project_path: Path to the project directory
        session_state: Optional shared session state dictionary
        
    Returns:
        Team: Configured enhanced SRE team with Docker integration
    """
        
    # 0 Extract knowledge_base from session_state (like core_agents does)
    knowledge_base = None
    if session_state and 'knowledge_base' in session_state:
        knowledge_base = session_state['knowledge_base']
        
    # 1) Ensure we have a mutable session_state dict
    if session_state is None:
        session_state = {}
    session_state.setdefault("validation_results", None)

    # 2) Resolve project_path, falling back into session_state if absent
    if project_path is None:
        project_path = Path(session_state.get("project_path", "."))
    else:
        project_path = Path(project_path)
    session_state["project_path"] = str(project_path)

    # 3) Instantiate enhanced Docker-aware members
    members = [
        SRELeadAgent(project_path=project_path, session_state=session_state),
        DockerConfigAgent(project_path=project_path),
        DependencyVerifierAgent(project_path=project_path, session_state=session_state),
        SandboxExecutorAgent(project_path=project_path),
    ]

    # 4) Create the enhanced AGNO Team
    team_instructions = [
            "You are the SRE Team ensuring code changes work and the app is deployment-ready.",
            "",
            "Your mission: Make sure the final app can run via 'docker-compose up'",
            "",
            "Essential workflow:",
            "1. Generate dependency files (requirements.txt, package.json) if missing",
            "2. Create Docker configs (Dockerfile, docker-compose.yml) for the app architecture", 
            "3. Test the code changes work (Docker containers preferred, local fallback)",
            "4. Quick dependency security check",
            "",
            "Key focus:",
            "- Does the app have what it needs to run in Docker?",
            "- Are there any obvious issues that would break deployment?",
            "- Can someone actually use docker-compose to run this app?",
            "",
            "Return: passed (true/false), deployment_ready, docker_ready, and brief summary.",
            "Keep it simple - you're one gear in a larger engine."
    ]
    
    team = Team(
        name="EnhancedSRETeam",
        members=members,
        mode="collaborate",  # lead agent orchestrates
        model=llm_middle,
        knowledge=knowledge_base, 
        instructions=team_instructions,
        session_state=session_state
    )

    # 5) Enhanced synchronous runner for integration tests
    def run_sync() -> Dict[str, Any]:
        """
        Run the complete Docker-integrated SRE pipeline synchronously
        Returns comprehensive validation results including Docker pipeline status
        """
        print("🚀 Starting Enhanced SRE Team Docker-Integrated Pipeline...")
        
        try:
            # Get project path from session state
            project_path = Path(session_state.get("project_path", "."))
            
            # Mock modified files for testing (in real usage, this comes from modification team)
            modified_files = {
                "main.py": "# Sample Python file",
                "frontend/src/App.jsx": "// Sample React component"
            }
            
            # Run the enhanced SRE lead agent validation
            sre_lead = members[0]  # SRELeadAgent
            result = sre_lead.validate_changes(project_path, modified_files)
            
            print(f"✅ Enhanced SRE Pipeline completed with {result['summary']['operational_score']} operational score")
            
            # Enhanced result with Docker pipeline status
            return {
                "passed": result.get("passed", False),
                "issues": result.get("issues", []),
                "docker_pipeline": result.get("docker_pipeline", {}),
                "summary": result.get("summary", {}),
                "deployment_ready": result.get("summary", {}).get("deployment_ready", False),
                "docker_ready": result.get("summary", {}).get("docker_ready", False)
            }
            
        except Exception as e:
            print(f"❌ Enhanced SRE Pipeline failed: {e}")
            return {
                "passed": False,
                "issues": [f"Pipeline error: {str(e)}"],
                "docker_pipeline": {
                    "manifests_generated": [],
                    "docker_configs_created": [],
                    "container_tests_run": False,
                    "container_security_scanned": False
                },
                "summary": {"deployment_ready": False, "docker_ready": False}
            }

    team.run_sync = run_sync  # monkey-patch enhanced runner onto the Team instance
    return team


# Backwards compatibility function
def build_enhanced_sre_team(project_path: Path = None, session_state: Dict[str, Any] = None) -> Team:
    """
    Backwards compatibility wrapper for build_sre_team
    """
    return build_sre_team(project_path=project_path, session_state=session_state)