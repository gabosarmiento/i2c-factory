# src/i2c/workflow/modification/code_modifier_adapter.py
"""
Adapter that decides, at runtime, which code‑modification engine to call.

• If a mock is provided → use legacy `ModificationManager` (unit‑test speed).
• Otherwise             → use the new Manager‑orchestrated coordinate team.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

from agno.team import Team                       
from i2c.agents.modification_team.patch import Patch

# ---------------------------------------------------------------------------
# Lazy cache so we don’t rebuild a team for every step
_team_cache: dict[str, Team] = {}
# ---------------------------------------------------------------------------


def _ensure_manager_team(project_path: Path) -> Team:
    """
    Build (or fetch) the coordinate‑mode team driven by ManagerAgent.
    """
    key = str(project_path.resolve())
    if key not in _team_cache:
        from i2c.agents.modification_team.code_modification_manager import (
            build_code_modification_team,
        )

        _team_cache[key] = build_code_modification_team(project_path)

    return _team_cache[key]


def _run_manager_team(
    modification_step: Dict,
    project_path: Path,
    retrieved_context: Optional[str],
) -> Union[Patch, Dict]:
    """
    Serialize the step (+ optional RAG context), send to Manager team,
    return a `Patch` or error dict.
    """
    # Instantiate the ManagerAgent and call its predict() entrypoint directly
    team = _ensure_manager_team(project_path)
    manager = team.members[0]  # build_code_modification_team puts Manager first
    from agno.agent import Message
    payload = json.dumps({
        "modification_step": modification_step,
        "retrieved_context": retrieved_context,
    }, indent=2)

    # Call the ManagerAgent.predict() directly to get the full reply
    reply = manager.predict([Message(role="user", content=payload)])
 
    # team = _ensure_manager_team(project_path)

    # payload = json.dumps(
    #     {
    #         "modification_step": modification_step,
    #         "retrieved_context": retrieved_context,
    #     },
    #     indent=2,
    # )

    # Leader’s text 
    # response = team.run(payload, stream=False)
    # # Extract the actual string reply from the TeamRunResponse
    # reply = response.content
    # run_iter = team.run(payload, stream=True)
    # first = next(run_iter)
    # reply = first.content

    try:
        diff = reply.split("## Patch", 1)[1].strip().split("\n##", 1)[0]
        return Patch(unified_diff=diff)
    except Exception:
        return {"error": "UNPARSEABLE_MANAGER_REPLY", "raw_reply": reply}


# ---------------------------------------------------------------------------
# Public API – signatures unchanged
# ---------------------------------------------------------------------------


def apply_modification(
    modification_step: Dict,
    project_path: Path,
    retrieved_context: Optional[str] = None,
    mock_function_modifier: Optional[Callable] = None,
) -> Union[Patch, Dict]:
    """Entry‑point the rest of the workflow calls."""
    # A) mock path for tests
    if mock_function_modifier is not None:
        from i2c.agents.modification_team.modification_manager import (
            ModificationManager,
        )

        manager = ModificationManager(project_path, mock_function_modifier)
        return manager.process_modification(modification_step, retrieved_context)

    # B) real path → Manager team
    return _run_manager_team(modification_step, project_path, retrieved_context)


def apply_modification_batch(
    modifications: List[Dict],
    project_path: Path,
    retrieved_context: Optional[str] = None,
    mock_function_modifier: Optional[Callable] = None,
) -> List[Union[Patch, Dict]]:
    """Loop over `apply_modification` for convenience."""
    return [
        apply_modification(step, project_path, retrieved_context, mock_function_modifier)
        for step in modifications
    ]
