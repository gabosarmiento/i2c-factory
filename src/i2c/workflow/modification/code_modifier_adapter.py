# code_modifier_adapter.py
from pathlib import Path
from typing import Dict, Optional, Union
import json

# Import our new team-based manager
from i2c.agents.modification_team.team_modification_manager import ModificationTeamManager

# Import the Patch class for compatibility
from i2c.agents.modification_team.patch import Patch

# Cache the manager to avoid recreating it for each call
_manager_instance = None

def apply_modification(
    modification_step: Dict, 
    project_path: Path,
    retrieved_context: Optional[str] = None
) -> Union[Patch, Dict]:
    """
    Apply a modification using the team-based approach.
    This function is a drop-in replacement for the old code_modifier_agent.modify_code.
    
    Args:
        modification_step: Dict with modification details
        project_path: Project path
        retrieved_context: Optional RAG context
        
    Returns:
        Patch object or error dict
    """
    global _manager_instance
    
    # Create manager instance if needed
    if _manager_instance is None or _manager_instance.project_path != project_path:
        _manager_instance = ModificationTeamManager(project_path)
    
    # Use the manager to apply the modification
    return _manager_instance.apply_modification(
        modification_step,
        project_path,
        retrieved_context
    )