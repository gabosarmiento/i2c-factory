# /agents/quality_team/__init__.py
# Makes quality_team a package and exports agent instances.

from .guardrail_agent import guardrail_agent
from .integration_checker_agent import integration_checker_agent
from .reviewer_agent import reviewer_agent
from .static_analysis_agent import static_analysis_agent

__all__ = [
    "guardrail_agent",
    "integration_checker_agent",
    "reviewer_agent",
    "static_analysis_agent",
]

# Optional: Log only if the package itself is run directly (less common for __init__)
if __name__ == "__main__":
    print("⭐ Quality Team Package Initialized and Agents Exported.")

