# /Users/caroco/Gabo-Dev/idea_to_code_factory/src/i2c/workflow/modification/code_modifier_adapter.py

from pathlib import Path
from typing import Dict, Optional, Union
import json 
# Import Patch class
from i2c.agents.modification_team.patch import Patch

def apply_modification(
    modification_step: Dict, 
    project_path: Path,
    retrieved_context: Optional[str] = None
) -> Union[Patch, Dict]:
    from i2c.cli.controller import canvas
    
    # Add diagnostic logging
    canvas.info("=" * 40)
    canvas.info(f"APPLYING MODIFICATION: {modification_step.get('what', 'Unknown')}")
    canvas.info(f"Project path: {project_path}")
    canvas.info(f"RAG context: {len(retrieved_context) if retrieved_context else 0} characters")
    canvas.info("=" * 40)
    
    try:
        # Import the clean architecture team builder
        from i2c.agents.modification_team.code_modification_manager import build_code_modification_team, ManagerAgent
        
        # Get the database and embedding model if available
        db = None
        embed_model = None
        try:
            from i2c.db_utils import get_db_connection
            from i2c.workflow.modification.rag_config import get_embed_model
            
            db = get_db_connection()
            embed_model = get_embed_model()
        except Exception as e:
            canvas.warning(f"Error initializing RAG components: {e}")
        
        # Build the team with RAG components
        team = build_code_modification_team(
            project_path=project_path, 
            db=db,
            embed_model=embed_model
        )
        
        # Get the manager agent (it's the first member of the team)
        manager = team.members[0]
        
        # Update the manager's project path
        manager._project_path = project_path
        
        # Create a properly formatted input message for the manager
        from agno.agent import Message
        
        # Create message with modification step and context
        message_content = {
            "modification_step": modification_step,
            "project_path": str(project_path),
            "retrieved_context": retrieved_context or ""
        }
        
        # Call the manager's predict method directly
        response = manager.predict([Message(role="user", content=json.dumps(message_content))])
        
        # Log the raw response
        canvas.info(f"Manager response length: {len(response) if response else 0}")
        canvas.info(f"Response preview: {response[:200] if response else 'None'}...")
        
        # Process the response
        if not response:
            return {"error": "Manager returned empty response"}
            
        # Try to parse as JSON first
        try:
            result = json.loads(response)
            
            # Extract unified diff
            if "unified_diff" in result:
                # Get the correct file path from the original request
                file_path = modification_step.get("file", result.get("file_path", "unknown.py"))
                
                # Ensure the unified diff is for the correct file
                unified_diff = result["unified_diff"]
                
                # Create patch with the correct file path
                return Patch(
                    file_path=file_path,
                    unified_diff=unified_diff
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
            
        # Fallback to a generic diff
        return Patch(
            file_path=modification_step.get("file", "unknown.py"),
            unified_diff=f"--- {modification_step.get('file', 'unknown.py')} (original)\n+++ {modification_step.get('file', 'unknown.py')} (modified)\n@@ -1,1 +1,1 @@\n-# Original\n+# Modified with: {modification_step.get('what', '')}"
        )
    except Exception as e:
        import traceback
        canvas.error(f"Error in team execution: {e}")
        canvas.error(traceback.format_exc())
        return {"error": f"Team execution error: {e}"}