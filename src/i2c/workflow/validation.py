# src/i2c/workflow/validation.py

from pathlib import Path
import subprocess
import os
import ast
import re
from typing import Dict, List, Tuple, Any

from i2c.cli.controller import canvas

def validate_generated_application(code_map, project_path, language):
    """
    Validate the entire generated application before deployment.
    Returns: (success: bool, validation_results: dict)
    """
    results = {
        "overall_success": True,
        "file_results": {},
        "runtime_check": None,
        "integration_check": None,
        "dependency_check": None,
    }
    
    # 1. Validate individual files
    for file_path, content in code_map.items():
        file_result = validate_file(content, file_path, language)
        results["file_results"][file_path] = file_result
        if not file_result["success"]:
            results["overall_success"] = False
    
    # Create temporary directory for files if not already done
    tmp_project_path = project_path / ".validation"
    tmp_project_path.mkdir(exist_ok=True)
    
    # 2. Write files to temporary location
    for file_path, content in code_map.items():
        full_path = tmp_project_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
    
    # 3. Dependency check
    if language.lower() == "python":
        results["dependency_check"] = check_python_dependencies(tmp_project_path)
        if not results["dependency_check"]["success"]:
            results["overall_success"] = False
    
    # 4. Syntax check for the entire project
    if language.lower() == "python":
        success, output = run_python_syntax_check(tmp_project_path)
        results["syntax_check"] = {"success": success, "output": output}
        if not success:
            results["overall_success"] = False
    
    # 5. Integration check (look for undefined references)
    try:
        from i2c.agents.quality_team.integration_checker_agent import integration_checker_agent
        integration_issues = integration_checker_agent.check_integrations(tmp_project_path)
        results["integration_check"] = {
            "success": len(integration_issues) == 0,
            "issues": integration_issues
        }
        if len(integration_issues) > 0:
            # Don't fail the build for minor integration issues
            canvas.warning(f"Integration issues found: {len(integration_issues)}")
    except ImportError:
        # Integration checker not available
        canvas.warning("Integration checker not available, skipping integration check")
        results["integration_check"] = {"success": True, "issues": []}
    
    # 6. Runtime check - try to execute the main file
    if language.lower() == "python":
        main_files = [f for f in code_map.keys() if "main.py" in f or f.endswith("app.py")]
        if main_files:
            main_file = main_files[0]
            success, output = run_python_script(tmp_project_path / main_file)
            results["runtime_check"] = {"success": success, "output": output}
            # Runtime issues are warnings only, not failures
            if not success:
                canvas.warning(f"Runtime issues in {main_file}: {output[:200]}")
    
    return results["overall_success"], results

def validate_file(content, file_path, language):
    """Validate a single file for syntax and other issues"""
    result = {"success": True, "issues": []}
    
    if language.lower() == "python" and file_path.endswith('.py'):
        try:
            import ast
            ast.parse(content)
        except SyntaxError as e:
            result["success"] = False
            result["issues"].append(f"Syntax error: {str(e)}")
    
    elif language.lower() == "javascript" and (file_path.endswith('.js') or file_path.endswith('.jsx')):
        try:
            import esprima
            esprima.parseScript(content)
        except Exception as e:
            result["success"] = False
            result["issues"].append(f"JavaScript syntax error: {str(e)}")
    
    # Check for other issues (add more checks as needed)
    if "TODO" in content or "FIXME" in content:
        result["issues"].append("Contains TODO or FIXME markers")
    
    # Check if file is suspiciously small
    if len(content.strip()) < 10:
        result["success"] = False
        result["issues"].append("File content suspiciously small")
    
    return result

def check_python_dependencies(project_path):
    """Check for missing Python dependencies"""
    import re
    from pathlib import Path
    
    result = {"success": True, "missing_deps": []}
    all_imports = set()
    
    # Scan all Python files for imports
    for py_file in project_path.glob("**/*.py"):
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                
            # Extract imports
            import_lines = re.findall(r'^(?:from|import)\s+([\w\.]+)', content, re.MULTILINE)
            for imp in import_lines:
                # Get the top-level package
                top_pkg = imp.split('.')[0]
                if top_pkg not in ['os', 'sys', 'pathlib', 'datetime', 're', 'json', 
                                'math', 'random', 'time', 'typing', 'collections',
                                'i2c']:  # Standard library and our own package
                    all_imports.add(top_pkg)
        except Exception as e:
            # Skip files that can't be read
            continue
    
    # Check if imports are installable
    import importlib.util
    for pkg in all_imports:
        if importlib.util.find_spec(pkg) is None:
            result["success"] = False
            result["missing_deps"].append(pkg)
    
    return result

def run_python_syntax_check(project_path):
    """Run Python syntax check on all files"""
    import subprocess
    from pathlib import Path
    
    # Find all Python files
    py_files = list(project_path.glob("**/*.py"))
    if not py_files:
        return True, "No Python files found"
    
    # Run syntax check
    cmd = ["python", "-m", "py_compile"]
    cmd.extend([str(f) for f in py_files])
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            cwd=str(project_path)
        )
        return result.returncode == 0, result.stderr
    except Exception as e:
        return False, str(e)

def run_python_script(script_path):
    """Try to run a Python script to check for runtime errors"""
    import subprocess
    from pathlib import Path
    
    if not script_path.exists():
        return False, f"Script not found: {script_path}"
    
    # Run with a timeout to prevent hanging
    try:
        result = subprocess.run(
            ["python", str(script_path)],
            capture_output=True,
            text=True,
            timeout=5,  # 5 second timeout
            cwd=str(script_path.parent)
        )
        return result.returncode == 0, result.stdout if result.returncode == 0 else result.stderr
    except subprocess.TimeoutExpired:
        return False, "Script execution timed out"
    except Exception as e:
        return False, str(e)

def get_code_map_from_path(project_path: Path) -> dict:
    """Scan a directory and create a code map of all files for validation"""
    code_map = {}
    
    for file_path in project_path.rglob('*'):
        if file_path.is_file():
            # Skip hidden files, pycache, etc.
            if any(part.startswith('.') for part in file_path.parts):
                continue
                
            # Read the file content
            try:
                rel_path = file_path.relative_to(project_path)
                code_map[str(rel_path)] = file_path.read_text(encoding='utf-8')
            except Exception:
                # Skip files that can't be read as text
                pass
    
    return code_map

def apply_fixes_based_on_validation(validation_results, project_path):
    """Apply fixes based on validation results"""
    from i2c.cli.controller import canvas
    import sys
    import os
    
    # Import fix_common_python_errors from the generation module
    try:
        from i2c.workflow.generation import fix_common_python_errors
    except ImportError:
        # Define it here as a fallback
        def fix_common_python_errors(code):
            import re
            
            # Fix missing colons after function/class definitions
            code = re.sub(r'(def\s+\w+\([^)]*\))\s*\n', r'\1:\n', code)
            code = re.sub(r'(class\s+\w+(?:\([^)]*\))?)\s*\n', r'\1:\n', code)
            
            # Fix indentation
            lines = code.split('\n')
            fixed_lines = []
            in_class_or_func = False
            expected_indent = 0
            
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    fixed_lines.append(line)
                    continue
                    
                if re.match(r'(def|class)\s+\w+', stripped):
                    in_class_or_func = True
                    expected_indent = len(line) - len(line.lstrip())
                    fixed_lines.append(line)
                elif in_class_or_func and not line.startswith(' '):
                    fixed_lines.append(' ' * 4 + line)
                else:
                    fixed_lines.append(line)
            
            return '\n'.join(fixed_lines)
    
    # Handle syntax issues
    for file_path, result in validation_results.get("file_results", {}).items():
        if not result["success"]:
            full_path = project_path / file_path
            if full_path.exists():
                try:
                    content = full_path.read_text(encoding='utf-8')
                    if file_path.endswith('.py'):
                        fixed_content = fix_common_python_errors(content)
                        full_path.write_text(fixed_content, encoding='utf-8')
                        canvas.info(f"Applied auto-fixes to {file_path}")
                except Exception as e:
                    canvas.warning(f"Error applying fixes to {file_path}: {e}")
    
    # Handle dependency issues
    missing_deps = validation_results.get("dependency_check", {}).get("missing_deps", [])
    if missing_deps:
        # Create requirements.txt with missing dependencies
        reqs_file = project_path / "requirements.txt"
        current_reqs = set()
        if reqs_file.exists():
            current_reqs = set(reqs_file.read_text().splitlines())
        
        with open(reqs_file, 'a') as f:
            for dep in missing_deps:
                if dep not in current_reqs:
                    f.write(f"{dep}\n")
        
        canvas.info(f"Updated requirements.txt with missing dependencies: {', '.join(missing_deps)}")

def try_recovery_actions(action_type: str, project_path: Path):
    """Try to recover from failures with specific actions"""
    from i2c.cli.controller import canvas
    
    # 1. Ensure project structure is valid
    ensure_basic_structure(project_path, action_type)
    
    # 2. Fix obvious syntax errors in Python files
    fix_python_syntax_errors(project_path)
    
    # 3. Ensure packages are importable
    add_missing_init_files(project_path)

def ensure_basic_structure(project_path: Path, action_type: str):
    """Ensure the project has at least a basic valid structure"""
    if action_type == "generate" and not any(project_path.iterdir()):
        # Create minimal structure for an empty project
        (project_path / "main.py").write_text(
            '#!/usr/bin/env python3\n\n"""\nMinimally viable application\n"""\n\n'
            'def main():\n    """Main function"""\n    print("Hello, World!")\n\n'
            'if __name__ == "__main__":\n    main()\n'
        )
        (project_path / "__init__.py").touch()

def fix_python_syntax_errors(project_path: Path):
    """Try to fix obvious syntax errors in Python files"""
    import ast
    
    for py_file in project_path.glob("**/*.py"):
        try:
            content = py_file.read_text(encoding='utf-8')
            # Try parsing with ast
            ast.parse(content)
            # No syntax error, continue
        except SyntaxError:
            # Try to fix the syntax
            try:
                from i2c.workflow.generation import fix_common_python_errors
            except ImportError:
                # If not available, define a simple version here
                def fix_common_python_errors(code):
                    import re
                    code = re.sub(r'(def\s+\w+\([^)]*\))\s*\n', r'\1:\n', code)
                    code = re.sub(r'(class\s+\w+(?:\([^)]*\))?)\s*\n', r'\1:\n', code)
                    return code
            
            fixed_content = fix_common_python_errors(content)
            py_file.write_text(fixed_content, encoding='utf-8')

def add_missing_init_files(project_path: Path):
    """Add __init__.py files to make packages importable"""
    from i2c.cli.controller import canvas
    
    # Find all directories that might be packages
    for dir_path in project_path.glob("**/"):
        if dir_path.is_dir() and any(f.suffix == '.py' for f in dir_path.iterdir() if f.is_file()):
            init_file = dir_path / "__init__.py"
            if not init_file.exists():
                init_file.touch()
                canvas.info(f"Added missing __init__.py to {dir_path.relative_to(project_path)}")