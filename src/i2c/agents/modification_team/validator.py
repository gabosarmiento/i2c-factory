# src/i2c/agents/modification_team/validator.py
from pathlib import Path      
import subprocess
import ast

def run_validator(repo_root: Path) -> tuple[bool, str]:
    """
    Run a simplified validator that checks Python syntax and some basic rules.
    Returns (passed, diagnostics).
    """
    # Check if our target file exists
    test_file = repo_root / "i2c_test/test_app/routers/users.py"
    if not test_file.exists():
        return False, f"Test file not found: {test_file}"
    
    # Check Python syntax
    try:
        with open(test_file, 'r') as f:
            content = f.read()
        ast.parse(content)
    except SyntaxError as e:
        return False, f"Syntax error in {test_file.name}: {e}"
    
    # Check for required code
    required_lines = [
        "if not user.name:",
        "raise HTTPException(400, 'Name cannot be empty')",
        "EmailStr.validate(user.email)"
    ]
    
    missing_lines = []
    for line in required_lines:
        if line not in content:
            missing_lines.append(line)
    
    if missing_lines:
        return False, f"Missing required code in {test_file.name}:\n" + "\n".join(missing_lines)
    
    # All checks passed
    return True, "All validation checks passed."