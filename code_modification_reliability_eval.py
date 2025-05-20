# code_modification_reliability_eval.py
# debug_knowledge_base.py
from i2c.bootstrap import initialize_environment
initialize_environment()
import json
from typing import Optional

from agno.eval.reliability import ReliabilityEval, ReliabilityResult
from agno.run.response import RunResponse

from i2c.agents.modification_team.code_modification_manager_agno import (
    build_code_modification_team,
    ModificationRequest,
    AnalysisResult
)
from i2c.cli.controller import canvas

def check_modification_reliability():
    # Create a simple Python function that needs modification
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
    
    # Create the modification team
    team = build_code_modification_team()
    
    # Add logging for team configuration
    try:
        canvas.info("=" * 40)
        canvas.info("TEAM CONFIGURATION:")
        canvas.info(f"Model: {team.team.model.id if team.team.model else 'None'}")
        canvas.info(f"Members: {[m.name for m in team.team.members]}")
        for member in team.team.members:
            canvas.info(f"Member {member.name} model: {member.model.id if member.model else 'None'}")
        canvas.info("=" * 40)
    except:
        pass
    
    # Define the modification request
    request = ModificationRequest(
        project_root="/test",
        user_prompt="""{"file": "greeting.py", "what": "add title parameter to greeting function", "how": "Add a title parameter to the greeting function that prepends the title to the name if provided"}""",
        rag_context=""
    )
    
    # Create an analyzer result (empty for simplicity)
    analysis = AnalysisResult(details="")
    
    # Capture the original team run response
    canvas.info("Running modification for reliability eval...")
    response = team.team.run("Modify the greeting function to add a title parameter")
    
    # Run the actual modification to see the result
    plan = team.modify(request, analysis)
    
    # Log the modification result
    canvas.info("=" * 40)
    canvas.info("MODIFICATION RESULT (DIFF HINTS):")
    canvas.info(plan.diff_hints[:500] + ("..." if len(plan.diff_hints) > 500 else ""))
    
    try:
        result = json.loads(plan.diff_hints)
        if "modified" in result:
            canvas.info("=" * 40)
            canvas.info("PARSED MODIFIED CODE:")
            canvas.info(result["modified"][:500] + ("..." if len(result["modified"]) > 500 else ""))
        else:
            canvas.warning("No 'modified' key in result")
    except Exception as e:
        canvas.error(f"Error parsing JSON: {str(e)}")
    
    canvas.info("=" * 40)
    
    # Create the reliability evaluation
    # We're looking for "analyze" and "modify" tool calls from the team members
    evaluation = ReliabilityEval(
        agent_response=response,
        expected_tool_calls=["analyze", "modify"],
    )
    
    # Run the evaluation
    result: Optional[ReliabilityResult] = evaluation.run(print_results=True)
    
    try:
        result.assert_passed()
        canvas.info("PASSED: All expected tool calls were made")
    except:
        canvas.warning("FAILED: Not all expected tool calls were made")
    
    return response

if __name__ == "__main__":
    check_modification_reliability()