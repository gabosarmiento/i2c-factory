# src/i2c/scripts/check_and_create_files.py
"""Check for missing files and create them if needed under src/i2c"""

from pathlib import Path
from i2c.bootstrap import initialize_environment, PROJECT_ROOT

# 1) Initialize environment (tokenizers env var + builtins)
initialize_environment()

# 2) Root of the i2c package under the project
package_root = PROJECT_ROOT / "src" / "i2c"

# Define required files relative to the package root
required_files = {
    "models/__init__.py": "",
    "models/user_story.py": "# models/user_story.py already provided above\n",
    "story_manager.py": "# story_manager.py already provided above\n",
    "workflow/feature_pipeline.py": "# workflow/feature_pipeline.py already provided above\n",
    "workflow/feature_integration.py": "# workflow/feature_integration.py already provided above\n",
    "cli/rich_output.py": "# cli/rich_output.py already provided above\n",
    "cli/demo.py": "# cli/demo.py already provided above\n",
    "scripts/__init__.py": "",
}

def check_and_create_files():
    """Check for missing files under the package and create them"""
    for rel_path, content in required_files.items():
        full_path = package_root / rel_path

        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Create file if missing
        if not full_path.exists():
            print(f"Creating missing file: {rel_path}")
            with open(full_path, 'w') as f:
                f.write(content)
        else:
            print(f"✓ File exists: {rel_path}")

if __name__ == "__main__":
    check_and_create_files()
