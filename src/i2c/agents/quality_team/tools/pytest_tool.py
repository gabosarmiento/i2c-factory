import subprocess
from pathlib import Path
from typing import Dict, Any, List
import os
from agno.tools import tool

@tool
def run_pytest(file_path: str, collect_coverage: bool = True) -> Dict[str, Any]:
    """
    Run pytest on a Python file or directory.
    
    Args:
        file_path: Path to the Python file or directory to test
        collect_coverage: Whether to collect coverage information
        
    Returns:
        Dict with test results and status
    """
    try:
        cmd = ['pytest', '-v', file_path]
        
        if collect_coverage:
            cmd.extend(['--cov', os.path.dirname(file_path)])
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            check=False  # Don't raise an exception for test failures
        )
        
        # Parse the output to get test results
        output_lines = result.stdout.strip().split('\n')
        
        # Extract summary
        summary = ""
        for line in reversed(output_lines):
            if "failed" in line and "passed" in line:
                summary = line
                break
        
        # Extract coverage if available
        coverage_data = {}
        in_coverage_section = False
        coverage_lines = []
        for line in output_lines:
            if 'TOTAL' in line and '%' in line:
                # This is likely a coverage summary line
                coverage_lines.append(line)
                
            if '----------- coverage:' in line:
                in_coverage_section = True
                continue
                
            if in_coverage_section and line.strip() and not line.startswith("------"):
                if "=" in line:  # End of coverage section
                    in_coverage_section = False
                else:
                    coverage_lines.append(line)
        
        if coverage_lines:
            coverage_data["lines"] = coverage_lines
            # Try to extract the overall percentage
            for line in coverage_lines:
                if 'TOTAL' in line:
                    parts = line.split()
                    for part in parts:
                        if '%' in part:
                            coverage_data["percentage"] = part.strip()
                            break
        
        return {
            "passed": result.returncode == 0,
            "summary": summary,
            "output": result.stdout,
            "coverage": coverage_data,
            "command": "pytest",
            "exit_code": result.returncode
        }
    except Exception as e:
        return {
            "passed": False,
            "summary": f"Error running pytest: {str(e)}",
            "output": str(e),
            "coverage": {},
            "command": "pytest",
            "exit_code": -1
        }