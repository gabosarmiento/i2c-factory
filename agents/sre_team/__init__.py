# /agents/sre_team/__init__.py
# Makes sre_team a package and re-exports agent instances.

from .code_quality import code_quality_sentinel
from .dependency import dependency_verifier
from .unit_test import unit_test_generator
from .sandbox import sandbox_executor
from .version_control import version_controller

# Define what gets imported when using 'from agents.sre_team import *'
# Also useful for introspection and clarity.
__all__ = [
    "code_quality_sentinel",
    "dependency_verifier",
    "unit_test_generator",
    "sandbox_executor",
    "version_controller",
]

print("📦 SRE Team Package Initialized and Agents Exported.")
