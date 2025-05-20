# code_modification_perf_eval.py
# debug_knowledge_base.py
from i2c.bootstrap import initialize_environment
initialize_environment()
import json
from agno.eval.perf import PerfEval

from i2c.agents.modification_team.code_modification_manager_agno import (
    build_code_modification_team,
    ModificationRequest,
    AnalysisResult
)
from i2c.cli.controller import canvas

def run_simple_modification():
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
    
    # Define the modification request
    request = ModificationRequest(
        project_root="/test",
        user_prompt="""{"file": "greeting.py", "what": "add title parameter to greeting function", "how": "Add a title parameter to the greeting function that prepends the title to the name if provided"}""",
        rag_context=""
    )
    
    # Create an analyzer result (empty for simplicity)
    analysis = AnalysisResult(details="")
    
    # Run the modification
    canvas.info("Starting modification performance test...")
    plan = team.modify(request, analysis)
    
    # Log the result for inspection
    canvas.info("=" * 40)
    canvas.info("MODIFICATION RESULT:")
    canvas.info(plan.diff_hints[:500] + ("..." if len(plan.diff_hints) > 500 else ""))
    canvas.info("=" * 40)
    
    # Try to parse the result
    try:
        result = json.loads(plan.diff_hints)
        modified_code = result.get("modified", "")
        canvas.info(f"Modified code length: {len(modified_code)} chars")
        return modified_code
    except Exception as e:
        canvas.error(f"Error parsing JSON: {str(e)}")
        return f"Error: {str(e)}"

# Create the performance evaluation
mod_perf_eval = PerfEval(
    func=run_simple_modification,
    num_iterations=3,
    warmup_runs=1
)

if __name__ == "__main__":
    mod_perf_eval.run(print_results=True)