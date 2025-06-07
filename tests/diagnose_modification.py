# diagnose_code_modification.py
# debug_knowledge_base.py
from i2c.bootstrap import initialize_environment
initialize_environment()
import json
import re
import ast
from pathlib import Path
from typing import Dict, Optional, Any

from i2c.agents.modification_team.code_modification_manager_agno import (
    build_code_modification_team,
    ModificationRequest,
    AnalysisResult
)
from i2c.cli.controller import canvas

def clean_and_validate_code(code: str) -> Optional[str]:
    """Clean and validate the code."""
    # Remove leading/trailing whitespace
    code = code.strip()
    
    # Check for duplicated content
    half_length = len(code) // 2
    if half_length > 20:
        first_half = code[:half_length].strip()
        second_half = code[half_length:].strip()
        if first_half and first_half == second_half:
            code = first_half
            canvas.info("Removed duplicated content (exact match)")
    
    # Check if code parses
    try:
        ast.parse(code)
        return code
    except SyntaxError as e:
        canvas.warning(f"Code has syntax errors: {e}")
        return None

def diagnose_modification():
    """Run a complete diagnostic on the code modification process."""
    # Test case: Simple function with a greeting
    original_code = """def greeting(name):
    \"\"\"
    Returns a personalized greeting message.
    Args:
        name (str): The name of the person to greet.
    Returns:
        str: A greeting message with the provided name.
    \"\"\"
    return f"Hello, {name}!"
"""
    
    canvas.info("=" * 60)
    canvas.info("DIAGNOSTIC: CODE MODIFICATION PROCESS")
    canvas.info("=" * 60)
    
    # Step 1: Validate the original code
    canvas.info("STEP 1: Validating original code")
    if clean_and_validate_code(original_code):
        canvas.info("✅ Original code is valid Python")
    else:
        canvas.error("❌ Original code is not valid Python")
    
    # Step 2: Create and inspect the modification team
    canvas.info("\nSTEP 2: Creating and inspecting the modification team")
    team = build_code_modification_team()
    canvas.info(f"Team type: {type(team)}")
    
    # Step 3: Create the modification request
    canvas.info("\nSTEP 3: Creating modification request")
    request = ModificationRequest(
        project_root="/test",
        user_prompt="""{"file": "greeting.py", "what": "add title parameter to greeting function", "how": "Add a title parameter to the greeting function that prepends the title to the name if provided"}""",
        rag_context=""
    )
    canvas.info(f"Request: {request}")
    
    # Step 4: Run the modification
    canvas.info("\nSTEP 4: Running modification")
    analysis = AnalysisResult(details="")
    plan = team.modify(request, analysis)
    canvas.info(f"Plan type: {type(plan)}")
    canvas.info(f"Diff hints length: {len(plan.diff_hints)} chars")
    canvas.info(f"Diff hints preview: {plan.diff_hints[:200]}...")
    
    # Step 5: Parse the result
    canvas.info("\nSTEP 5: Parsing the result")
    try:
        result = json.loads(plan.diff_hints)
        canvas.info(f"Result keys: {list(result.keys())}")
        
        if "modified" in result:
            modified_code = result["modified"]
            canvas.info(f"Modified code length: {len(modified_code)} chars")
            canvas.info(f"Modified code preview: {modified_code[:200]}...")
            
            # Validate the modified code
            if clean_and_validate_code(modified_code):
                canvas.info("✅ Modified code is valid Python")
            else:
                canvas.error("❌ Modified code is not valid Python")
        else:
            canvas.warning("No 'modified' key in result")
    except Exception as e:
        canvas.error(f"Error parsing JSON: {str(e)}")
    
    canvas.info("=" * 60)
    canvas.info("DIAGNOSTIC COMPLETE")
    canvas.info("=" * 60)

if __name__ == "__main__":
    diagnose_modification()