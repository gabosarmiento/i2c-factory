# /workflow.py
# Clean Workflow: Pure Application Logic, No Colors, No Visuals

from pathlib import Path
import json

from agents.core_agents import (
    input_processor_agent,
    planner_agent,
    code_builder_agent,
    write_files,
)
from cli.controller import canvas

DEFAULT_OUTPUT_DIR = Path("./output/generated_project")

def run_workflow():
    canvas.start_process("Idea-to-Code Factory Workflow")

    # Step 1: Get User Idea
    canvas.step("Describe your project idea")
    user_idea = canvas.get_user_input("Enter your project idea:")
    if not user_idea.strip():
        canvas.error("No idea provided. Exiting.")
        return

    output_directory = DEFAULT_OUTPUT_DIR
    canvas.info(f"Output directory set to: {output_directory}")

    # Step 2: Clarify Idea
    canvas.step("Clarifying idea...")
    try:
        response = input_processor_agent.run(user_idea)
        structured_goal = json.loads(response.content)
        canvas.success(f"Objective: {structured_goal['objective']}")
        canvas.success(f"Language: {structured_goal['language']}")
    except Exception as e:
        canvas.error(f"Error clarifying idea: {e}")
        return

    # Step 3: Plan Files
    canvas.step("Planning minimal file structure...")
    try:
        plan_prompt = (
            f"Objective: {structured_goal['objective']}\n"
            f"Language: {structured_goal['language']}"
        )
        response = planner_agent.run(plan_prompt)
        file_plan = json.loads(response.content)
        canvas.success(f"Planned files: {file_plan}")
    except Exception as e:
        canvas.error(f"Error planning files: {e}")
        return

    # Step 4: Generate Code
    canvas.step("Generating code files...")
    generated_code = {}
    try:
        for file_path in file_plan:
            build_prompt = (
                f"Objective: {structured_goal['objective']}\n"
                f"Language: {structured_goal['language']}\n"
                f"Generate complete, runnable code for the file '{file_path}'."
            )
            response = code_builder_agent.run(build_prompt)
            raw = response.content
            # Strip markdown code fences if present
            if raw.strip().startswith("```"):
                lines = raw.splitlines()
                # remove opening fence
                if lines and lines[0].strip().startswith("```"):
                    lines = lines[1:]
                # remove closing fence
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                code = "\n".join(lines)
            else:
                code = raw
            code = code.strip()
            generated_code[file_path] = code
            canvas.success(f"Generated: {file_path}")
    except Exception as e:
        canvas.error(f"Error generating code: {e}")
        return

    # Step 5: Write Files
    canvas.step("Writing files to disk...")
    try:
        write_files(generated_code, output_directory)
        canvas.success("Project generation complete!")
        canvas.info(f"Files saved at: {output_directory}")
    except Exception as e:
        canvas.error(f"Error writing files: {e}")
        return

    canvas.end_process("Workflow completed successfully.")

if __name__ == "__main__":
    run_workflow()
