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

        # Build Prompt with RAG Context
        plan_prompt = (
            f"Project Path: {project_path}\n"
            f"Language: {language}\n\n"
            f"{retrieved_context_plan}\n\n" # Include retrieved context string
            f"User Request: {request_detail}\n\n"
            f"Based on the user request and ONLY the relevant context provided above (if any), "
            f"provide a detailed modification plan as a JSON list of steps "
            f"(keys: 'file', 'action', 'what', 'how'), adhering strictly to valid JSON format with double quotes:"
        )

        # Use direct agent call (error handling is outside this function for now)
        response = modification_planner_agent.run(plan_prompt)
        content = response.content if hasattr(response, 'content') else str(response)

        # Parse and Validate JSON Plan
        try:
            content_processed = content.strip()
            if content_processed.startswith("```json"): content_processed = content_processed[len("```json"):].strip()
            if content_processed.startswith("```"): content_processed = content_processed[3:].strip()
            if content_processed.endswith("```"): content_processed = content_processed[:-3:].strip()
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

