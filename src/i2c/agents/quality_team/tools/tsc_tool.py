import subprocess
from typing import Dict, Any
from agno.tools import tool

@tool
def run_tsc(file_path: str) -> Dict[str, Any]:
    """
    Run TypeScript compiler (tsc) for type checking.
    
    Args:
        file_path: Path to the TypeScript file
        
    Returns:
        Dict with type checking results
    """
    try:
        result = subprocess.run(
            ['tsc', '--noEmit', file_path], 
            capture_output=True, 
            text=True,
            check=False
        )
        
        # Parse the output
        issues = []
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line:
                    issues.append(line)
        if result.stderr:
            for line in result.stderr.strip().split('\n'):
                if line:
                    issues.append(line)
        
        return {
            "passed": result.returncode == 0,
            "issues": issues,
            "command": "tsc",
            "exit_code": result.returncode
        }
    except Exception as e:
        return {
            "passed": False,
            "issues": [f"Error running tsc: {str(e)}"],
            "command": "tsc",
            "exit_code": -1
        }