# /agents/modification_team/static_analysis_tools.py
# Utility functions for running static analysis tools like Ruff and AST parsing.

import subprocess
import tempfile
import os
from pathlib import Path
import ast
import json
from typing import List, Dict, Any

# Import CLI for logging
try:
    from i2c.cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_SA] {msg}")
        def error(self, msg): print(f"[ERROR_SA] {msg}")
        def info(self, msg): print(f"[INFO_SA] {msg}")
    canvas = FallbackCanvas()

# --- Ruff Analysis ---
def run_ruff_checks(code_content: str, file_identifier: str = "snippet") -> Dict[str, Any]:
    """
    Runs Ruff check on a code string using a temporary file.

    Args:
        code_content: The string containing the Python code.
        file_identifier: A name (like relative path) used for logging.

    Returns:
        A dictionary containing 'lint_errors' (list of strings).
        Note: Formatting check removed, as it's less useful as metadata.
              Quality Sentinel agent still performs format check before writing.
    """
    results = {"lint_errors": []} # Simplified results
    ruff_available = False
    try:
        subprocess.run(['ruff', '--version'], capture_output=True, check=True, text=True)
        ruff_available = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        results["lint_errors"].append("Ruff command not found or failed.")
        canvas.warning(f"   [SA] Skipping Ruff checks for {file_identifier}: Ruff not found.")
        return results

    temp_filepath = None
    try:
        temp_dir = Path(tempfile.gettempdir())
        temp_file_obj = tempfile.NamedTemporaryFile(
            mode='w+', suffix=".py", delete=False, encoding='utf-8', dir=temp_dir
        )
        with temp_file_obj as temp_file:
            temp_file.write(code_content)
            temp_filepath = temp_file.name

        # Run Ruff Check (Linting) - Use --format=json for easier parsing
        # Use --select ALL to get all possible issues 
        # Use --exit-zero so it doesn't error out just because issues were found
        check_cmd = ['ruff', 'check', '--select=ALL', '--exit-zero', '--force-exclude', '--no-cache', '--format=json', temp_filepath]
        canvas.info(f"      [SA] Running Ruff check for {file_identifier}...")
        check_result = subprocess.run(check_cmd, capture_output=True, text=True, encoding='utf-8')

        # Parse JSON output
        if check_result.stdout:
            try:
                ruff_output = json.loads(check_result.stdout)
                # Filter out results not pertaining to our temp file if needed (though unlikely with --force-exclude)
                # ruff_output = [item for item in ruff_output if item.get("filename") == temp_filepath]

                for issue in ruff_output:
                    code = issue.get('code', 'UNKNOWN')
                    message = issue.get('message', 'No message')
                    location = f"L{issue.get('location',{}).get('row', '?')}:C{issue.get('location',{}).get('column', '?')}"
                    results["lint_errors"].append(f"{code} ({location}): {message}")

                if results["lint_errors"]:
                     canvas.info(f"      [SA] Ruff check found {len(results['lint_errors'])} issues in {file_identifier}.")

            except json.JSONDecodeError:
                 canvas.warning(f"      [SA] Failed to parse Ruff JSON output for {file_identifier}.")
                 # Fallback: add raw output if parsing fails
                 results["lint_errors"].append(f"Ruff raw output (parse failed): {check_result.stdout[:200]}...")

        # Check stderr for execution errors
        if check_result.returncode != 0 and check_result.stderr:
             error_msg = f"Ruff check command failed: {check_result.stderr.strip()}"
             results["lint_errors"].append(error_msg)
             canvas.error(f"   ❌ [SA] {error_msg}")


    except Exception as e:
        error_msg = f"Error during Ruff execution for {file_identifier}: {e}"
        results["lint_errors"].append(error_msg)
        canvas.error(f"   ❌ [SA] {error_msg}")
    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            try: os.remove(temp_filepath)
            except OSError as rm_err: canvas.warning(f"   [SA] Warning: Could not remove temp file {temp_filepath}: {rm_err}")

    return results

# --- AST Analysis ---
def extract_imports(code_content: str, file_identifier: str = "snippet") -> List[str]:
    """
    Parses Python code using AST to extract top-level import statements.
    """
    imports = set()
    try:
        tree = ast.parse(code_content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Handle 'import x.y.z' -> add 'x'
                    base_module = alias.name.split('.')[0]
                    imports.add(base_module)
            elif isinstance(node, ast.ImportFrom):
                # Handle 'from x.y import z' -> add 'x'
                # Handle 'from . import z' -> skip relative for now or add special marker?
                # Handle 'from .foo import z' -> add '.' or 'foo'? Let's skip relative for simplicity.
                if node.level == 0 and node.module: # Only absolute imports
                     base_module = node.module.split('.')[0]
                     imports.add(base_module)
    except SyntaxError as e:
        canvas.warning(f"   [SA] Skipping import extraction for {file_identifier} due to SyntaxError: {e}")
    except Exception as e:
        canvas.warning(f"   [SA] Error during AST import extraction for {file_identifier}: {e}")
    return sorted(list(imports))

# --- Future Tools ---
# def run_semgrep(code: str, language: str) -> dict: ...
# def analyze_complexity(code: str) -> int: ...

