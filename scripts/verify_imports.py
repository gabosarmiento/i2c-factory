# scripts/verify_imports.py
"""Verify imports in feature_integration.py"""

import ast
from pathlib import Path

def check_imports(file_path):
    """Check imports in a Python file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
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
    file_path = Path("workflow/feature_integration.py")
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    imports = check_imports(file_path)
    
    print(f"Imports found in {file_path}:")
    for imp in imports:
        print(f"  - {imp}")
    
    # Check for required imports
    required = [
        "models.user_story.UserStory",
        "models.user_story.StoryStatus",
        "models.user_story.StoryPriority",
        "models.user_story.AcceptanceCriteria"
    ]
    
    print("\nChecking required imports:")
    for req in required:
        if any(req in imp for imp in imports):
            print(f"  ✓ {req}")
        else:
            print(f"  ❌ {req} - MISSING")

if __name__ == "__main__":
    main()