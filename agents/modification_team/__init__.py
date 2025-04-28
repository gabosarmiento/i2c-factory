# /agents/modification_team/__init__.py
# Makes modification_team a package and re-exports agent instances.

from .context_reader import context_reader_agent
from .modification_planner import modification_planner_agent
from .code_modifier import code_modifier_agent

__all__ = [
    "context_reader_agent",
    "modification_planner_agent",
    "code_modifier_agent",
]

print("🛠️  Modification Team Package Initialized and Agents Exported.")
