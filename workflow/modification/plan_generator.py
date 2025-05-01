# /workflow/modification/plan_generator.py
# Handles generating the modification plan using the planner agent and RAG context.

import json
from pathlib import Path

# Import necessary agent INSTANCES
from agents.modification_team import modification_planner_agent
# Import CLI controller
from cli.controller import canvas

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

        # Build enhanced prompt with structured RAG Context section
        plan_prompt = (
            f"# Project Information\n"
            f"Project Path: {project_path}\n"
            f"Primary Language: {language}\n\n"
            
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
            modification_plan = json.loads(content_processed)

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
            for step in modification_plan:
                action = step.get('action', '').lower()
                if action not in ['create', 'modify', 'delete']:
                    raise ValueError(f"Invalid action type '{action}' in modification plan. Must be 'create', 'modify', or 'delete'.")

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