# /agents/modification_team/context_reader/__init__.py
# Makes context_reader a package and re-exports the agent instance.

from .context_reader_agent import context_reader_agent

__all__ = ["context_reader_agent"]

print("📄 Context Reader Agent Package Initialized.")
