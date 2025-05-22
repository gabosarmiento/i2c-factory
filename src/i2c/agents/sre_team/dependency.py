# /agents/sre_team/dependency.py
# Agent for checking dependencies using pip-audit.

import subprocess
import json
from pathlib import Path

class DependencyVerifierAgent:
    """
    Checks dependencies listed in requirements.txt for known vulnerabilities using pip-audit.
    """
    def __init__(self):
        print("📦 [DependencyVerifierAgent] Initialized.")
        # Check if pip-audit is accessible
        try:
            subprocess.run(['pip-audit', '--version'], capture_output=True, check=True, text=True)
            print("   ✅ pip-audit executable found.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("   ⚠️ Warning: 'pip-audit' command not found or failed. Dependency checks will be skipped.")
            print("      Please install pip-audit: pip install pip-audit")

    def check_dependencies(self, project_path: Path) -> list[str]:
        """Runs pip-audit on the requirements.txt file within the project path."""
        print("🤖 [DependencyVerifierAgent] Checking dependencies...")
        issues_found = []
        requirements_file = project_path / "requirements.txt"

        # Check prerequisite: pip-audit command
        pip_audit_available = False
        try:
            subprocess.run(['pip-audit', '--version'], capture_output=True, check=True, text=True)
            pip_audit_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            issues_found.append("Skipped: pip-audit command not found or failed.")
            print("   Skipping pip-audit checks.")
            return issues_found

        # Check prerequisite: requirements.txt file exists
        if not requirements_file.is_file():
            print(f"   ⚪ No requirements file found at {requirements_file}. Skipping dependency check.")
            return issues_found # No file, no issues to report from this agent

        print(f"   🔎 Auditing {requirements_file}...")
        # Use -r for requirements file, --local to avoid creating virtual envs (faster but less isolated)
        # Use --json for parseable output, --exit-zero to prevent error on finding vulns
        audit_cmd = ['pip-audit', '-r', str(requirements_file)]

        try:
            # Run in the project directory context for potentially better dependency resolution
            result = subprocess.run(audit_cmd, capture_output=True, text=True, check=False, cwd=project_path, encoding='utf-8')

            # Check for execution errors (non-zero return code AND stderr content)
            if result.returncode != 0 and result.stderr:
                 error_msg = f"pip-audit execution failed: {result.stderr.strip()}"
                 issues_found.append(error_msg)
                 print(f"   ❌ {error_msg}")
                 # Don't parse stdout if the command itself failed
                 return issues_found

            # Parse JSON output for vulnerabilities if execution seemed okay
            try:
                audit_data = json.loads(result.stdout)
                vulnerabilities = audit_data.get("vulnerabilities", [])
                if vulnerabilities:
                    for vuln in vulnerabilities:
                        pkg = vuln.get("name", "Unknown pkg")
                        version = vuln.get("version", "?.?.?")
                        vuln_id = vuln.get("id", "NO_ID")
                        description = vuln.get("description", "No description").split('\n')[0] # Keep it brief
                        issue_msg = f"Vulnerability found: {pkg} ({version}) - ID: {vuln_id} - {description}"
                        issues_found.append(issue_msg)
                        print(f"      🚨 {issue_msg}")
                # Check for dependency resolution errors if the format includes them
                # errors = audit_data.get("errors", []) # Example, check actual schema
                # if errors: ...

            except json.JSONDecodeError:
                # This might happen if pip-audit output wasn't JSON despite the flag (e.g., due to an error message)
                error_msg = "Failed to parse pip-audit JSON output."
                issues_found.append(error_msg)
                print(f"   ❌ {error_msg}")
                # Optionally include raw output snippet for debugging
                # print(f"      Raw output: {result.stdout[:200]}")

        except Exception as e:
            issue_msg = f"Error running pip-audit: {e}"
            issues_found.append(issue_msg)
            print(f"   ❌ {issue_msg}")


        if not issues_found:
            print("✅ [DependencyVerifierAgent] No dependencies issues detected.")
        else:
            print(f"⚠️ [DependencyVerifierAgent] Found {len(issues_found)} dependency issue(s).")
        return issues_found

# Instantiate the agent for easy import
dependency_verifier = DependencyVerifierAgent()
