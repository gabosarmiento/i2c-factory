# /agents/quality_team/__init__.py
# Makes quality_team a package and exports agent instances.

from .static_analysis_agent import static_analysis_agent
from .reviewer_agent import reviewer_agent
from .guardrail_agent import guardrail_agent # <<< ADDED IMPORT >>>

__all__ = [
    "static_analysis_agent",
    "reviewer_agent",
    "guardrail_agent", # <<< ADDED EXPORT >>>
]

print("⭐ Quality Team Package Initialized and Agents Exported.")
