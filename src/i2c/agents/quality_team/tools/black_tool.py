import subprocess
from pathlib import Path
from typing import Dict, Any, List
from agno.tools import tool

@tool
def run_black(file_path: str, check_only: bool = True) -> Dict[str, Any]:
    """
    Run black formatter on a Python file.
    
    Args:
        file_path: Path to the Python file to format
        check_only: If True, only check formatting without modifying the file
        
    Returns:
        Dict with formatting diff and status
    """
    try:
        cmd = ['black', '--quiet']
        
        if check_only:
            cmd.append('--diff')
            cmd.append('--check')
        
        cmd.append(file_path)
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            check=False  # Don't raise an exception for formatting issues
        )
        
        # Parse the output
        if check_only:
            # In check mode, a non-zero exit code means formatting differences
            formatted_correctly = result.returncode == 0
            diff = result.stdout.strip() if result.stdout else ""
            
            # If no diff is provided but exit code is not 0, there was an error
            if not diff and result.returncode != 0:
                diff = result.stderr.strip()
        else:
            # In reformat mode, success means the file was reformatted or already correct
            formatted_correctly = result.returncode == 0
            diff = "File reformatted" if result.returncode == 0 else result.stderr.strip()
        
        return {
            "passed": formatted_correctly,
            "diff": diff,
            "command": "black",
            "check_only": check_only,
            "exit_code": result.returncode
        }
    except Exception as e:
        return {
            "passed": False,
            "diff": f"Error running black: {str(e)}",
            "command": "black",
            "check_only": check_only,
            "exit_code": -1
        }