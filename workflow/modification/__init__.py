# /workflow/modification/__init__.py
# Makes 'modification' a package and exports the main cycle executor.

from .execute_cycle import execute_modification_cycle

__all__ = ["execute_modification_cycle"]

print("🔄 Modification Workflow Package Initialized.")

