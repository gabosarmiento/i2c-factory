# i2c/workflow/session_manager.py
from typing import Dict, Any, Optional
from pathlib import Path
import time
from datetime import datetime

class WorkflowSessionManager:
    """
    Maintains shared session state between different workflow components.
    Designed to be lightweight and compatible with existing agent patterns.
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now().isoformat()
        self.state = {
            "project_path": None,
            "language": None, 
            "action_type": None,
            "structured_goal": None,
            "code_map": None,
            "analysis_summary": None,
            "timestamp": time.time()
        }
        self.history = []  # Track state changes

    def update_state(self, **kwargs) -> None:
        """Update session state with new values"""
        # Record previous state in history
        self.history.append({
            "timestamp": time.time(),
            "changes": {k: v for k, v in kwargs.items() if k in self.state}
        })
        
        # Update state
        self.state.update(kwargs)
        self.state["timestamp"] = time.time()

    def get_state(self) -> Dict[str, Any]:
        """Get current session state"""
        return self.state
        
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get specific value from state with optional default"""
        return self.state.get(key, default)