# src/i2c/workflow/modification/code_modifier_adapter.py
"""
Adapter that decides, at runtime, which code‑modification engine to call.

- If a mock is provided → use legacy `ModificationManager` (unit‑test speed).
- Otherwise             → use the new Manager‑orchestrated coordinate team.
"""

from __future__ import annotations

import json
import difflib  # Add this missing import
import traceback
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

from agno.team import Team                       
from i2c.agents.modification_team.patch import Patch

# Optional import for transitional period
try:
    from i2c.agents.modification_team.code_modifier import code_modifier_agent
    _HAS_CODE_MODIFIER = True
except ImportError:
    _HAS_CODE_MODIFIER = False

# Debug mode - set to True during development for more verbose output
DEBUG_MODE = True

# ---------------------------------------------------------------------------
# Lazy cache so we don't rebuild a team for every step
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


def _run_manager_team(modification_step: Dict, project_path: Path, retrieved_context: Optional[str]) -> Union[Patch, Dict]:
    print(f"=== USING NEW CODE MODIFICATION MANAGER SYSTEM ===")
    print(f"Action: {modification_step.get('action')}")
    print(f"File: {modification_step.get('file')}")
    
    if DEBUG_MODE:
        print("=== DETAILED DEBUG INFORMATION ===")
        print(f"Modification step: {modification_step}")
        print(f"Project path: {project_path}")
    
    try:
        team = _ensure_manager_team(project_path)
        manager = team.members[0]  # build_code_modification_team puts Manager first
        
        # Prepare the payload for the manager
        from agno.agent import Message
        payload = json.dumps({
            "modification_step": modification_step,
            "retrieved_context": retrieved_context,
        }, indent=2)
        
        if DEBUG_MODE:
            print(f"Sending payload to manager: {payload[:100]}...")
        
        # Get the response from the manager
        reply = manager.predict([Message(role="user", content=payload)])
        
        if DEBUG_MODE:
            print(f"Got reply from manager: {reply[:100]}...")
        
        # Try to parse as JSON first (preferred format)
        try:
            data = json.loads(reply)
            if isinstance(data, dict) and "file_path" in data and "modified" in data:
                # We have a valid ModPayload JSON
                file_path = data["file_path"]
                modified = data["modified"]
                
                # Create a diff and return a Patch
                original = data.get("original", "")
                diff = "".join(
                    difflib.unified_diff(
                        original.splitlines(keepends=True),
                        modified.splitlines(keepends=True),
                        fromfile=f"{file_path} (original)",
                        tofile=f"{file_path} (modified)",
                        lineterm=""
                    )
                )
                return Patch(file_path=file_path, unified_diff=diff)
            else:
                # JSON was valid but not in the expected format
                return {"error": "Invalid response format", "data": data}
                
        except json.JSONDecodeError:
            # Not valid JSON, try to extract patch section
            try:
                if "## Patch" in reply:
                    patch_section = reply.split("## Patch", 1)[1].strip()
                    if "##" in patch_section:
                        patch_section = patch_section.split("##", 1)[0].strip()
                    
                    file_hint = modification_step.get("file", "unknown.py")
                    return Patch(file_path=file_hint, unified_diff=patch_section)
                else:
                    return {"error": "UNPARSEABLE_MANAGER_REPLY", "raw_reply": reply[:500] if len(reply) > 500 else reply}
            except Exception as parse_error:
                return {"error": f"Failed to extract patch: {parse_error}", "raw_reply": reply[:500] if len(reply) > 500 else reply}
    
    except Exception as e:
        print(f"Error in _run_manager_team: {e}")
        traceback.print_exc()
        return {"error": str(e)}

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
    print("USING NEW CODE MODIFICATION SYSTEM - ADAPTER CALLED")
    
    # A) mock path for tests
    if mock_function_modifier is not None:
        from i2c.agents.modification_team.modification_manager import (
            ModificationManager,
        )

        manager = ModificationManager(project_path, mock_function_modifier)
        return manager.process_modification(modification_step, retrieved_context)

    # B) Try the new system first
    try:
        result = _run_manager_team(modification_step, project_path, retrieved_context)
        if not isinstance(result, dict) or "error" not in result:
            return result
        # New system failed, log the error
        print(f"New system failed: {result.get('error')}")
        
        # If the legacy system isn't available, return the error from the new system
        if not _HAS_CODE_MODIFIER:
            return result
    except Exception as e:
        print(f"New system error: {e}")
        traceback.print_exc()
        
        # If the legacy system isn't available, return the error
        if not _HAS_CODE_MODIFIER:
            return {"error": str(e)}
    
    # C) Fall back to legacy system if available
    if _HAS_CODE_MODIFIER:
        print("Falling back to legacy code modifier...")
        try:
            result = code_modifier_agent.modify_code(modification_step, project_path, retrieved_context)
            if isinstance(result, str):
                # It's a successful string result from the legacy system, wrap it in a Patch
                file_path = modification_step.get('file', 'unknown.py')
                try:
                    # Try to get original content for diff
                    full_path = project_path / file_path
                    original = full_path.read_text(encoding='utf-8') if full_path.exists() else ""
                    
                    # Create a diff
                    diff = "".join(
                        difflib.unified_diff(
                            original.splitlines(keepends=True),
                            result.splitlines(keepends=True),
                            fromfile=f"{file_path} (original)",
                            tofile=f"{file_path} (modified)",
                            lineterm=""
                        )
                    )
                    return Patch(file_path=file_path, unified_diff=diff)
                except Exception as e:
                    print(f"Error creating patch from legacy result: {e}")
                    # Return the legacy result directly - the workflow knows how to handle it
                    return result
            else:
                # It's already some other type, just return it
                return result
        except Exception as e:
            print(f"Legacy system error: {e}")
            traceback.print_exc()
            return {"error": f"Both systems failed. New: earlier error. Legacy: {e}"}
    
    # Should never reach here, but for completeness
    return {"error": "Both systems failed"}


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