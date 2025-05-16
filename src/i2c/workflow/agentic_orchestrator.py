from pathlib import Path
from typing import Dict, Any
import os
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

    # Log the constraints
    if "constraints" in objective:
        canvas.info(f"Orchestrator received {len(objective['constraints'])} constraints:")
        for i, constraint in enumerate(objective['constraints']):
            canvas.info(f"  Constraint {i+1}: {constraint}")
    
    # Analyze the current project state
    canvas.info(f"Analyzing project at: {project_path}")
    project_files = []
    for root, dirs, files in os.walk(project_path):
        for file in files:
            if file.endswith(('.py', '.js', '.html', '.css')):
                rel_path = os.path.relpath(os.path.join(root, file), project_path)
                project_files.append(rel_path)
    
    # Add project state to objective
    objective['existing_files'] = project_files
    canvas.info(f"Found {len(project_files)} existing files in project")
    
    # Initialize session state
    initial_session_state = {
        "project_path": str(project_path),
        "objective": objective,
        "reasoning_trajectory": [],
        "start_time": datetime.datetime.now().isoformat(),
        "existing_files": project_files
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

# Add to src/i2c/workflow/agentic_orchestrator.py (if not already there)

def execute_agentic_evolution_sync(objective: Dict[str, Any], project_path: Path) -> Dict[str, Any]:
    """Synchronous wrapper for execute_agentic_evolution."""
    import asyncio
    # Add debug logging for constraints WITH RAISE
    from i2c.cli.controller import canvas
    if "constraints" in objective:
        canvas.info("🔍 CONSTRAINTS RECEIVED IN ORCHESTRATOR:")
        for i, constraint in enumerate(objective["constraints"], 1):
            canvas.info(f"  Constraint {i}: {constraint}")
    else:
        canvas.info("❌ NO CONSTRAINTS FOUND IN OBJECTIVE")
        raise ValueError("HALTING: No constraints found in objective!")
    # Check if we're already running in an event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create a new event loop for this call
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(execute_agentic_evolution(objective, project_path))
            finally:
                new_loop.close()
                asyncio.set_event_loop(loop)
        else:
            # Use the existing loop
            return loop.run_until_complete(execute_agentic_evolution(objective, project_path))
    except RuntimeError:
        # No event loop exists, create one
        return asyncio.run(execute_agentic_evolution(objective, project_path))