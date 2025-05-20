import json
from pathlib import Path
from typing import Any, Dict, Optional

# Import AGNO manager and patch models
from i2c.agents.modification_team.code_modification_manager_agno import (
    AgnoCodeModificationManager,
    ModificationRequest,
    AnalysisResult,
    ModificationPlan,
)

# Create a single manager instance (singleton pattern is optional)
manager = AgnoCodeModificationManager()

def apply_modification(
    modification_step: Dict[str, Any],
    project_path: Path,
    retrieved_context: Optional[str] = None,
) -> Any:
    """
    Adapter function to bridge workflow plan step to AGNO manager.
    Args:
        modification_step: dict with at least 'file' and 'what' keys
        project_path: Path to root of project
        retrieved_context: (Optional) String containing RAG/semantic context for the step
    Returns:
        ModificationPlan object or error dict if failure.
    """
    # Prepare ModificationRequest for AGNO
    user_prompt = json.dumps({
        "file": modification_step.get("file", "unknown.py"),
        "what": modification_step.get("what", ""),
    })
    request = ModificationRequest(
        project_root=str(project_path),
        user_prompt=user_prompt,
        rag_context=retrieved_context
    )
    # You can provide an empty or dummy AnalysisResult for compatibility
    analysis = AnalysisResult(details="")

    try:
        # Call the AGNO manager (core logic)
        plan: ModificationPlan = manager.apply_modification(request, analysis)
        # Unpack diff hints (always JSON-encoded)
        if not plan or not getattr(plan, "diff_hints", None):
            raise ValueError("No diff_hints returned by AGNO modification manager")
        # Optionally, decode and re-check the JSON
        diff_dict = json.loads(plan.diff_hints)
        # For the legacy workflow, you might need to return a dict or custom Patch object.
        # But usually, you can just return the plan for your diff processor.
        class Patch:
            def __init__(self, d):
                self.file_path = d.get("file_path", "")
                self.original = d.get("original", "")
                self.modified = d.get("modified", "")
                # Optionally, provide a unified_diff attribute if needed by code_executor
                # Here just return the modified content (you can implement diffing if required)
                self.unified_diff = self.modified

        return Patch(diff_dict)
    except Exception as e:
        # Error fallback for workflow
        return {"error": str(e)}

