
from pathlib import Path
from typing import Dict, Any, Optional
import os
import asyncio
import datetime
import json
from i2c.utils.json_extraction import extract_json
from agno.team import Team
from agno.agent import Message
from i2c.workflow.orchestration_team import build_orchestration_team
from i2c.cli.controller import canvas


def is_json_like_string(s: str) -> bool:
    s = s.strip()
    return s.startswith("{") and s.endswith("}")


async def execute_agentic_evolution(
    objective: Dict[str, Any],
    project_path: Path,
    session_state: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Orchestrate an agentic evolution run with proper async handling of intermediate states.

    :param objective: The dictionary describing task, constraints, and metadata.
    :param project_path: Path to the current project directory.
    :param session_state: Optional initial session state passed through runs.
    :returns: Final parsed JSON response from the agent team.
    """
    # Prepare or initialize session state
    if session_state is None:
        session_state = {
            "project_path": str(project_path),
            "objective": objective,
            "reasoning_trajectory": [],
            "start_time": datetime.datetime.now().isoformat(),
            "existing_files": os.listdir(project_path)
        }

    # Build or retrieve the orchestration team with state
    team_input = {"objective": objective, "session_state": session_state}
    team: Team = build_orchestration_team(team_input)

    # Kick off the async run, passing both objective and state
    message = Message(role="user", content=json.dumps(team_input))
    result = await team.arun(message=message)

    # Loop until we get a terminal event (no longer paused/intermediate)
    intermediate_events = {"run_paused", "waiting", "intermediate"}
    while getattr(result, "event", None) in intermediate_events:
        canvas.info(f"Waiting on agentic evolution, current state: {result.event}")
        await asyncio.sleep(1)
        # Resume or fetch next result
        if hasattr(team, "resume_run"):
            result = await team.resume_run(result.run_id)
        else:
            result = await team.get_next_result(result.run_id)

    # Once final, parse the content safely
    content = getattr(result, "content", None)
    if hasattr(content, "dict"):
        return {
            "result": content.dict(),
            "session_state": session_state
        }
    elif isinstance(content, dict):
        return {
            "result": content,
            "session_state": session_state
        }
    elif isinstance(content, str):
        if is_json_like_string(content):
            try:
                return {
                    "result": json.loads(content),
                    "session_state": session_state
                }
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON from string: {e}")
        else:
            raise ValueError(f"String content received but not valid JSON: {content[:80]}")
    else:
        raise ValueError(f"Unexpected content format: {type(content)}")


def execute_agentic_evolution_sync(
    objective: Dict[str, Any],
    project_path: Path,
    session_state: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Synchronous wrapper for execute_agentic_evolution. Runs the async function to completion.

    :param objective: The dictionary describing task, constraints, and metadata.
    :param project_path: Path to the current project directory.
    :param session_state: Optional initial session state passed through runs.
    :returns: Final parsed JSON response from the agent team.
    """
    return asyncio.get_event_loop().run_until_complete(
        execute_agentic_evolution(objective, project_path, session_state)
    )
