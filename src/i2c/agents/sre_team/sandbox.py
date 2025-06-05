# /agents/sre_team/sandbox.py
# Enhanced Agent for performing syntax checks and running unit tests inside Docker containers.

import subprocess
import py_compile
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple
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

class SandboxExecutorAgent:
    """
    Enhanced Syntax + Test Runner with Docker container support:
      1) Checks syntax with py_compile (fallback for non-containerized)
      2) Builds Docker containers for isolated testing
      3) Executes tests inside containers matching production environment
      4) Supports multi-language testing (Python, Node.js, Go, Java)
    """
    SKIP_DIRS = {'__pycache__', '.git', '.venv', 'node_modules', 'dist', 'build'}
    
    # Docker image templates for different languages
    DOCKER_IMAGES = {
        'python': 'python:3.11-slim',
        'javascript': 'node:18-alpine',
        'typescript': 'node:18-alpine',
        'go': 'golang:1.21-alpine',
        'java': 'openjdk:17-alpine'
    }
    
    def __init__(self, project_path=None, **kwargs):
        self.project_path = Path(project_path) if project_path else Path(".")
        self.name = "Sandbox"
        canvas.info("🏃 [SandboxExecutorAgent] Initialized (Container-Enhanced Mode).")
        self.docker_available = self._check_docker_availability()
    
    async def run(self) -> Dict[str, Any]:
        """
        AGNO-compatible async run method for SRE team integration.
        Runs tests using Docker containers when available, falls back to local execution.
        """
        try:
            # Detect primary language from project
            language = self._detect_project_language()
            
            # Execute tests using the existing execute method
            success, message = self.execute(self.project_path, language)
            
            return {
                "passed": success,
                "issues": [] if success else [message],
                "container_based": self.docker_available and self._has_docker_configuration(self.project_path),
                "language": language,
                "message": message
            }
        except Exception as e:
            return {
                "passed": False,
                "issues": [f"Sandbox execution failed: {str(e)}"],
                "container_based": False,
                "language": "unknown",
                "message": f"Error: {str(e)}"
            }
    
    def _detect_project_language(self) -> str:
        """Detect the primary language of the project"""
        # Check for Python files
        python_files = list(self.project_path.rglob("*.py"))
        if python_files:
            return "python"
        
        # Check for JavaScript/TypeScript files
        js_files = list(self.project_path.rglob("*.js")) + list(self.project_path.rglob("*.ts")) + list(self.project_path.rglob("*.jsx")) + list(self.project_path.rglob("*.tsx"))
        if js_files:
            return "javascript"
        
        # Check for other languages
        go_files = list(self.project_path.rglob("*.go"))
        if go_files:
            return "go"
        
        java_files = list(self.project_path.rglob("*.java"))
        if java_files:
            return "java"
        
        return "python"  # Default fallback

    def _check_docker_availability(self) -> bool:
        """Check if Docker is available and running"""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Also check if Docker daemon is running
                result = subprocess.run(['docker', 'info'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    canvas.success("   ✅ Docker is available and running.")
                    return True
                else:
                    canvas.warning("   ⚠️ Docker is installed but daemon is not running.")
                    return False
            else:
                canvas.warning("   ⚠️ Docker is not installed or not accessible.")
                return False
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            canvas.warning("   ⚠️ Docker check failed. Falling back to local execution.")
            return False

    def execute(self, project_path: Path, language: str) -> Tuple[bool, str]:
        """
        Runs syntax checks and unit tests, preferring Docker containers when available.
        
        Returns:
            Tuple[bool, str]: (True if all checks passed, Message summary)
        """
        canvas.info(f"🤖 [SandboxExecutorAgent] Running validation in {project_path} ({language})…")
        
        # Check if we have Docker configuration files
        has_docker_config = self._has_docker_configuration(project_path)
        
        if self.docker_available and has_docker_config:
            return self._execute_in_container(project_path, language)
        else:
            canvas.info("   📋 Falling back to local execution mode.")
            return self._execute_locally(project_path, language)

    def _has_docker_configuration(self, project_path: Path) -> bool:
        """Check if project has Docker configuration files"""
        docker_files = [
            project_path / "Dockerfile",
            project_path / "backend" / "Dockerfile", 
            project_path / "frontend" / "Dockerfile",
            project_path / "docker-compose.yml"
        ]
        return any(f.exists() for f in docker_files)

    def _execute_in_container(self, project_path: Path, language: str) -> Tuple[bool, str]:
        """Execute tests inside Docker containers"""
        canvas.info("   🐳 Running tests in Docker containers...")
        
        # Check for docker-compose.yml first (preferred for full-stack apps)
        compose_file = project_path / "docker-compose.yml"
        if compose_file.exists():
            return self._execute_with_docker_compose(project_path)
        else:
            return self._execute_with_dockerfile(project_path, language)

    def _execute_with_docker_compose(self, project_path: Path) -> Tuple[bool, str]:
        """Execute tests using docker-compose"""
        try:
            canvas.info("   📦 Building services with docker-compose...")
            
            # Build all services (try both docker-compose and docker compose)
            try:
                build_result = subprocess.run([
                    'docker', 'compose', 'build', '--no-cache'
                ], cwd=project_path, capture_output=True, text=True, timeout=300)
            except FileNotFoundError:
                build_result = subprocess.run([
                    'docker-compose', 'build', '--no-cache'
                ], cwd=project_path, capture_output=True, text=True, timeout=300)
            
            if build_result.returncode != 0:
                error_msg = f"Docker compose build failed: {build_result.stderr}"
                canvas.error(f"   ❌ {error_msg}")
                return False, error_msg

            canvas.success("   ✅ Docker services built successfully.")
            
            # Run tests for each service
            results = []
            
            # Test backend service
            if self._service_exists_in_compose(project_path, 'backend'):
                backend_success, backend_msg = self._run_service_tests(project_path, 'backend')
                results.append(('backend', backend_success, backend_msg))
            
            # Test frontend service (if applicable)
            if self._service_exists_in_compose(project_path, 'frontend'):
                frontend_success, frontend_msg = self._run_service_tests(project_path, 'frontend')
                results.append(('frontend', frontend_success, frontend_msg))
            
            # Cleanup containers
            self._cleanup_docker_compose(project_path)
            
            # Evaluate overall results
            all_passed = all(success for _, success, _ in results)
            messages = [f"{service}: {msg}" for service, _, msg in results]
            
            if all_passed:
                canvas.success("   ✅ All container tests passed.")
                return True, "Container tests completed successfully. " + "; ".join(messages)
            else:
                failed_services = [service for service, success, _ in results if not success]
                canvas.error(f"   ❌ Container tests failed for: {', '.join(failed_services)}")
                return False, "Container test failures: " + "; ".join(messages)
                
        except subprocess.TimeoutExpired:
            canvas.error("   ❌ Docker compose operation timed out.")
            self._cleanup_docker_compose(project_path)
            return False, "Docker operation timed out."
        except Exception as e:
            canvas.error(f"   ❌ Docker compose execution error: {e}")
            self._cleanup_docker_compose(project_path)
            return False, f"Container execution error: {e}"

    def _service_exists_in_compose(self, project_path: Path, service_name: str) -> bool:
        """Check if a service is defined in docker-compose.yml"""
        try:
            compose_file = project_path / "docker-compose.yml"
            content = compose_file.read_text()
            return f"{service_name}:" in content
        except:
            return False

    def _run_service_tests(self, project_path: Path, service_name: str) -> Tuple[bool, str]:
        """Run tests for a specific service"""
        try:
            canvas.info(f"   🧪 Running tests for {service_name} service...")
            
            # Define test commands for different services
            test_commands = {
                'backend': ['python', '-m', 'pytest', '-v', '--tb=short'],
                'frontend': ['npm', 'test', '--', '--watchAll=false', '--verbose']
            }
            
            command = test_commands.get(service_name, ['echo', 'No test command defined'])
            
            # Run tests in the service container with unique container name
            container_name = f"test-{service_name}-{int(time.time())}"
            try:
                result = subprocess.run([
                    'docker', 'compose', 'run', '--rm', '--name', container_name, service_name
                ] + command, cwd=project_path, capture_output=True, text=True, timeout=120)
            except FileNotFoundError:
                result = subprocess.run([
                    'docker-compose', 'run', '--rm', '--name', container_name, service_name
                ] + command, cwd=project_path, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                canvas.success(f"   ✅ {service_name} tests passed.")
                return True, f"{service_name} tests passed"
            else:
                error_output = result.stderr.strip() or result.stdout.strip()
                canvas.error(f"   ❌ {service_name} tests failed.")
                return False, f"{service_name} tests failed: {error_output[:200]}..."
                
        except subprocess.TimeoutExpired:
            return False, f"{service_name} tests timed out"
        except Exception as e:
            return False, f"{service_name} test error: {str(e)}"

    def _execute_with_dockerfile(self, project_path: Path, language: str) -> Tuple[bool, str]:
        """Execute tests using individual Dockerfile"""
        try:
            # Look for Dockerfile in project root or language-specific directory
            dockerfile_paths = [
                project_path / "Dockerfile",
                project_path / "backend" / "Dockerfile",
                project_path / language / "Dockerfile"
            ]
            
            dockerfile = next((p for p in dockerfile_paths if p.exists()), None)
            if not dockerfile:
                return self._execute_locally(project_path, language)
            
            canvas.info(f"   🐳 Building Docker image from {dockerfile.relative_to(project_path)}...")
            
            # Build Docker image
            image_name = f"sre-test-{language}-{int(time.time())}"
            build_result = subprocess.run([
                'docker', 'build', '-t', image_name, '-f', str(dockerfile), '.'
            ], cwd=dockerfile.parent, capture_output=True, text=True, timeout=300)
            
            if build_result.returncode != 0:
                error_msg = f"Docker build failed: {build_result.stderr}"
                canvas.error(f"   ❌ {error_msg}")
                return False, error_msg
            
            # Run tests in container
            test_success, test_msg = self._run_tests_in_image(image_name, language)
            
            # Cleanup
            self._cleanup_docker_image(image_name)
            
            return test_success, test_msg
            
        except Exception as e:
            canvas.error(f"   ❌ Docker execution error: {e}")
            return False, f"Container execution error: {e}"

    def _run_tests_in_image(self, image_name: str, language: str) -> Tuple[bool, str]:
        """Run tests inside a Docker image"""
        test_commands = {
            'python': ['python', '-m', 'unittest', 'discover', '-v'],
            'javascript': ['npm', 'test'],
            'typescript': ['npm', 'test'],
            'go': ['go', 'test', './...'],
            'java': ['mvn', 'test']
        }
        
        command = test_commands.get(language, ['echo', 'No test command for', language])
        
        try:
            result = subprocess.run([
                'docker', 'run', '--rm', image_name
            ] + command, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                canvas.success(f"   ✅ Container tests passed for {language}.")
                return True, f"Container tests passed for {language}"
            else:
                error_output = result.stderr.strip() or result.stdout.strip()
                canvas.error(f"   ❌ Container tests failed for {language}.")
                return False, f"Container tests failed: {error_output[:200]}..."
                
        except subprocess.TimeoutExpired:
            return False, "Container tests timed out"
        except Exception as e:
            return False, f"Container test error: {str(e)}"

    def _cleanup_docker_compose(self, project_path: Path):
        """Clean up docker-compose resources"""
        try:
            # Stop and remove all containers (try both commands)
            try:
                subprocess.run(['docker', 'compose', 'down', '--volumes', '--remove-orphans'], 
                             cwd=project_path, capture_output=True, timeout=30)
            except FileNotFoundError:
                subprocess.run(['docker-compose', 'down', '--volumes', '--remove-orphans'], 
                             cwd=project_path, capture_output=True, timeout=30)
            # Remove any dangling containers with snippet prefix
            subprocess.run(['docker', 'ps', '-a', '--filter', 'name=snippet-', '-q'], 
                         capture_output=True, timeout=10)
        except:
            pass  # Ignore cleanup errors

    def _cleanup_docker_image(self, image_name: str):
        """Remove Docker image"""
        try:
            subprocess.run(['docker', 'rmi', image_name], 
                         capture_output=True, timeout=30)
        except:
            pass  # Ignore cleanup errors

    def _execute_locally(self, project_path: Path, language: str) -> Tuple[bool, str]:
        """Fallback to local execution (original implementation)"""
        if language.lower() != 'python':
            msg = f"Local syntax/test checks currently only implemented for Python, not {language}."
            canvas.info(f"   ⚪ Skipping: {msg}")
            return True, msg

        # 1. Syntax Check
        syntax_ok, syntax_msg = self._syntax_check(project_path)
        if not syntax_ok:
            return False, f"Syntax check failed:\n{syntax_msg}"

        # 2. Check for Dependencies (Warn only)
        if self._has_dependency_declaration(project_path):
            canvas.warning(
                "   ⚠️ Detected dependency files. "
                "Ensure dependencies are installed if tests require them."
            )

        # 3. Run Unit Tests
        tests_ok, tests_msg = self._run_unit_tests(project_path)
        if not tests_ok:
            return False, f"Unit tests failed:\n{tests_msg}"

        final_msg = "Syntax check passed. " + tests_msg
        canvas.success(f"✅ [SandboxExecutorAgent] {final_msg}")
        return True, final_msg

    def _syntax_check(self, project_path: Path) -> Tuple[bool, str]:
        """Performs py_compile check on all .py files."""
        canvas.info("   ▶️ Performing Syntax Check...")
        py_files = list(project_path.rglob("*.py"))
        if not py_files:
            return True, "No Python files found to check syntax."

        errors: List[str] = []
        passed_count = 0
        checked_count = 0

        for f in py_files:
            relative_parts = set(f.relative_to(project_path).parts)
            if relative_parts & self.SKIP_DIRS:
                continue
            checked_count += 1

            try:
                py_compile.compile(str(f), doraise=True)
                passed_count += 1
            except py_compile.PyCompileError as e:
                ln = getattr(e, "lineno", "?")
                col = getattr(e, "offset", "?")
                err_line = f"{f.relative_to(project_path)} (L{ln}:C{col}): {getattr(e,'msg',e)}"
                errors.append(err_line)
            except Exception as e:
                errors.append(f"{f.relative_to(project_path)}: Error during compile check - {e}")

        if not errors:
            msg = f"Syntax OK for {passed_count}/{checked_count} checked Python file(s)."
            canvas.success(f"   ✅ {msg}")
            return True, msg
        else:
            detail = "\n      - ".join(errors)
            msg = f"Syntax errors found in {len(errors)} of {checked_count} checked file(s):\n      - {detail}"
            canvas.error(f"   ❌ {msg}")
            return False, msg

    def _has_dependency_declaration(self, project_path: Path) -> bool:
        """Checks if common dependency files exist."""
        return any((project_path / n).is_file() for n in ("requirements.txt", "pyproject.toml", "package.json"))

    def _run_unit_tests(self, project_path: Path) -> Tuple[bool, str]:
        """Runs 'python -m unittest discover' in the project directory."""
        canvas.info("   ▶️ Running Unit Tests...")
        test_files = list(project_path.rglob("test*.py"))
        if not test_files:
            msg = "No test files (test*.py) found to run."
            canvas.info(f"   ⚪ {msg}")
            return True, msg

        try:
            command = [
                sys.executable, "-m", "unittest", "discover",
                "-s", ".",
                "-p", "test*.py"
            ]
            canvas.info(f"      Running command: {' '.join(command)}")
            result = subprocess.run(
                command,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
                encoding='utf-8'
            )

            output = result.stderr.strip() or result.stdout.strip()

            if result.returncode == 0:
                if "OK" in output:
                    summary = output.splitlines()[-1]
                    canvas.success(f"   ✅ Unit tests passed. ({summary})")
                    return True, f"All tests passed ({summary})."
                else:
                    canvas.warning(f"   ⚠️ Unit tests finished with exit code 0 but no 'OK' status found.")
                    return True, f"Tests finished without explicit OK status (Exit Code 0)."
            else:
                summary = output.splitlines()[-1] if output else "(No output)"
                canvas.error(f"   ❌ Unit tests failed (Exit Code {result.returncode}). Summary: {summary}")
                return False, f"Test failures occurred. Summary: {summary}"

        except subprocess.TimeoutExpired:
            canvas.error("   ❌ Unit tests timed out after 60 seconds.")
            return False, "Tests timed out."
        except Exception as e:
            canvas.error(f"   ❌ Unexpected error running unit tests: {e}")
            return False, f"Error running tests: {e}"

# Pre-instantiated agent for quick access
sandbox_executor = SandboxExecutorAgent(project_path=Path("."))

# Factory function for dynamic instantiation
def build_sandbox_executor_agent(project_path=None) -> SandboxExecutorAgent:
    return SandboxExecutorAgent(project_path=Path(project_path or "."))