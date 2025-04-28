# /agents/sre_team/__init__.py
# Makes sre_team a package and re-exports agent instances.

# Existing SRE Agents
from .code_quality import code_quality_sentinel
from .dependency import dependency_verifier
from .unit_test import unit_test_generator
from .sandbox import sandbox_executor
from .version_control import version_controller

# Note: ContextReader, ModificationPlanner, CodeModifier are conceptually
# part of the core modification workflow, not strictly SRE checks.
# Consider moving them to a different package like 'agents/modification_team' later
# if this structure becomes too crowded, but keep them here for now for simplicity.

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

