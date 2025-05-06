# src/i2c/scripts/verify_imports.py
"""Verify imports in workflow/feature_integration.py"""

import ast
from pathlib import Path
from i2c.bootstrap import initialize_environment, PROJECT_ROOT

# 1) Bootstrap env & builtins (including PROJECT_ROOT)
initialize_environment()

def check_imports(file_path: Path):
    """Parse a Python file and return a list of all imported modules/names."""
    content = file_path.read_text()
    tree = ast.parse(content)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                imports.append(f"{module}.{alias.name}")
    return imports

def main():
    # 2) Locate feature_integration.py inside your package
    fi = PROJECT_ROOT / "src" / "i2c" / "workflow" / "feature_integration.py"
    if not fi.exists():
        print(f"❌ File not found: {fi}")
        return

    # 3) Collect and display imports
    imports = check_imports(fi)
    print(f"Imports found in {fi}:")
    for imp in imports:
        print(f"  - {imp}")

    # 4) Check for required fully-qualified imports
    required = [
        "i2c.models.user_story.UserStory",
        "i2c.models.user_story.StoryStatus",
        "i2c.models.user_story.StoryPriority",
        "i2c.models.user_story.AcceptanceCriteria",
    ]
    print("\nChecking required imports:")
    for req in required:
        status = "✓" if any(im.startswith(req) for im in imports) else "❌"
        print(f"  {status} {req}")

if __name__ == "__main__":
    main()
