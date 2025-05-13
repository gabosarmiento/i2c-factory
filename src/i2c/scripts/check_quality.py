#!/usr/bin/env python
# scripts/check_quality.py
# A script to run quality checks on files

import asyncio
import argparse
from pathlib import Path
import sys
import json

# Import the quality lead agent
from i2c.agents.quality_team.quality_team import QualityLeadAgent

async def check_quality(files_to_check, quality_gates=None, project_path=None):
    """
    Run quality checks on the specified files.
    
    Args:
        files_to_check: Dictionary mapping file paths to content
        quality_gates: List of quality gates to run or preset names
        project_path: Path to the project directory
    
    Returns:
        Dict with validation results
    """
    quality_lead = QualityLeadAgent()
    
    if project_path is None:
        # Use the current directory if not specified
        project_path = Path.cwd()
    
    # Run validation
    results = await quality_lead.validate_changes(
        project_path=project_path,
        modified_files=files_to_check,
        quality_gates=quality_gates
    )
    
    return results

def format_results(results):
    """Format the results for display"""
    output = []
    
    # Show overall status
    passed = results.get("passed", False)
    output.append(f"Quality Check: {'PASSED' if passed else 'FAILED'}")
    output.append("")
    
    # Show enterprise quality gate issues
    if "enterprise_results" in results:
        enterprise_results = results["enterprise_results"]
        summary = enterprise_results.get("summary", {})
        
        output.append(f"Quality Gates Run: {summary.get('quality_gates_run', 0)}")
        output.append(f"Quality Gates Failed: {summary.get('quality_gates_failed', 0)}")
        output.append(f"Total Issues: {summary.get('total_issues', 0)}")
        output.append("")
        
        # Show file-specific issues
        if enterprise_results.get("files_with_issues"):
            output.append("Files with Issues:")
            for file_path in enterprise_results.get("files_with_issues", []):
                output.append(f"  - {file_path}")
                
                file_issues = enterprise_results.get("issues", {}).get(file_path, {})
                for gate, gate_result in file_issues.items():
                    gate_passed = gate_result.get("passed", False)
                    gate_status = "PASSED" if gate_passed else "FAILED"
                    output.append(f"    {gate}: {gate_status}")
                    
                    for issue in gate_result.get("issues", [])[:5]:  # Show up to 5 issues
                        output.append(f"      - {issue}")
                    
                    if len(gate_result.get("issues", [])) > 5:
                        output.append(f"      ... and {len(gate_result.get('issues', [])) - 5} more issues")
        
        output.append("")
    
    # Show other issues
    if "issues" in results:
        other_issues = results["issues"]
        if other_issues:
            output.append("Other Issues:")
            for issue in other_issues[:10]:  # Show up to 10 issues
                output.append(f"  - {issue}")
            
            if len(other_issues) > 10:
                output.append(f"  ... and {len(other_issues) - 10} more issues")
    
    return "\n".join(output)

def main():
    """Run quality checks from the command line"""
    parser = argparse.ArgumentParser(description="Run quality checks on files")
    parser.add_argument("files", nargs="+", help="Files to check")
    parser.add_argument("--gates", nargs="+", default=["all"], 
                        help="Quality gates to run (e.g., flake8, black, or presets like 'python', 'all')")
    parser.add_argument("--project", type=str, default=None,
                        help="Project directory path (defaults to current directory)")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    
    args = parser.parse_args()
    
    # Read file contents
    files_to_check = {}
    for file_path in args.files:
        path = Path(file_path)
        if not path.exists():
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        
        try:
            with open(path, 'r') as f:
                files_to_check[str(path)] = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Set project path
    project_path = None
    if args.project:
        project_path = Path(args.project)
        if not project_path.exists() or not project_path.is_dir():
            print(f"Error: Project directory not found: {args.project}", file=sys.stderr)
            sys.exit(1)
    
    # Run quality checks
    try:
        results = asyncio.run(check_quality(
            files_to_check=files_to_check,
            quality_gates=args.gates,
            project_path=project_path
        ))
        
        # Output results
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print(format_results(results))
        
        # Exit with appropriate status code
        sys.exit(0 if results.get("passed", False) else 1)
        
    except Exception as e:
        print(f"Error running quality checks: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()