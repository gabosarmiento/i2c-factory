# src/i2c/app.py

import subprocess
import sys
from dotenv import load_dotenv

from i2c.workflow import start_factory_session
from i2c.cli.ascii   import show_banner
from i2c.config.config import load_groq_api_key
from i2c.agents.budget_manager import BudgetManagerAgent
from i2c.workflow.scenario_processor import run_scenario, add_scenario_arguments

from i2c.cli.diagnostic_cli import run_diagnostic_command
from pathlib import Path

import builtins

def check_environment():
    """Check Python and dependency versions"""
    print("🔍 Running environment check…")
    # result = subprocess.run([sys.executable, "scripts/check_versions.py"], capture_output=True)
    # point at the installed package location
    result = subprocess.run(
        [sys.executable, "-m", "i2c.scripts.check_versions"],
        capture_output=True
    )
    if result.returncode != 0:
        print("❌ Environment check failed!")
        print(result.stdout.decode())
        sys.exit(1)
    else:
        print("✅ Environment check passed.")

def load_environment():
    """Loads environment variables from .env file."""
    load_dotenv()
    print("🔑 Environment variables loaded (if .env file exists).")
    try:
        load_groq_api_key()
        print("   ✅ GROQ_API_KEY found.")
        return True
    except ValueError as e:
        print(f"   {e}")
        return False

def initialize_budget_manager():
    """Sets up and globally registers the budget manager."""
    global_budget_manager = BudgetManagerAgent(session_budget=None)
    builtins.global_budget_manager = global_budget_manager
    print("💰 Budget manager initialized with $10 session budget.")

def main():
    """Entry point for your Idea-to-Code Factory CLI."""
    print("--- Application Start ---")
    check_environment()
    show_banner()
    
    # Add argument parsing
    import argparse
    parser = argparse.ArgumentParser(description="I2C Factory")
    
    # Add scenario arguments
    add_scenario_arguments(parser)
    
    # Add diagnostic command arguments
    parser.add_argument("--diagnose", action="store_true", 
                       help="Run diagnostic analysis on the modification workflow")
    parser.add_argument("--request", help="Modification request for diagnostic")
    parser.add_argument("--project-path", help="Project path for diagnostic")
    parser.add_argument("--language", "-l", default="python", 
                       help="Programming language (default: python)")
    parser.add_argument("--output-dir", "-o", default="./diagnostic_reports", 
                       help="Output directory for reports")
    parser.add_argument("--index", action="store_true", help="Index the codebase context")

     # Parse arguments
    args = parser.parse_args()

    if load_environment():
        initialize_budget_manager()
        if args.index:
            if not args.project_path:
                print("Error: --project-path is required with --index")
                return
            from i2c.agents.modification_team.context_reader import ContextReaderAgent
            from pathlib import Path
            reader = ContextReaderAgent(Path(args.project_path))
            result = reader.index_project_context()
            print("\n✅ Indexing complete.")
            for k, v in result.items():
                print(f"{k}: {v}")
            return
        # Check if we should run a diagnostic
        if args.diagnose:
            if not args.request or not args.project_path:
                print("Error: --request and --project-path are required with --diagnose")
                return
                
            # Run diagnostic command
            run_diagnostic_command(args)
            return
        
        # Check if we should run a scenario
        if hasattr(args, 'scenario') and args.scenario:
            print(f"Running scenario: {args.scenario}")
            run_scenario(args.scenario, builtins.global_budget_manager)
        else:
            # Start normal interactive session
            start_factory_session()
    else:
        print("❌ Workflow aborted due to missing environment configuration.")

    print("--- Application End ---")

# Keep this here if someone runs `python src/i2c/app.py` directly:
if __name__ == "__main__":
    main()
