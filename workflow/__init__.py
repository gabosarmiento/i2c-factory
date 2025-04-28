# /workflow/__init__.py
# Makes 'workflow' a package and exports the main session entry point.

from .session import run_session as start_factory_session

__all__ = ["start_factory_session"]

print("🔄 Workflow Package Initialized.")
