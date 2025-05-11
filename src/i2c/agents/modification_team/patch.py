# src/i2c/agents/modification_team/patch.py
from dataclasses import dataclass

@dataclass
class Patch:
    file_path: str          # repo‑relative path (routers/users.py)
    unified_diff: str          # unified diff (git-style)
    
    # Add a compatibility property
    @property
    def unified_text(self) -> str:
        """Backward compatibility for existing code."""
        return self.unified_diff
