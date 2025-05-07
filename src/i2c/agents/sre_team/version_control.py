# /agents/sre_team/version_control.py
# Agent for handling Git version control operations.

import subprocess
import shlex
import textwrap
from pathlib import Path

class VersionControlAgent:
    """Handles basic Git version control operations for the generated project."""
    def __init__(self):
        print("💾 [VersionControlAgent] Initialized.")
        try:
            subprocess.run(['git', '--version'], capture_output=True, check=True, text=True)
            print("   ✅ Git executable found.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("   ⚠️ Warning: 'git' command not found. Version control operations will be skipped.")
            print("      Please install Git and ensure it's in your system PATH.")

    def _run_git_command(self, command: str, cwd: Path) -> tuple[bool, str]:
        """Helper to run Git commands safely."""
        try:
            subprocess.run(['git', '--version'], capture_output=True, check=True, text=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False, "Git command not found."

        print(f"   ⚡ Running: git {command} in {cwd}")
        try:
            # Use shlex.split for safer command parsing
            result = subprocess.run(['git'] + shlex.split(command), cwd=cwd, capture_output=True, text=True, check=False, encoding='utf-8')
            if result.returncode == 0:
                # print(f"      ✅ Success: {result.stdout.strip()}") # Reduce verbosity
                return True, result.stdout.strip()
            else:
                error_output = result.stderr.strip() or result.stdout.strip()
                print(f"      ❌ Git Error (ret={result.returncode}): {error_output}")
                return False, error_output
        except FileNotFoundError:
            print("      ❌ Git Error: 'git' command not found.")
            return False, "'git' command not found."
        except Exception as e:
            print(f"      ❌ Unexpected error running Git command: {e}")
            return False, str(e)

    def initialize_and_commit(self, project_path: Path, commit_message: str = "Initial commit by IdeaFactory"):
        """Initializes a Git repository if needed, adds all files, and commits."""
        print(f"🤖 [VersionControlAgent] Performing Git operations for: {project_path}")
        if not project_path.is_dir():
            print(f"   ❌ Error: Project path '{project_path}' does not exist or is not a directory.")
            return

        git_dir = project_path / ".git"
        if not git_dir.exists():
            print("   -> Initializing Git repository...")
            success, _ = self._run_git_command("init", cwd=project_path)
            if not success:
                print("   ⚠️ Failed to initialize Git repository. Skipping remaining Git operations.")
                return
            else:
                 print("      ✅ Git repository initialized.")
        else:
            print("   -> Git repository already initialized.")

        print("   -> Staging all changes...")
        # Stage all files, including untracked ones. Ignore errors for things like empty dirs.
        success, _ = self._run_git_command("add -A --ignore-errors .", cwd=project_path)
        if not success:
            print("   ⚠️ Warning during staging. Attempting commit anyway.")

        print("   -> Committing changes...")
        # Shorten the commit message to a single, 72-char line
        
        short_msg = textwrap.shorten(commit_message, width=72, placeholder="…")

        print("   -> Committing changes…")
        # Allow empty commits in case only metadata changed
        success, output = self._run_git_command(
            f"commit --allow-empty -m {shlex.quote(short_msg)}",
            cwd=project_path
        )
        if success:
             print("   ✅ Git commit successful.")
        elif "nothing to commit" in output or "no changes added to commit" in output:
             print("   ℹ️ No changes detected to commit.")
        else:
             print("   ⚠️ Failed to commit changes.")
        print("✅ [VersionControlAgent] Git operations finished.")

# Instantiate the agent for easy import
version_controller = VersionControlAgent()
