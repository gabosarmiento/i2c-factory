import subprocess
from typing import Dict, Any
from agno.tools import tool

@tool
def run_govet(file_path: str) -> Dict[str, Any]:
    """
    Run go vet for Go code analysis.
    
    Args:
        file_path: Path to the Go file
        
    Returns:
        Dict with analysis results
    """
    try:
        result = subprocess.run(
            ['go', 'vet', file_path], 
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
            "command": "go vet",
            "exit_code": result.returncode
        }
    except Exception as e:
        return {
            "passed": False,
            "issues": [f"Error running go vet: {str(e)}"],
            "command": "go vet",
            "exit_code": -1
        }