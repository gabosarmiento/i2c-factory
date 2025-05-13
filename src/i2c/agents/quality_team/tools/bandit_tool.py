import subprocess
from pathlib import Path
from typing import Dict, Any, List
from agno.tools import tool

@tool
def run_bandit(file_path: str) -> Dict[str, Any]:
    """
    Run bandit security scanner on a Python file or directory.
    
    Args:
        file_path: Path to the Python file or directory to scan
        
    Returns:
        Dict with security issues found and status
    """
    try:
        cmd = ['bandit', '-r', file_path, '-f', 'json']
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            check=False  # Don't raise an exception for security issues
        )
        
        # Parse the output
        issues = []
        json_output = None
        
        # Bandit output might be empty if no issues
        if result.stdout and 'results' in result.stdout:
            import json
            try:
                json_output = json.loads(result.stdout)
                
                # Extract issues by severity
                if 'results' in json_output:
                    # Group by severity
                    by_severity = {
                        'HIGH': [],
                        'MEDIUM': [],
                        'LOW': []
                    }
                    
                    for issue in json_output['results']:
                        severity = issue.get('issue_severity', 'UNKNOWN')
                        if severity in by_severity:
                            by_severity[severity].append({
                                'issue_text': issue.get('issue_text', ''),
                                'filename': issue.get('filename', ''),
                                'line': issue.get('line_number', 0),
                                'test_id': issue.get('test_id', '')
                            })
                        
                        issues.append(f"{severity}: {issue.get('issue_text', '')} in {issue.get('filename', '')}:{issue.get('line_number', 0)}")
                    
                    # Add structured data
                    return {
                        "passed": len(json_output['results']) == 0,
                        "issues": issues,
                        "issues_by_severity": by_severity,
                        "command": "bandit",
                        "exit_code": result.returncode,
                        "metrics": json_output.get('metrics', {})
                    }
            except json.JSONDecodeError:
                # If JSON parsing fails, use simple text output
                issues = [line for line in result.stdout.strip().split('\n') if line]
        elif result.stderr:
            # There might be errors in stderr
            issues = [line for line in result.stderr.strip().split('\n') if line]
        
        # If we couldn't parse JSON output, return a simpler structure
        return {
            "passed": result.returncode == 0,
            "issues": issues,
            "command": "bandit",
            "exit_code": result.returncode
        }
    except Exception as e:
        return {
            "passed": False,
            "issues": [f"Error running bandit: {str(e)}"],
            "command": "bandit",
            "exit_code": -1
        }