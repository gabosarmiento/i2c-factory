# src/i2c/agents/quality_team/hooks/__init__.py
# Makes the hooks package available for import

from i2c.agents.quality_team.hooks.validation_tool_hook import validation_tool_hook

__all__ = [
    "validation_tool_hook",
]