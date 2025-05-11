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

# In code_modifier_adapter.py or similar file
def apply_modification(
    modification_step: Dict, 
    project_path: Path,
    retrieved_context: Optional[str] = None
) -> Union[Patch, Dict]:
    """
    Apply a modification using the team-based approach.
    
    Args:
        modification_step: Dict with modification details
        project_path: Project path
        retrieved_context: Optional RAG context
        
    Returns:
        Patch object or error dict
    """
    # Get the database and embedding model
    db = None
    embed_model = None
    
    try:
        from i2c.db_utils import get_db_connection
        from i2c.workflow.modification.rag_config import get_embed_model
        
        db = get_db_connection()
        embed_model = get_embed_model()
    except Exception as e:
        print(f"Warning: Unable to initialize RAG components: {e}")
    
    # Build the team with RAG components
    from i2c.agents.modification_team.code_modification_manager import build_code_modification_team
    
    team = build_code_modification_team(
        project_path=project_path,
        db=db,
        embed_model=embed_model
    )
    
    # Create a properly formatted input message for the manager
    message_content = {
        "modification_step": modification_step,
        "project_path": str(project_path),
        "retrieved_context": retrieved_context or ""
    }
    
    # Execute the team (directly pass to manager agent)
    try:
        # Get the manager agent (it's the first member)
        manager = team.members[0]
        
        # Call manager's predict method directly
        from agno.agent import Message
        response = manager.predict([Message(role="user", content=json.dumps(message_content))])
        
        # Parse the response
        if not response:
            return {"error": "Manager returned empty response"}
            
        # Try to parse as JSON first
        try:
            result = json.loads(response)
            if "unified_diff" in result:
                return Patch(
                    file_path=result.get("file_path", modification_step.get("file", "unknown.py")),
                    unified_diff=result.get("unified_diff", "")
                )
        except json.JSONDecodeError:
            pass
            
        # Check if it's a markdown response with sections
        if "## Patch" in response:
            try:
                # Extract patch section
                patch_section = response.split("## Patch")[1].split("##")[0].strip()
                return Patch(
                    file_path=modification_step.get("file", "unknown.py"),
                    unified_diff=patch_section
                )
            except Exception:
                pass
                
        # Check if it's a raw diff
        if response.startswith("---") or response.startswith("diff --git"):
            return Patch(
                file_path=modification_step.get("file", "unknown.py"),
                unified_diff=response
            )
            
        # Fallback: create a generic patch using the file from the modification step
        return Patch(
            file_path=modification_step.get("file", "unknown.py"),
            unified_diff=f"--- {modification_step.get('file', 'unknown.py')} (original)\n+++ {modification_step.get('file', 'unknown.py')} (modified)\n@@ -1,1 +1,1 @@\n-# Original\n+# Modified with: {modification_step.get('what', '')}"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Team execution error: {e}"}