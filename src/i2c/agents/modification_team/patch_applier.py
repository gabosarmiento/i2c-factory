# src/i2c/agents/modification_team/patch_applier.py
import subprocess
from pathlib import Path
from .patch import Patch

class PatchApplier:
    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()

    def apply_patch(self, patch: Patch) -> None:
        """Apply unified diff via `git apply --cached` then write to wc."""
        patch_file = self.repo_root / ".tmp_patch.diff"
        patch_file.write_text(patch.unified_diff, encoding="utf-8")
        try:
            subprocess.run(["git", "apply", str(patch_file)], check=True, cwd=self.repo_root)
        finally:
            patch_file.unlink(missing_ok=True)
