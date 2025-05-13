import subprocess
from pathlib import Path
from typing import Dict, Any, List
from agno.tools import tool

@tool
def run_mypy(file_path: str) -> Dict[str, Any]:
    """
    Run mypy type checking on a Python file.
    
    Args:
        file_path: Path to the Python file to check
        
    Returns:
        Dict with type issues found and status
    """
    try:
        result = subprocess.run(
            ['mypy', file_path], 
            capture_output=True, 
            text=True,
            check=False  # Don't raise an exception for type errors
        )
        
        # Parse the output
        issues = []
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line:
                    issues.append(line)
        
        # mypy returns 0 if no issues, 1 if issues found
        return {
            "passed": result.returncode == 0,
            "issues": issues,
            "command": "mypy",
            "exit_code": result.returncode
        }
    except Exception as e:
        return {
            "passed": False,
            "issues": [f"Error running mypy: {str(e)}"],
            "command": "mypy",
            "exit_code": -1
        }