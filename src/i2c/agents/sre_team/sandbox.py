# /agents/sre_team/sandbox.py
# Agent for performing syntax checks and running unit tests.
# Refined version based on user suggestion.

import subprocess
import py_compile
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple # Added Tuple

# Import CLI for logging and user input
try:
    from i2c.cli.controller import canvas
except ImportError:
    class FallbackCanvas: # Basic fallback logger
        def warning(self, msg): print(f"[WARN_SANDBOX] {msg}")
        def error(self, msg): print(f"[ERROR_SANDBOX] {msg}")
        def info(self, msg): print(f"[INFO_SANDBOX] {msg}")
        def success(self, msg): print(f"[SUCCESS_SANDBOX] {msg}")
        # get_user_input removed as it's no longer used here
    canvas = FallbackCanvas()

class SandboxExecutorAgent:
    """
    Syntax + Test Runner:
      1) Checks syntax with py_compile.
      2) Warns if requirements.txt/pyproject.toml exist (suggesting manual install).
      3) Executes `python -m unittest discover`.
    """
    SKIP_DIRS = {'__pycache__', '.git', '.venv', 'node_modules'} # Define skip dirs

    def __init__(self):
        print("🏃 [SandboxExecutorAgent] Initialized (Syntax & Test Mode).")

    def execute(self, project_path: Path, language: str) -> Tuple[bool, str]:
        """
        Runs syntax checks and unit tests for the project.

        Returns:
            Tuple[bool, str]: (True if all checks passed, Message summary)
        """
        canvas.info(f"🤖 [SandboxExecutorAgent] Running syntax+tests in {project_path}…")
        if language.lower() != 'python':
            msg = f"Syntax/Test checks currently only implemented for Python, not {language}."
            canvas.info(f"   ⚪ Skipping: {msg}")
            return True, msg # Return True as no checks failed

        # 1. Syntax Check
        syntax_ok, syntax_msg = self._syntax_check(project_path)
        if not syntax_ok:
            # Error already logged by _syntax_check
            return False, f"Syntax check failed:\n{syntax_msg}"

        # 2. Check for Dependencies (Warn only)
        if self._has_dependency_declaration(project_path):
            canvas.warning(
                "   ⚠️ Detected `requirements.txt`/`pyproject.toml`. "
                "Ensure dependencies are installed manually if tests require them."
            )

        # 3. Run Unit Tests
        tests_ok, tests_msg = self._run_unit_tests(project_path)
        if not tests_ok:
            # Error already logged by _run_unit_tests
            return False, f"Unit tests failed or errored:\n{tests_msg}"

        # If both syntax and tests passed
        final_msg = "Syntax check passed. " + tests_msg # Combine success messages
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
            # Skip directories defined in SKIP_DIRS
            relative_parts = set(f.relative_to(project_path).parts)
            if relative_parts & self.SKIP_DIRS:
                continue
            checked_count +=1

            try:
                # Check file size before reading? Optional.
                py_compile.compile(str(f), doraise=True)
                passed_count += 1
            except py_compile.PyCompileError as e:
                ln = getattr(e, "lineno", "?")
                col = getattr(e, "offset", "?") # Try to get column
                err_line = f"{f.relative_to(project_path)} (L{ln}:C{col}): {getattr(e,'msg',e)}"
                errors.append(err_line)
            except Exception as e: # Catch other errors like file read issues
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
        return any((project_path / n).is_file() for n in ("requirements.txt","pyproject.toml"))

    def _run_unit_tests(self, project_path: Path) -> Tuple[bool, str]:
        """Runs 'python -m unittest discover' in the project directory."""
        canvas.info("   ▶️ Running Unit Tests...")
        # Check if any test files exist first
        test_files = list(project_path.rglob("test*.py"))
        if not test_files:
             msg = "No test files (test*.py) found to run."
             canvas.info(f"   ⚪ {msg}")
             return True, msg # No tests to run isn't a failure

        try:
            # Command to discover and run tests starting from project_path
            # -s specifies the start directory
            # -p specifies the pattern for test files
            # Use sys.executable to ensure using the correct python interpreter
            command = [
                sys.executable, "-m", "unittest", "discover",
                "-s", ".", # Discover in current directory
                "-p", "test*.py"         # Pattern for test files
            ]
            canvas.info(f"      Running command: {' '.join(command)}")
            result = subprocess.run(
                command,
                cwd=project_path, # Run from project directory
                capture_output=True,
                text=True,
                timeout=60, # 60 second timeout for tests
                check=False, # Don't raise error on non-zero exit code
                encoding='utf-8'
            )

            # unittest discover often prints failures/errors to stderr
            output = result.stderr.strip() or result.stdout.strip() # Prioritize stderr

            if result.returncode == 0:
                # Check output for "OK" - sometimes tests pass but print warnings to stderr
                if "OK" in output:
                     summary = output.splitlines()[-1] # Get the summary line (e.g., OK, Ran 5 tests...)
                     canvas.success(f"   ✅ Unit tests passed. ({summary})")
                     return True, f"All tests passed ({summary})."
                else:
                     # Tests ran but didn't output "OK" - might be warnings or unusual setup
                     canvas.warning(f"   ⚠️ Unit tests finished with exit code 0 but no 'OK' status found.")
                     canvas.warning(f"      Output:\n{output}")
                     return True, f"Tests finished without explicit OK status (Exit Code 0)." # Consider this success for now
            else:
                # Tests failed or errored
                summary = output.splitlines()[-1] if output else "(No output)" # Get last line if possible
                canvas.error(f"   ❌ Unit tests failed or errored (Exit Code {result.returncode}). Summary: {summary}")
                # canvas.error(f"      Full Output:\n{output}") # Optionally log full output
                return False, f"Test Failures/Errors occurred. Summary: {summary}"

        except subprocess.TimeoutExpired:
            canvas.error("   ❌ Unit tests timed out after 60 seconds.")
            return False, "Tests timed out."
        except Exception as e:
            canvas.error(f"   ❌ Unexpected error running unit tests: {e}")
            return False, f"Error running tests: {e}"

# Instantiate the agent globally <<< CORRECTED >>>
sandbox_executor = SandboxExecutorAgent()
