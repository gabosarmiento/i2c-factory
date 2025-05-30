# code_modification_eval.py
# debug_knowledge_base.py
from i2c.bootstrap import initialize_environment
initialize_environment()
from typing import Optional
import json
from agno.agent import Agent
from agno.eval.accuracy import AccuracyEval, AccuracyResult

from agno.team import Team

from i2c.agents.modification_team.code_modification_manager_agno import (
    build_code_modification_team,
    ModificationRequest,
    AnalysisResult,
    ModificationPlan
)

def test_simple_code_modification():
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
    
    # Define the expected modified code with a title parameter
    expected_code = """def greeting(name, title=None):
    \"\"\"
    Returns a personalized greeting message.
    Args:
        name (str): The name of the person to greet.
        title (Optional[str]): The title to prepend to the name.
    Returns:
        str: A greeting message with the provided name and optional title.
    \"\"\"
    if title:
        return f"Hello, {title} {name}!"
    return f"Hello, {name}!"
"""

    # Create the modification team
    team = build_code_modification_team()
    
    # Define the modification request
    request = ModificationRequest(
        project_root="/test",
        user_prompt="""{"file": "greeting.py", "what": "add title parameter to greeting function", "how": "Add a title parameter to the greeting function that prepends the title to the name if provided"}""",
        rag_context=""
    )
    
    # Create an analyzer result (empty for simplicity)
    analysis = AnalysisResult(details="")
    
    # Define a function that runs the modification
    def run_modification():
        # Run the modification
        plan = team.modify(request, analysis)
        
        # Parse the result
        try:
            from i2c.cli.controller import canvas
            canvas.info(f"Modification result: {plan.diff_hints}")
        except ImportError:
            print(f"Modification result: {plan.diff_hints}")
            
        try:
            result = json.loads(plan.diff_hints)
            return result.get("modified", "")
        except Exception as e:
            return f"Error parsing JSON: {str(e)}"
    
    # Create the evaluation
    evaluation = AccuracyEval(
        agent=None,  # Not using a standard agent here
        prompt="Evaluate if the modified code correctly adds a title parameter to the greeting function",
        expected_answer=expected_code,
        actual_answer_fn=run_modification,
        num_iterations=3  # Run multiple times to see consistency
    )
    
    # Run the evaluation
    result: Optional[AccuracyResult] = evaluation.run(print_results=True)
    
    # Assert the result
    if result is not None:
        print(f"Average score: {result.avg_score}")
        if result.avg_score < 7:
            print("FAILED: Code modification does not meet expectations")
        else:
            print("PASSED: Code modification meets expectations")


if __name__ == "__main__":
    test_simple_code_modification()