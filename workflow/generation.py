# /workflow/generation.py
# Contains the logic for executing the initial project generation cycle.

import json
from pathlib import Path

# Import core agent instances
from agents.core_agents import (
    planner_agent,
    code_builder_agent,
)
# Import SRE agent INSTANCES
from agents.sre_team import (
    unit_test_generator,
    code_quality_sentinel
)
# Import file operations
from .modification.file_operations import write_files_to_disk as write_files
# Import CLI controller
from cli.controller import canvas

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
            build_prompt = (
                f"Objective: {objective}\nLanguage: {language}\n"
                f"Generate complete, runnable code for the file '{file_path}'."
            )
            response = code_builder_agent.run(build_prompt)
            raw = response.content if hasattr(response, 'content') else str(response)
            # ... (cleaning logic) ...
            if raw.strip().startswith("```"):
                lines = raw.splitlines()
                if lines and lines[0].strip().startswith("```"): lines = lines[1:]
                if lines and lines[-1].strip().startswith("```"): lines = lines[:-1]
                code = "\n".join(lines)
            else: code = raw
            generated_code[file_path] = code.strip()
            canvas.success(f"Generated: {file_path}")
    except Exception as e:
        canvas.error(f"Error generating code: {e}")
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
        if issues: canvas.warning(f"Code quality issues found: {len(issues)}")
        else: canvas.success("Code quality checks passed.")
    except Exception as e:
        canvas.error(f"Error during SRE Quality Check: {e}")
        canvas.end_process(f"Generation cycle failed during quality check.")
        return return_context # Return context with success=False

    # 5. Write Files
    canvas.step("Writing files to disk...")
    try:
        write_files(code_map_with_tests, project_path)
        ensure_init_py(project_path)  # <<< PATCH: Ensure __init__.py exists
    except Exception as e:
        canvas.error(f"Error during file writing step: {e}")
        canvas.end_process(f"Generation cycle failed during file writing.")
        return return_context # Return context with success=False

    canvas.end_process(f"Generation cycle for {project_path.name} completed successfully.")
    return_context["success"] = True
    # return_context["code_map"] already set
    return return_context
