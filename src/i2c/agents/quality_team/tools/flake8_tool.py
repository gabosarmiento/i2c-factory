import subprocess
from pathlib import Path
from typing import Dict, Any, List
from agno.tools import tool

@tool
def run_flake8(file_path: str) -> Dict[str, Any]:
    """
    Run flake8 linting on a Python file.
    
    Args:
        file_path: Path to the Python file to check
        
    Returns:
        Dict with issues found and status
    """
    try:
        result = subprocess.run(
            ['flake8', file_path], 
            capture_output=True, 
            text=True,
            check=False  # Don't raise an exception for linting errors
        )
        
        # Parse the output
        issues = []
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line:
                    issues.append(line)
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "command": "flake8",
            "exit_code": result.returncode
        }
    except Exception as e:
        return {
            "passed": False,
            "issues": [f"Error running flake8: {str(e)}"],
            "command": "flake8",
            "exit_code": -1
        }