# /workflow/__init__.py
# Makes 'workflow' a package and exports entry points.

from .session import start_factory_session
from .sre_team_workflow import SRETeamWorkflow # Optional export

__all__ = [
    "start_factory_session",
    "SRETeamWorkflow" # Optional export
    ]

print("🔄 Workflow Package Initialized.")
