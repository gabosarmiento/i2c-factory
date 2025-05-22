# src/i2c/cli/diagnostic_cli.py
"""Diagnostic CLI for analyzing the modification workflow."""

import argparse
from pathlib import Path
from i2c.cli.controller import canvas
from i2c.workflow.diagnostic.modification_analyzer import ModificationAnalyzer

def run_diagnostic_command(args=None):
    """Run the modification workflow diagnostic tool."""
    if args is None:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="I2C Factory Modification Workflow Analyzer")
        parser.add_argument("request", help="The modification request to analyze")
        parser.add_argument("project_path", help="Path to the project directory")
        parser.add_argument("--language", "-l", default="python", help="Programming language (default: python)")
        parser.add_argument("--output-dir", "-o", default="./diagnostic_reports", help="Output directory for reports")
        
        args = parser.parse_args()
        
    canvas.start_process("Modification Workflow Diagnostic")
    
    project_path = Path(args.project_path)
    output_dir = Path(args.output_dir)
    
    # Validate project path
    if not project_path.exists() or not project_path.is_dir():
        canvas.error(f"Project path does not exist or is not a directory: {project_path}")
        return False
    
    # Run the diagnostic
    canvas.info(f"Running diagnostic on '{project_path}' for request: {args.request}")
    
    analyzer = ModificationAnalyzer(output_dir=output_dir)
    result = analyzer.run_diagnostic(
        user_request=args.request,
        project_path=project_path,
        language=args.language
    )
    
    # Show result summary
    if result.get("overall_result", False):
        canvas.success("Diagnostic completed successfully!")
    else:
        canvas.error("Diagnostic failed. Check the generated reports for details.")
    
    canvas.info(f"Diagnostic reports saved to: {output_dir}")
    canvas.end_process("Diagnostic Completed")
    return True

def main():
    """CLI entry point"""
    run_diagnostic_command()

if __name__ == "__main__":
    main()