# run_modification_cycle.py

from i2c.bootstrap import initialize_environment
initialize_environment()

import argparse
from pathlib import Path
from i2c.workflow.modification_workflow import run_modification_workflow, run_reflective_validation_if_needed


def get_latest_output_folder(base_dir="output") -> Path:
    """Detect the most recently created/modified project folder inside 'output/'."""
    base_path = Path(base_dir)
    all_dirs = [d for d in base_path.iterdir() if d.is_dir()]
    if not all_dirs:
        raise FileNotFoundError("No folders found in output/")
    latest_dir = max(all_dirs, key=lambda d: d.stat().st_mtime)
    return latest_dir


def run_full_cycle(scenario_path: str, project_path: str = None):
    print("🚀 Running Modification Workflow")
    run_modification_workflow(scenario_path=scenario_path)

    print("\n🧪 Running Reflective Validation")
    if not project_path:
        project_path = get_latest_output_folder()
        print(f"[INFO] Auto-detected latest project path: {project_path}")

    valid = run_reflective_validation_if_needed(project_path)
    if valid:
        print("\n✅ Code is ready to go!")
    else:
        print("\n⚠️ Validation failed. Review retry suggestions above.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run modification + validation cycle")
    parser.add_argument("--scenario", required=True, help="Path to the scenario JSON file")
    parser.add_argument("--project", required=False, help="Optional path to the project folder (auto-detected if missing)")
    args = parser.parse_args()

    run_full_cycle(args.scenario, args.project)
