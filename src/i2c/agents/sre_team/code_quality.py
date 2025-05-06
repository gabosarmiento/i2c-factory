# /agents/sre_team/code_quality.py
# Agent for checking code quality using Ruff.

import subprocess
import tempfile
import os
from pathlib import Path

class CodeQualitySentinelAgent:
    """
    Runs static analysis (linting, formatting checks) on generated code using Ruff.
    """
    def __init__(self):
        print("🛡️  [CodeQualitySentinelAgent] Initialized.")
        # Check if ruff is accessible
        try:
            subprocess.run(['ruff', '--version'], capture_output=True, check=True, text=True)
            print("   ✅ Ruff executable found.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("   ⚠️ Warning: 'ruff' command not found or failed. Sentinel checks will be skipped.")
            print("      Please install ruff: pip install ruff")


    def check_code(self, code_map: dict[str, str]) -> list[str]:
        """Checks Python code quality using Ruff."""
        print("🤖 [CodeQualitySentinelAgent] Checking code quality...")
        issues_found = []
        ruff_available = False
        try:
            # Check availability again in case PATH changed or installed mid-session
            subprocess.run(['ruff', '--version'], capture_output=True, check=True, text=True)
            ruff_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            issues_found.append("Skipped: Ruff command not found or failed.")
            print("   Skipping Ruff checks.")
            return issues_found

        for file_path, code_content in code_map.items():
            if not file_path.endswith(".py"):
                print(f"   ⚪ Skipping non-Python file: {file_path}")
                continue

            print(f"   🔎 Checking {file_path}...")
            temp_filepath = None
            try:
                # Use a temporary file to run ruff
                temp_dir = Path(tempfile.gettempdir())
                # Ensure the temp file has a .py extension for Ruff
                temp_file_obj = tempfile.NamedTemporaryFile(
                    mode='w+', suffix=".py", delete=False, encoding='utf-8', dir=temp_dir
                )
                with temp_file_obj as temp_file:
                    temp_file.write(code_content)
                    temp_filepath = temp_file.name # Get the path after writing

                # Run Ruff Check (Linting)
                check_cmd = ['ruff', 'check', '--exit-zero', '--force-exclude', '--no-cache', temp_filepath]
                check_result = subprocess.run(check_cmd, capture_output=True, text=True, encoding='utf-8')

                if check_result.stdout:
                    lines = check_result.stdout.strip().split('\n')
                    relevant_issues = [f"{file_path}: {line.split(temp_filepath)[-1].strip()}"
                                       for line in lines if temp_filepath in line]
                    if relevant_issues:
                        issues_found.extend(relevant_issues)
                        print(f"      Lint issues found in {file_path}.")
                    elif lines:
                         issues_found.append(f"{file_path}: Ruff check reported: {lines[0]}")
                         print(f"      General Ruff check output for {file_path}.")

                # Run Ruff Format Check
                format_cmd = ['ruff', 'format', '--check', '--force-exclude', '--no-cache', temp_filepath]
                format_result = subprocess.run(format_cmd, capture_output=True, text=True, encoding='utf-8')

                if format_result.returncode != 0:
                    if format_result.stderr and "would be reformatted" in format_result.stderr:
                         issues_found.append(f"{file_path}: Formatting issues detected (would be reformatted).")
                         print(f"      Formatting issues found in {file_path}.")
                    elif format_result.stdout and "would be reformatted" in format_result.stdout:
                         issues_found.append(f"{file_path}: Formatting issues detected (would be reformatted).")
                         print(f"      Formatting issues found in {file_path}.")
                    elif format_result.stderr:
                         issues_found.append(f"{file_path}: Ruff format check error: {format_result.stderr.strip().splitlines()[0]}")
                         print(f"      Ruff format check error for {file_path}.")

            except Exception as e:
                issue_msg = f"{file_path}: Error during Ruff check - {e}"
                issues_found.append(issue_msg)
                print(f"   ❌ {issue_msg}")
            finally:
                if temp_filepath and os.path.exists(temp_filepath):
                    try:
                        os.remove(temp_filepath)
                    except OSError as rm_err:
                         print(f"   ⚠️ Warning: Could not remove temp file {temp_filepath}: {rm_err}")


        if not issues_found:
            print("✅ [CodeQualitySentinelAgent] No quality issues detected.")
        else:
            print(f"⚠️ [CodeQualitySentinelAgent] Found {len(issues_found)} quality issue(s).")
        return issues_found

# Instantiate the agent for easy import
code_quality_sentinel = CodeQualitySentinelAgent()
