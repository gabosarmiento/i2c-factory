import subprocess
from typing import Dict, Any
from agno.tools import tool

@tool
def run_checkstyle(file_path: str, config_path: str = '/google_checks.xml') -> Dict[str, Any]:
    """
    Run checkstyle for Java code analysis.
    
    Args:
        file_path: Path to the Java file
        config_path: Path to checkstyle config XML
        
    Returns:
        Dict with analysis results
    """
    try:
        result = subprocess.run(
            ['checkstyle', '-c', config_path, file_path], 
            capture_output=True, 
            text=True,
            check=False
        )
        
        # Parse the output
        issues = []
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line and not line.startswith('Starting audit'):
                    issues.append(line)
        if result.stderr:
            for line in result.stderr.strip().split('\n'):
                if line:
                    issues.append(line)
        
        return {
            "passed": result.returncode == 0,
            "issues": issues,
            "command": "checkstyle",
            "config": config_path,
            "exit_code": result.returncode
        }
    except Exception as e:
        return {
            "passed": False,
            "issues": [f"Error running checkstyle: {str(e)}"],
            "command": "checkstyle",
            "config": config_path,
            "exit_code": -1
        }