# src/i2c/agents/modification_team/patch.py
from dataclasses import dataclass

@dataclass
class Patch:
    """
    A unified-diff patch for a single file
    (kept exactly as the rest of the pipeline expects).
    """
    file_path: str            # repo-relative path, e.g. "routers/users.py"
    unified_diff: str         # git-style unified diff text

    # ↳ older parts of the codebase still refer to .unified_text
    @property
    def unified_text(self) -> str:      # pragma: no cover
        """Backward-compat shim; identical to `unified_diff`."""
        return self.unified_diff


@dataclass
class ModificationPlan:
    """
    Very small wrapper that AgnoTeamAdapter returns.
    Keeping it here avoids circular imports and
    lets the adapter do `from …patch import ModificationPlan`.
    """
    diff_hints: str           # JSON-encoded dict produced by Agno team
