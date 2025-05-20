# workflow/modification/plan_generator.py
# Handles generating the modification plan using the planner agent and RAG context.

import json, re
from pathlib import Path

# Import necessary agent INSTANCES
from i2c.agents.modification_team import modification_planner_agent
# Import CLI controller
from i2c.cli.controller import canvas

def _safe_json_load(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        # common error: unescaped double-quotes inside 'how'
        fixed = re.sub(r'("how"\\s*:\\s*")([^"]*?)(".*?")',
                       lambda m: m.group(1) + m.group(2).replace('"', '\\"') + m.group(3),
                       raw, count=1)
        return json.loads(fixed)

def generate_modification_plan(user_request: str, retrieved_context_plan: str, project_path: Path, language: str) -> list[dict] | None:
    """
    Constructs the prompt and calls the ModificationPlannerAgent to get the plan.

    Args:
        user_request: The raw user request ('r' or 'f ...').
        retrieved_context_plan: Formatted string of context retrieved via RAG for planning.
        project_path: Path to the project.
        language: Primary language of the project.

    Returns:
        The parsed modification plan (list of dicts) or None on failure.
    """
    canvas.step("Planning modifications (using retrieved context)...")
    modification_plan = None

    try:
        # Interpret the user request for the prompt
        if user_request.lower() == 'r':
            request_detail = "Refine the existing project based on its current state and purpose."
        elif user_request.lower().startswith('f '):
            request_detail = f"Implement feature: {user_request[len('f '):].strip()}"
        else:
            request_detail = f"Process request: {user_request}"
        
        # Get list of existing files to include in the prompt
        existing_files = []
        for file_path in project_path.glob("**/*"):
            if file_path.is_file():
                try:
                    rel_path = file_path.relative_to(project_path)
                    existing_files.append(str(rel_path))
                except ValueError:
                    continue
        
        file_list_str = "\n".join(existing_files) if existing_files else "No files found in project."

        # Build enhanced prompt with structured RAG Context section
        plan_prompt = (
            f"# Project Information\n"
            f"Project Path: {project_path}\n"
            f"Primary Language: {language}\n\n"
            
            f"# Existing Project Files\n"
            f"{file_list_str}\n\n"
            
            f"# User Request\n"
            f"{request_detail}\n\n"
            
            f"# Retrieved Context\n"
            f"{retrieved_context_plan}\n\n"
            
            f"# Planning Instructions\n"
            f"1. Analyze the context above to understand the project structure and patterns\n"
            f"2. Identify which components need to be modified to fulfill the user request\n"
            f"3. Create a detailed, step-by-step modification plan as a valid JSON list\n"
            f"4. Ensure each step specifies exactly what file to modify/create/delete and how\n"
            f"5. Make your plan comprehensive yet minimal - include only necessary changes\n"
            f"6. IMPORTANT: Only reference files that exist in the 'Existing Project Files' list for 'modify' or 'delete' actions\n"
        )

        # Use direct agent call (error handling is outside this function for now)
        response = modification_planner_agent.run(plan_prompt)
        content = response.content if hasattr(response, 'content') else str(response)

        # Parse and Validate JSON Plan
        try:
            # Enhanced content cleaning to handle different LLM output formats
            content_processed = content.strip()
            
            # Handle potential markdown code blocks
            if "```json" in content_processed:
                # Extract content between ```json and ``` markers
                start_idx = content_processed.find("```json") + len("```json")
                end_idx = content_processed.find("```", start_idx)
                if end_idx != -1:
                    content_processed = content_processed[start_idx:end_idx].strip()
            elif "```" in content_processed:
                # Extract content between ``` markers (no language specified)
                start_idx = content_processed.find("```") + len("```")
                end_idx = content_processed.find("```", start_idx)
                if end_idx != -1:
                    content_processed = content_processed[start_idx:end_idx].strip()
            
            # Additional cleaning
            # Remove any non-JSON text before/after the JSON content
            open_bracket_idx = content_processed.find("[")
            close_bracket_idx = content_processed.rfind("]")
            if open_bracket_idx != -1 and close_bracket_idx != -1 and close_bracket_idx > open_bracket_idx:
                content_processed = content_processed[open_bracket_idx:close_bracket_idx+1]
            
            # Parse JSON
            modification_plan = _safe_json_load(content_processed)

            # Complete Validation Logic
            if not isinstance(modification_plan, list) or not all(
                isinstance(step, dict) and
                all(k in step for k in ['file', 'action', 'what', 'how']) and
                isinstance(step.get('file'), str) and
                isinstance(step.get('action'), str) and
                isinstance(step.get('what'), str) and
                isinstance(step.get('how'), str)
                for step in modification_plan
            ):
                raise ValueError("LLM response was not a valid list of modification step objects.")

            # Validate action types
            # Validate file existence for non-create actions
            for step in modification_plan:
                action = step.get('action', '').lower()
                file_path = step.get('file', '')
                
                # Skip validation for 'create' actions since those files don't exist yet
                if action != 'create':
                    full_path = project_path / file_path
                    if not full_path.exists():
                        # Look for similar files as alternatives
                        similar_files = []
                        for existing in existing_files:
                            # If the base filename is similar, suggest it as an alternative
                            if Path(existing).name.lower() == Path(file_path).name.lower():
                                similar_files.append(existing)
                            elif Path(existing).name.lower() in Path(file_path).name.lower() or Path(file_path).name.lower() in Path(existing).name.lower():
                                similar_files.append(existing)
                        
                        if similar_files:
                            # Use the first similar file as a replacement
                            original_path = step['file']
                            step['file'] = similar_files[0]
                            canvas.warning(f"File '{original_path}' doesn't exist. Replacing with similar file: '{similar_files[0]}'")
                        else:
                            canvas.error(f"File '{file_path}' specified in plan doesn't exist and no similar files found.")
                            # Option 1: Modify to create instead
                            if action == 'modify':
                                step['action'] = 'create'
                                canvas.warning(f"Changed action from 'modify' to 'create' for non-existent file: {file_path}")
                            # Option 2: Skip this step entirely
                            # modification_plan.remove(step)
                            # canvas.warning(f"Removed step targeting non-existent file: {file_path}")

            canvas.success(f"Generated modification plan with {len(modification_plan)} step(s).")
            return modification_plan # Return the valid plan

        except (json.JSONDecodeError, ValueError) as err:
            print(f"❌ [ModificationPlannerAgent] Failed to parse/validate JSON plan (Error: {err}).")
            canvas.error(f"DEBUG: Content that failed JSON parsing: {content[:500]}")
            # Let the exception propagate up
            raise err

    except Exception as e:
        # Let the exception propagate up
        canvas.error(f"Error during modification planning call: {e}")
        raise e