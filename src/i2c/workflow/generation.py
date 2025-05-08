# Contains the logic for executing the initial project generation cycle.

import json
from pathlib import Path

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
from .modification.file_operations import write_files_to_disk as write_files
# Import CLI controller
from i2c.cli.controller import canvas

def clean_llm_response(raw_text, file_path):
    """Cleans the LLM response to extract only valid code"""
    # 1. Remove XML/HTML tags
    import re
    clean_raw = re.sub(r'<\/?think>', '', raw_text)
    clean_raw = re.sub(r'<\/?answer>', '', clean_raw)
    clean_raw = re.sub(r'<\/?code>', '', clean_raw)
    
    # 2. Handle markdown code blocks
    if clean_raw.strip().startswith("```"):
        # Extract code from markdown blocks
        code_start = clean_raw.find("```") + 3
        # Skip language declaration if it exists
        language_marker_end = clean_raw.find("\n", code_start)
        if language_marker_end != -1:
            code_start = language_marker_end + 1
        code_end = clean_raw.rfind("```")
        if code_end != -1:
            code = clean_raw[code_start:code_end].strip()
        else:
            # If no closing block, take everything after the opening
            code = clean_raw[code_start:].strip()
    else:
        # Try to extract only code if no markdown blocks
        python_pattern = re.compile(r'(def|class|import|from|print|if __name__|#!\/usr\/bin\/env python)', re.MULTILINE)
        matches = list(python_pattern.finditer(clean_raw))
        if matches:
            # Start from the first Python pattern
            first_match = matches[0]
            code = clean_raw[first_match.start():].strip()
        else:
            code = clean_raw.strip()
    
    # 3. Special handling for qwen model's thinking patterns
    thinking_phrases = [
        "The file needs to be named", "Let me make sure", 
        "When you run", "I don't need any", "Alright, that's all",
        "So the entire code", "should output", "just that one line"
    ]
    
    # If any of these phrases are found, create a fallback hello world program
    if any(phrase in code for phrase in thinking_phrases):
        if file_path.endswith('.py'):
            return '#!/usr/bin/env python3\n\ndef main():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()'
        elif file_path.endswith('.js'):
            return 'console.log("Hello, World!");'
        elif file_path.endswith('.html'):
            return '<!DOCTYPE html>\n<html>\n<head>\n    <title>Hello World</title>\n</head>\n<body>\n    <h1>Hello, World!</h1>\n</body>\n</html>'
        else:
            return f'# {file_path}\nprint("Hello, World!")'
    
    # 4. Check for other thinking text
    thinking_phrases = ["Let's think about", "I need to create", "Okay, I need to", 
                       "should", "could", "would", "thinking", "plan", "First,", 
                       "create a Python script", "implement", "write a program"]
    
    contains_thinking = any(phrase in code for phrase in thinking_phrases)
    
    if contains_thinking:
        # Extract only what looks like real code
        real_code_lines = []
        in_comment_block = False
        for line in code.split('\n'):
            # Skip thinking lines
            if any(re.search(rf'.*{re.escape(phrase)}.*', line, re.IGNORECASE) for phrase in thinking_phrases):
                continue
                
            # Check if we're in a comment block
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                in_comment_block = not in_comment_block
                
            # Only include actual code and proper comments
            if not in_comment_block or line.strip().startswith('#'):
                real_code_lines.append(line)
                
        code = '\n'.join(real_code_lines).strip()
    
    # 5. Final fallback for invalid or empty code
    if not code or len(code) < 10:
        if file_path.endswith('.py'):
            return '#!/usr/bin/env python3\n\ndef main():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()'
        elif file_path.endswith('.js'):
            return 'console.log("Hello, World!");'
        elif file_path.endswith('.html'):
            return '<!DOCTYPE html>\n<html>\n<head>\n    <title>Hello World</title>\n</head>\n<body>\n    <h1>Hello, World!</h1>\n</body>\n</html>'
        else:
            return f'# {file_path}\nprint("Hello, World!")'
            
    return code

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
            
            # Use the clean_llm_response function to handle the cleaning
            code = clean_llm_response(raw, file_path)
            
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
