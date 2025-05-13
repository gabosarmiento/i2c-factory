# src/i2c/agents/quality_team/tools/tool_utils.py

import subprocess
from typing import Dict, Any, List, Optional, Callable
import os
from pathlib import Path

def execute_command(
    cmd: List[str], 
    file_path: str, 
    tool_name: str,
    parse_output: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Execute a command and return results in a standardized format.
    
    Args:
        cmd: Command to execute (as list)
        file_path: Path to the file being checked
        tool_name: Name of the tool being run
        parse_output: Optional function to parse the output
        
    Returns:
        Dict with standardized results
    """
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            check=False  # Don't raise an exception for tool errors
        )
        
        # Parse output (default parsing if none provided)
        issues = []
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line:
                    issues.append(line)
        if result.stderr:
            for line in result.stderr.strip().split('\n'):
                if line:
                    issues.append(line)
        
        # Apply custom parsing if provided
        if parse_output:
            parsed_result = parse_output(result, issues)
            if parsed_result:
                return parsed_result
        
        # Return standard format
        return {
            "passed": result.returncode == 0,
            "issues": issues,
            "command": " ".join(cmd),
            "exit_code": result.returncode
        }
    except Exception as e:
        return {
            "passed": False,
            "issues": [f"Error running {tool_name}: {str(e)}"],
            "command": " ".join(cmd) if isinstance(cmd, list) else str(cmd),
            "exit_code": -1
        }

# Define actual tool functions without decorators

def run_flake8(file_path: str) -> Dict[str, Any]:
    """Run flake8 linting on a Python file."""
    return execute_command(['flake8', file_path], file_path, "flake8")

def run_black(file_path: str, check_only: bool = True) -> Dict[str, Any]:
    """Run black formatter on a Python file."""
    cmd = ['black', '--quiet']
    if check_only:
        cmd.append('--diff')
        cmd.append('--check')
    cmd.append(file_path)
    
    def parse_black_output(result, issues):
        formatted_correctly = result.returncode == 0
        diff = result.stdout.strip() if result.stdout else ""
        if not diff and result.returncode != 0:
            diff = result.stderr.strip()
        
        return {
            "passed": formatted_correctly,
            "diff": diff,
            "issues": issues if not formatted_correctly else [],
            "command": " ".join(cmd),
            "check_only": check_only,
            "exit_code": result.returncode
        }
    
    return execute_command(cmd, file_path, "black", parse_black_output)

def run_mypy(file_path: str) -> Dict[str, Any]:
    """Run mypy type checking on a Python file."""
    return execute_command(['mypy', file_path], file_path, "mypy")

def run_pytest(file_path: str, collect_coverage: bool = True) -> Dict[str, Any]:
    """Run pytest on a Python file or directory."""
    cmd = ['pytest', '-v', file_path]
    if collect_coverage:
        cmd.extend(['--cov', os.path.dirname(file_path)])
    
    def parse_pytest_output(result, issues):
        # Extract summary and coverage info
        output_lines = result.stdout.strip().split('\n')
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
                coverage_lines.append(line)
                
            if '----------- coverage:' in line:
                in_coverage_section = True
                continue
                
            if in_coverage_section and line.strip() and not line.startswith("------"):
                if "=" in line:
                    in_coverage_section = False
                else:
                    coverage_lines.append(line)
        
        if coverage_lines:
            coverage_data["lines"] = coverage_lines
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
            "issues": issues,
            "coverage": coverage_data,
            "command": " ".join(cmd),
            "exit_code": result.returncode
        }
    
    return execute_command(cmd, file_path, "pytest", parse_pytest_output)

def run_bandit(file_path: str) -> Dict[str, Any]:
    """Run bandit security scanner on a Python file or directory."""
    cmd = ['bandit', '-r', file_path, '-f', 'json']
    
    def parse_bandit_output(result, issues):
        json_output = None
        if result.stdout and 'results' in result.stdout:
            import json
            try:
                json_output = json.loads(result.stdout)
                
                # Group by severity
                by_severity = {
                    'HIGH': [],
                    'MEDIUM': [],
                    'LOW': []
                }
                
                issues = []
                if 'results' in json_output:
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
                
                return {
                    "passed": len(json_output.get('results', [])) == 0,
                    "issues": issues,
                    "issues_by_severity": by_severity,
                    "command": " ".join(cmd),
                    "exit_code": result.returncode,
                    "metrics": json_output.get('metrics', {})
                }
            except json.JSONDecodeError:
                pass
                
        return None  # Use default parsing
    
    return execute_command(cmd, file_path, "bandit", parse_bandit_output)

def run_eslint(file_path: str) -> Dict[str, Any]:
    """Run ESLint on a JavaScript/TypeScript file."""
    return execute_command(['eslint', '--format', 'json', file_path], file_path, "eslint")

def run_tsc(file_path: str) -> Dict[str, Any]:
    """Run TypeScript compiler (tsc) for type checking."""
    return execute_command(['tsc', '--noEmit', file_path], file_path, "tsc")

def run_govet(file_path: str) -> Dict[str, Any]:
    """Run go vet for Go code analysis."""
    return execute_command(['go', 'vet', file_path], file_path, "go vet")

def run_checkstyle(file_path: str, config_path: str = '/google_checks.xml') -> Dict[str, Any]:
    """Run checkstyle for Java code analysis."""
    return execute_command(['checkstyle', '-c', config_path, file_path], file_path, "checkstyle")

# Export all tool functions
__all__ = [
    "run_flake8",
    "run_black",
    "run_mypy",
    "run_pytest",
    "run_bandit",
    "run_eslint",
    "run_tsc",
    "run_govet",
    "run_checkstyle",
]