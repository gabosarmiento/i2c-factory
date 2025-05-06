# File: cli/utils/documentation_type_selector.py
import json
from pathlib import Path
from cli.controller import canvas

# Cache document types to avoid repeated disk reads
_DOC_TYPES = None

def _load_doc_types() -> list[dict]:
    """Load document types from JSON configuration"""
    global _DOC_TYPES
    if _DOC_TYPES is None:
        try:
            cfg_path = Path(__file__).parents[1] / "config" / "documentation_types.json"
            if cfg_path.exists():
                _DOC_TYPES = json.loads(cfg_path.read_text())
            else:
                # Fallback if file doesn't exist
                _DOC_TYPES = [
                    {"key": "api_documentation", "label": "API Documentation"},
                    {"key": "tutorial", "label": "Tutorial / Guide"},
                    {"key": "code_examples", "label": "Code Examples"},
                    {"key": "best_practices", "label": "Best Practices"},
                    {"key": "other", "label": "Other"}
                ]
        except Exception as e:
            canvas.warning(f"Error loading document types: {e}")
            # Fallback to default values
            _DOC_TYPES = [
                {"key": "api_documentation", "label": "API Documentation"},
                {"key": "tutorial", "label": "Tutorial / Guide"},
                {"key": "code_examples", "label": "Code Examples"},
                {"key": "best_practices", "label": "Best Practices"},
                {"key": "other", "label": "Other"}
            ]
    return _DOC_TYPES

def get_document_type() -> str:
    """
    Prompt the user to select a documentation type from the configuration.
    Returns the corresponding 'key'.
    """
    types = _load_doc_types()
    
    canvas.info("\nDocument types:")
    for idx, t in enumerate(types, start=1):
        canvas.info(f"{idx}. {t['label']}")
    
    choice = canvas.get_user_input(f"Select document type (1-{len(types)}): ").strip()
    
    try:
        index = int(choice) - 1
        if 0 <= index < len(types):
            return types[index]["key"]
        else:
            canvas.warning(f"Invalid selection '{choice}', defaulting to 'other'.")
            return "other"
    except Exception:
        canvas.warning(f"Invalid selection '{choice}', defaulting to 'other'.")
        return "other"