# src/i2c/workflow/modification/code_modifier_adapter.py
"""
Adapter module to provide backward compatibility when migrating from CodeModifierAgent 
to the new SafeFunctionModifier system.

This module exposes functions that match the original API but use the new implementation.
"""

from pathlib import Path
from typing import Dict, Optional, Union, Callable

# Import the new manager
from i2c.agents.modification_team.modification_manager import ModificationManager
from i2c.agents.modification_team.patch import Patch

def apply_modification(
    modification_step: Dict, 
    project_path: Path, 
    retrieved_context: Optional[str] = None,
    mock_function_modifier: Optional[Callable] = None
) -> Union[Patch, Dict]:
    """
    Backward-compatible function to apply a modification.
    Replacement for direct calls to code_modifier_agent.modify_code
    
    Args:
        modification_step: Dict containing modification details
        project_path: Base path of the project
        retrieved_context: Optional RAG context
        mock_function_modifier: Optional mock function for testing
        
    Returns:
        Patch object or error dictionary
    """
    manager = ModificationManager(project_path, mock_function_modifier)
    return manager.process_modification(modification_step, retrieved_context)

def apply_modification_batch(
    modifications: list[Dict], 
    project_path: Path, 
    retrieved_context: Optional[str] = None,
    mock_function_modifier: Optional[Callable] = None
) -> list[Union[Patch, Dict]]:
    """
    Apply multiple modifications in batch.
    
    Args:
        modifications: List of modification step dictionaries
        project_path: Base path of the project
        retrieved_context: Optional RAG context
        mock_function_modifier: Optional mock function for testing
        
    Returns:
        List of Patch objects or error dictionaries
    """
    manager = ModificationManager(project_path, mock_function_modifier)
    results = []
    
    for step in modifications:
        result = manager.process_modification(step, retrieved_context)
        results.append(result)
        
    return results

# Testing utilities

class MockRunResponse:
    """Mock response object to use in tests."""
    def __init__(self, content):
        self.content = content

def create_default_mock_function():
    """
    Create a default mock function for testing.

    Returns:
        A function that can be used as mock_function_modifier in tests
    """
    def mock_function(prompt):
        """
        Default mock implementation that generates simple function responses.
        """
        import re
        # Extract function name from prompt
        function_name_match = re.search(r'def\s+(\w+)', prompt)
        function_name = function_name_match.group(1) if function_name_match else "unknown_function"

        # Generate a simple response
        if "add" in prompt.lower() or "create" in prompt.lower():
            return MockRunResponse(f"""```python
def {function_name}(a, b):
    \"\"\"Test function created by mock.\"\"\"
    return a + b
```""")
        elif "modify" in prompt.lower() or "update" in prompt.lower():
            return MockRunResponse(f"""```python
def {function_name}(a, b=None):
    \"\"\"Test function modified by mock.\"\"\"
    if b is None:
        return a
    return a + b
```""")
        else:
            return MockRunResponse(f"""```python
def {function_name}(x):
    \"\"\"Default test function from mock.\"\"\"
    return x
```""")

    return mock_function
