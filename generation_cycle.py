# /generation_cycle.py
# Contains the logic for executing a single generation cycle:
# Plan -> Build -> Unit Test Gen -> Quality Check -> Write Files
# Accepts structured_goal as input.

import json
from pathlib import Path

# Import core agent instances
from agents.core_agents import (
    # InputProcessor is now called *before* this cycle starts
    planner_agent,
    code_builder_agent,
    write_files
)
# Import SRE agent INSTANCES from the sre_team module
from agents.sre_team import (
    unit_test_generator,
    code_quality_sentinel
)

# Import CLI controller
from cli.controller import canvas

def run_generation_cycle(structured_goal: dict, project_path: Path) -> dict:
    """
    Runs a single cycle of planning, generation, unit test generation,
    quality check, and writing based on a pre-processed goal.

    Args:
        structured_goal: Dictionary containing 'objective' and 'language'.
        project_path: The target directory for the generated files.

    Returns:
        A dictionary: {"success": bool, "language": str | None}
    """
    canvas.start_process(f"Generation Cycle for: {project_path.name}")
    language = structured_goal.get("language")
    objective = structured_goal.get("objective")
    file_plan = None
    generated_code = {}
    code_map_with_tests = {}
    return_context = {"success": False, "language": language} # Default return

    if not language or not objective:
         canvas.error("Invalid structured_goal provided to generation cycle (missing objective or language).")
         return return_context

    # Step numbers adjusted as clarification is done outside this function now

    # 1. Plan Files
    canvas.step("Planning minimal file structure...")
    try:
        plan_prompt = (
            f"Objective: {objective}\n"
            f"Language: {language}"
        )
        response = planner_agent.run(plan_prompt)
        file_plan = json.loads(response.content)
        canvas.success(f"Planned files: {file_plan}")
    except Exception as e:
        canvas.error(f"Error planning files: {e}")
        canvas.end_process(f"Generation cycle for {project_path.name} failed at planning.")
        return return_context # success remains False

    # 2. Generate Code
    canvas.step("Generating code files...")
    try:
        for file_path in file_plan:
            build_prompt = (
                f"Objective: {objective}\n"
                f"Language: {language}\n" # Pass correct language
                f"Generate complete, runnable code for the file '{file_path}'."
            )
            response = code_builder_agent.run(build_prompt)
            raw = response.content
            if raw.strip().startswith("```"):
                lines = raw.splitlines()
                if lines and lines[0].strip().startswith("```"): lines = lines[1:]
                if lines and lines[-1].strip().startswith("```"): lines = lines[:-1]
                code = "\n".join(lines)
            else:
                code = raw
            code = code.strip()
            generated_code[file_path] = code
            canvas.success(f"Generated: {file_path}")
    except Exception as e:
        canvas.error(f"Error generating code: {e}")
        canvas.end_process(f"Generation cycle for {project_path.name} failed at code generation.")
        return return_context

    # 3. Generate Unit Tests
    canvas.step("Generating Unit Tests...")
    try:
        code_map_with_tests = unit_test_generator.generate_tests(generated_code)
    except Exception as e:
        canvas.error(f"Error during Unit Test Generation: {e}")
        canvas.warning("Proceeding without generated unit tests due to error.")
        code_map_with_tests = generated_code # Fallback

    # 4. SRE Quality Check
    canvas.step("Performing SRE Code Quality Check...")
    try:
        issues = code_quality_sentinel.check_code(code_map_with_tests)
        if issues:
            canvas.warning("Code quality issues found:")
            for issue in issues: canvas.warning(f"  - {issue}")
        else:
            canvas.success("Code quality checks passed.")
    except Exception as e:
        canvas.error(f"Error during SRE Quality Check: {e}")
        canvas.end_process(f"Generation cycle for {project_path.name} failed during quality check.")
        return return_context

    # 5. Write Files
    canvas.step("Writing files to disk...")
    try:
        write_files(code_map_with_tests, project_path)
        canvas.success("Project files saved!")
        canvas.info(f"Files saved at: {project_path}")
    except Exception as e:
        canvas.error(f"Error writing files: {e}")
        canvas.end_process(f"Generation cycle for {project_path.name} failed during file writing.")
        return return_context

    canvas.end_process(f"Generation cycle for {project_path.name} completed successfully.")
    return_context["success"] = True # Mark success
    return return_context # Return success status and language

