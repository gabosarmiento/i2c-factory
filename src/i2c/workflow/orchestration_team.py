# src/i2c/workflow/orchestration_team.py

from agno.team import Team
from i2c.agents.code_orchestration_agent import CodeOrchestrationAgent, OrchestrationResult
from builtins import llm_highest


def build_orchestration_team(initial_session_state=None) -> Team:
    """
    Build the orchestration team with the CodeOrchestrationAgent as the leader.
    
    Args:
        initial_session_state: Initial session state dictionary
        
    Returns:
        Team: Configured orchestration team
    """
    # Use empty dict if no initial state is provided
    if initial_session_state is None:
        initial_session_state = {}
    
    # Create the orchestration agent
    orchestration_agent = CodeOrchestrationAgent(session_state=initial_session_state)
    
    # Create the team with session state
    return Team(
        name="CodeEvolutionTeam",
        members=[orchestration_agent],
        mode="coordinate",
        model=llm_highest,  # Use the most capable model for orchestration
        session_state=initial_session_state,
        instructions=[
            "You are the Code Evolution Team, responsible for safely and intelligently evolving code.",
            "Follow the lead of the CodeOrchestrator.",
            "Your final response **must be strictly valid JSON**.",
            "Do not explain. Do not add text. Do not use Markdown. Output only JSON.",
            "Expected format:",
            "```json",
            '{',
            '  "decision": "approve",',
            '  "reason": "All quality and operational checks passed",',
            '  "modifications": { "sample.py": "Added type hints" },',
            '  "quality_results": { "lint": "passed", "types": "passed", "security": "passed" },',
            '  "sre_results": { "uptime_check": "passed" },',
            '  "reasoning_trajectory": [ { "step": "Final Decision", "description": "All gates passed", "success": true } ]',
            '}',
            "```",
        ],
        response_model=OrchestrationResult,  
        show_tool_calls=True,
        debug_mode=True,
        markdown=True,
        enable_agentic_context=True
    )
