# /agents/sre_team/sandbox.py
# Agent for performing syntax checks (basic sandbox execution).

import subprocess
import py_compile # <<< Import py_compile >>>
import sys
from pathlib import Path

class SandboxExecutorAgent:
    """
    Attempts to verify the basic syntax and import structure of generated Python code.
    """
    def __init__(self):
        print("🏃 [SandboxExecutorAgent] Initialized (Syntax Check Mode).")
        # Timeout not needed for compile check

    def execute(self, project_path: Path, language: str) -> tuple[bool, str]:
        """
        Performs a syntax check on Python files using py_compile.

        Args:
            project_path: The path to the generated project directory.
            language: The primary language of the project.

        Returns:
            A tuple: (success: bool, message: str describing results).
        """
        print(f"🤖 [SandboxExecutorAgent] Performing syntax check in {project_path}...")

        if language.lower() != 'python':
            msg = f"Syntax check only implemented for Python, not {language}."
            print(f"   ⚪ Skipping: {msg}")
            # Return True because we didn't *fail* the check, just skipped it.
            # Alternatively, return False if non-python should be considered a failure here.
            return True, msg

        # Use rglob to find all python files recursively
        python_files = list(project_path.rglob('*.py'))
        if not python_files:
            msg = "No Python files found in project to check."
            print(f"   ⚪ {msg}")
            return True, msg # No files to check isn't a failure

        errors_found = []
        success_count = 0
        print(f"   ▶️ Checking syntax for {len(python_files)} Python file(s)...")
        for py_file in python_files:
            # Skip files in common hidden/metadata directories
            if any(part.startswith('.') for part in py_file.relative_to(project_path).parts) or \
               "__pycache__" in py_file.relative_to(project_path).parts:
                continue

            relative_path = py_file.relative_to(project_path)
            print(f"      Checking: {relative_path}")
            try:
                # doraise=True makes it raise PyCompileError on failure
                py_compile.compile(str(py_file), doraise=True)
                # print(f"      ✅ Syntax OK: {relative_path}") # Reduce verbosity
                success_count += 1
            except py_compile.PyCompileError as e:
                # Provide more context from the exception if possible
                # Check if lineno is available, otherwise provide msg only
                line_info = f"(Line: {e.lineno})" if hasattr(e, 'lineno') and e.lineno else ""
                error_msg = f"Syntax Error in {relative_path}{line_info}: {e.msg}"
                errors_found.append(error_msg)
                print(f"      ❌ {error_msg}")
            except Exception as e:
                # Catch other potential errors like file encoding issues
                error_msg = f"Error checking {relative_path}: {e}"
                errors_found.append(error_msg)
                print(f"      ❌ {error_msg}")

        if not errors_found:
            msg = f"Syntax check successful for all {success_count} checked Python file(s)."
            print(f"   ✅ {msg}")
            return True, msg
        else:
            # Format error message slightly better
            error_details = "\n      - ".join(errors_found)
            msg = f"Syntax check failed. Errors found in {len(errors_found)} file(s):\n      - {error_details}"
            print(f"   ❌ {msg}")
            return False, msg

# Instantiate the agent for easy import
sandbox_executor = SandboxExecutorAgent()
