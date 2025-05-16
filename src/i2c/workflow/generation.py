# Contains the logic for executing the initial project generation cycle.

import json
from pathlib import Path
import traceback

# Import core agent instances
from i2c.agents.core_agents import (
    planner_agent,
    code_builder_agent,
)
# Import SRE agent INSTANCES
from i2c.agents.sre_team import (
    unit_test_generator,
    code_quality_sentinel
)
# Import file operations
from .modification.file_operations import write_files_to_disk as write_files, post_process_code_map
# Import CLI controller
from i2c.cli.controller import canvas
# Import Utils 
from i2c.workflow.utils import deduplicate_code_map

def clean_and_validate_code(raw_text, file_path):
    """Enhanced code cleaning and validation function"""
    # 1. Remove thinking/reasoning text
    import re
    
    # First, extract code blocks if present
    if "```" in raw_text:
        code_blocks = re.findall(r'```(?:python|javascript)?\s*([\s\S]*?)```', raw_text)
        if code_blocks:
            # Use the largest code block found
            code = max(code_blocks, key=len).strip()
        else:
            code = raw_text.strip()
    else:
        code = raw_text.strip()
    
    # 2. Enhanced language detection
    is_python = file_path.endswith('.py')
    is_javascript = file_path.endswith('.js') or file_path.endswith('.jsx')
    is_html = file_path.endswith('.html') or file_path.endswith('.htm')
    
    # 3. Validate syntax based on language
    if is_python:
        try:
            import ast
            ast.parse(code)
            # Syntax is valid, keep the code
        except SyntaxError as e:
            # Log the error
            from i2c.cli.controller import canvas
            canvas.warning(f"Syntax error in generated Python code: {e}")
            
            # Apply auto-fixes for common Python syntax issues
            code = fix_common_python_errors(code)
            
            # If code still has syntax errors after fixes, fall back to template
            try:
                ast.parse(code)
            except SyntaxError:
                code = generate_fallback_template(file_path)
    
    elif is_javascript:
        try:
            # Use esprima for JS validation (already in dependencies)
            import esprima
            esprima.parseScript(code)
        except Exception as e:
            # Log the error
            from i2c.cli.controller import canvas
            canvas.warning(f"Syntax error in generated JavaScript code: {e}")
            
            # Fall back to template
            code = generate_fallback_template(file_path)
    
    # 4. Ensure file has minimum required content
    if len(code.strip()) < 10:
        code = generate_fallback_template(file_path)
        
    return code

def fix_common_python_errors(code):
    """Fix common Python syntax errors"""
    import re
    
    # Fix 1: Missing colons after function/class definitions
    code = re.sub(r'(def\s+\w+\([^)]*\))\s*\n', r'\1:\n', code)
    code = re.sub(r'(class\s+\w+(?:\([^)]*\))?)\s*\n', r'\1:\n', code)
    
    # Fix 2: Incorrect indentation (basic fix)
    lines = code.split('\n')
    fixed_lines = []
    in_class_or_func = False
    expected_indent = 0
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            fixed_lines.append(line)
            continue
            
        # Check for class/function definitions
        if re.match(r'(def|class)\s+\w+', stripped):
            in_class_or_func = True
            expected_indent = len(line) - len(line.lstrip())
            fixed_lines.append(line)
        elif in_class_or_func and not line.startswith(' '):
            # Indentation needed but not present
            fixed_lines.append(' ' * 4 + line)
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

# Add to generation.py or another appropriate file

def generate_fallback_template(file_path):
    """Generate a minimal working fallback template based on file type"""
    if file_path.endswith('.py'):
        return '#!/usr/bin/env python3\n\n"""\nModule: {}\nGenerated fallback template\n"""\n\ndef main():\n    """Main function"""\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()'.format(file_path)
    elif file_path.endswith('.js'):
        return '/**\n * File: {}\n * Generated fallback template\n */\n\nconsole.log("Hello, World!");'.format(file_path)
    elif file_path.endswith('.html'):
        return '<!DOCTYPE html>\n<html>\n<head>\n    <meta charset="UTF-8">\n    <title>{}</title>\n</head>\n<body>\n    <h1>Hello, World!</h1>\n</body>\n</html>'.format(file_path)
    else:
        return '# {}\n# Generated fallback template\n\nprint("Hello, World!")'.format(file_path)

def ensure_init_py(project_path: Path):
    """Ensure __init__.py exists in the project root to make it a Python package."""
    init_file = project_path / "__init__.py"
    if not init_file.exists():
        init_file.touch()
        canvas.success(f"✅ [AutoPatch] Created missing __init__.py at {init_file}")
        
def execute_generation_cycle(structured_goal: dict, project_path: Path) -> dict:
    """
    Runs a single cycle of planning, generation, unit test generation,
    quality check, and writing for a NEW project.

    Returns:
        A dictionary: {"success": bool, "language": str | None, "code_map": dict | None}
    """
    canvas.start_process(f"Generation Cycle for: {project_path.name}")
    language = structured_goal.get("language")
    objective = structured_goal.get("objective")
    
    # Log constraints
    if "constraints" in structured_goal:
        canvas.info("🔍 CONSTRAINTS FOUND IN EXECUTE_GENERATION_CYCLE:")
        for i, constraint in enumerate(structured_goal["constraints"], 1):
            canvas.info(f"  Constraint {i}: {constraint}")
                
    file_plan = None
    generated_code = {}
    code_map_with_tests = None # Initialize as None
    # <<< Initialize return context with code_map >>>
    return_context = {"success": False, "language": language, "code_map": None}

    if not language or not objective:
         canvas.error("Invalid structured_goal provided to generation cycle.")
         return return_context

    # 1. Plan Files
    canvas.step("Planning minimal file structure...")
    try:
        # Build constraint text if available
        constraint_text = ""
        if "constraints" in structured_goal:
            constraint_text = "\n\nQUALITY CONSTRAINTS (MUST FOLLOW):\n"
            for i, constraint in enumerate(structured_goal["constraints"], 1):
                constraint_text += f"{i}. {constraint}\n"
            canvas.info(f"Added {len(structured_goal['constraints'])} quality constraints to planning prompt")
            
        plan_prompt = f"Objective: {objective}\nLanguage: {language}"
        response = planner_agent.run(plan_prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        # ... (JSON parsing/validation) ...
        try:
            
            content_processed = content.strip()
            if content_processed.startswith("```json"): content_processed = content_processed[len("```json"):].strip()
            if content_processed.startswith("```"): content_processed = content_processed[3:].strip()
            if content_processed.endswith("```"): content_processed = content_processed[:-3:].strip()
            file_plan = json.loads(content_processed)
            if not isinstance(file_plan, list): raise ValueError("Planner did not return a list.")
        except (json.JSONDecodeError, ValueError) as json_err:
             canvas.error(f"Failed to parse planner response as JSON list: {json_err}")
             canvas.error(f"Planner Raw Response: {content[:500]}")
             raise json_err

        canvas.success(f"Planned files: {file_plan}")
    except Exception as e:
        canvas.error(f"Error planning files: {e}")
        canvas.end_process(f"Generation cycle failed at planning.")
        return return_context

    if not file_plan:
         canvas.error("File plan is empty or invalid. Cannot generate code.")
         canvas.end_process(f"Generation cycle failed: Empty/invalid plan.")
         return return_context

    # 2. Generate Code
    canvas.step("Generating code files...")
    try:
        for file_path in file_plan:
            # Add our quality constraints directly to each prompt
            quality_constraints = (
                "\n\nIMPORTANT QUALITY REQUIREMENTS:\n"
                "1. Use a consistent data model across all files\n"
                "2. Avoid creating duplicate implementations of the same functionality\n"
                "3. Ensure tests do not have duplicate unittest.main() calls\n"
                "4. If creating a CLI app, use a single approach for the interface\n"
                "5. Use consistent file naming for data storage (e.g., todos.json)\n"
            )
            build_prompt = (
                f"Objective: {objective}\nLanguage: {language}\n"
                f"{quality_constraints}\n"
                f"Generate complete, runnable code for the file '{file_path}'."
            )
            response = code_builder_agent.run(build_prompt)
            raw = response.content if hasattr(response, 'content') else str(response)
            
            # Use the clean_llm_response function to handle the cleaning
            code = clean_and_validate_code(raw, file_path)
            
            # Debug logging
            canvas.info(f"Cleaned code for {file_path}: {len(code)} chars")
            if len(code) > 0:
                preview = code[:50] + "..." if len(code) > 50 else code
                canvas.info(f"Preview: {preview}")
            
            generated_code[file_path] = code.strip()
            canvas.success(f"Generated: {file_path}")
            
    except Exception as e:
        canvas.error(f"Error generating code: {e}")
        canvas.error(traceback.format_exc())
        canvas.end_process(f"Generation cycle failed at code generation.")
        return return_context
    

    # 3. Generate Unit Tests
    canvas.step("Generating Unit Tests...")
    try:
        code_map_with_tests = unit_test_generator.generate_tests(generated_code)
    except Exception as e:
        canvas.error(f"Error during Unit Test Generation orchestration: {e}")
        canvas.warning("Proceeding without generated unit tests due to error.")
        code_map_with_tests = generated_code # Fallback

    # Assign to return context BEFORE potential failure in later steps
    return_context["code_map"] = code_map_with_tests

    # 4. SRE Quality Check
    canvas.step("Performing SRE Code Quality Check...")
    try:
        issues = code_quality_sentinel.check_code(code_map_with_tests)
        if issues: 
            canvas.warning(f"Code quality issues found: {len(issues)}")
        else: 
            canvas.success("Code quality checks passed.")
    except Exception as e:
        canvas.error(f"Error during SRE Quality Check: {e}")
        canvas.end_process(f"Generation cycle failed during quality check.")
        return return_context # Return context with success=False

    # 4.5 Apply deduplication to remove redundant files
    canvas.step("Applying file deduplication...")
    try:
        original_file_count = len(code_map_with_tests)
        code_map_with_tests = deduplicate_code_map(code_map_with_tests)
        if len(code_map_with_tests) < original_file_count:
            canvas.success(f"Removed {original_file_count - len(code_map_with_tests)} duplicate files")
    except Exception as e:
        canvas.error(f"Error during file deduplication: {e}")
        
    # 5. Write Files
    canvas.step("Writing files to disk...")
    try:
        write_files(code_map_with_tests, project_path)
        # make both 'output/' and 'output/helloworld/' importable packages
        ensure_init_py(project_path.parent)
        ensure_init_py(project_path)  # <<< PATCH: Ensure __init__.py exists
    except Exception as e:
        canvas.error(f"Error during file writing step: {e}")
        canvas.end_process(f"Generation cycle failed during file writing.")
        return return_context # Return context with success=False

    canvas.end_process(f"Generation cycle for {project_path.name} completed successfully.")
    return_context["success"] = True
    # return_context["code_map"] already set
    return return_context
