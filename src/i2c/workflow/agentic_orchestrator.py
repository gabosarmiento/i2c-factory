from pathlib import Path
from typing import Dict, Any
import asyncio
import datetime
import json
import re
from i2c.utils.json_extraction import extract_json
from agno.team import Team
from agno.agent import Message
        
from i2c.workflow.orchestration_team import build_orchestration_team
from i2c.cli.controller import canvas

async def execute_agentic_evolution(objective: Dict[str, Any], project_path: Path) -> Dict[str, Any]:
    """
    Execute a code evolution task using the agentic orchestration team.

    Args:
        objective: Dictionary containing the evolution objective.
        project_path: Path to the project directory.

    Returns:
        Dictionary with execution results.
    """

    # Add project path to objective
    objective['project_path'] = str(project_path)

    # Initialize session state with key information
    initial_session_state = {
        "project_path": str(project_path),
        "objective": objective,    
        "reasoning_trajectory": [],
        "start_time": datetime.datetime.now().isoformat()
    }

    # Add embedding model if available
    try:
        from i2c.agents.budget_manager import get_budget_manager
        from i2c.workflow.modification.rag_config import get_embed_model, get_rag_table
        
        initial_session_state["embed_model"] = get_embed_model()
        initial_session_state["rag_table"] = get_rag_table()
        initial_session_state["budget_manager"] = get_budget_manager()
        
    except ImportError:
        canvas.warning("Embedding model not available - continuing without RAG capabilities")

    # Build the orchestration team with the initial session state
    canvas.info("Building orchestration team...")
    orchestration_team = build_orchestration_team(initial_session_state)

    # Execute the objective
    canvas.info(f"Executing objective: {objective.get('task', 'No task specified')}")
    result = await orchestration_team.arun(
        message=Message(role="user", content=json.dumps(objective))
    )

    # Unwrap TeamRunResponse.content
    if hasattr(result, "content"):
        content = result.content

        # ✅ Case 1: Already parsed Pydantic model
        if hasattr(content, "dict"):
            return content.dict()

        # ✅ Case 2: Already a dict
        elif isinstance(content, dict):
            return content

        # ✅ Case 3: String with JSON (try to parse it)
        elif isinstance(content, str):
            parsed_content = extract_json(content)
            return parsed_content
        # ❌ Unknown type
        else:
            raise ValueError(f"Unexpected content format: {type(content)}")

    else:
        raise ValueError(f"Unexpected result format: {type(result)}")

def execute_agentic_evolution_sync(objective: Dict[str, Any], project_path: Path) -> Dict[str, Any]:
    """Synchronous wrapper for execute_agentic_evolution."""
    return asyncio.run(execute_agentic_evolution(objective, project_path))

