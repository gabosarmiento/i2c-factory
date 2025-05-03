# scripts/check_and_create_files.py
"""Check for missing files and create them if needed"""

import os
from pathlib import Path

# Define required files and their content
required_files = {
    "models/__init__.py": "",
    "models/user_story.py": """# models/user_story.py already provided above""",
    "story_manager.py": """# story_manager.py already provided above""",
    "workflow/feature_pipeline.py": """# workflow/feature_pipeline.py already provided above""",
    "workflow/feature_integration.py": """# workflow/feature_integration.py already provided above""",
    "cli/rich_output.py": """# cli/rich_output.py already provided above""",
    "cli/demo.py": """# cli/demo.py already provided above""",
    "scripts/__init__.py": "",
}

def check_and_create_files():
    """Check for missing files and create them"""
    project_root = Path(__file__).parent.parent
    
    for file_path, content in required_files.items():
        full_path = project_root / file_path
        
        # Create directory if it doesn't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file exists
        if not full_path.exists():
            print(f"Creating missing file: {file_path}")
            with open(full_path, 'w') as f:
                f.write(content)
        else:
            print(f"✓ File exists: {file_path}")


if __name__ == "__main__":
    check_and_create_files()