import subprocess
from pathlib import Path
from typing import Dict, Any, List
from agno.tools import tool

@tool
def run_eslint(file_path: str) -> Dict[str, Any]:
    """
    Run ESLint on a JavaScript/TypeScript file.
    
    Args:
        file_path: Path to the JS/TS file to check
        
    Returns:
        Dict with linting issues found and status
    """
    try:
        result = subprocess.run(
            ['eslint', '--format', 'json', file_path], 
            capture_output=True, 
            text=True,
            check=False  # Don't raise an exception for linting issues
        )
        
        # Parse the output
        issues = []
        json_output = None
        
        if result.stdout:
            import json
            try:
                json_output = json.loads(result.stdout)
                for file_result in json_output:
                    for msg in file_result.get('messages', []):
                        severity = 'ERROR' if msg.get('severity') == 2 else 'WARNING'
                        issues.append(f"{severity}: {msg.get('message', '')} at line {msg.get('line', 0)}, column {msg.get('column', 0)}")
            except json.JSONDecodeError:
                # If JSON parsing fails, use simple text output
                issues = [line for line in result.stdout.strip().split('\n') if line]
        
        return {
            "passed": result.returncode == 0,
            "issues": issues,
            "command": "eslint",
            "exit_code": result.returncode
        }
    except Exception as e:
        return {
            "passed": False,
            "issues": [f"Error running eslint: {str(e)}"],
            "command": "eslint",
            "exit_code": -1
        }