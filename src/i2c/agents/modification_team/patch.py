# src/i2c/agents/modification_team/patch.py
from dataclasses import dataclass

@dataclass
class Patch:
    file_path: str          # repo‑relative path (routers/users.py)
    diff_text: str          # unified diff (git-style)
