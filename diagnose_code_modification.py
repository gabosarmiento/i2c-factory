# diagnose_code_modification.py
"""
Integration script for diagnosing issues with the code modification system.
This script wraps your existing code with diagnostic tracking.
"""
# debug_knowledge_base.py
from i2c.bootstrap import initialize_environment
initialize_environment()


import os
import json
import time
from pathlib import Path
import traceback

# Import the diagnostic wrapper
from diagnostic_wrapper import initialize_diagnostics, save_diagnostics, track_api_call

# Initialize diagnostics
diagnostics = initialize_diagnostics()

# Import original components with minimal modifications
from i2c.agents.modification_team.code_modification_manager_agno import build_code_modification_team
from i2c.workflow.modification.code_modifier_adapter import apply_modification

# Test function to diagnose a simple modification
@track_api_call
def test_simple_modification():
    """Test a simple modification to diagnose timeouts."""
    print("\n=== Starting Simple Modification Test ===\n")
    
    # Create a temporary project directory
    project_dir = Path("./test_project")
    project_dir.mkdir(exist_ok=True)
    
    # Create a simple greetings.py file
    greetings_file = project_dir / "greetings.py"
    original_content = """
def greet(name):
    return f"Hello, {name}!"

def main():
    print(greet("World"))

if __name__ == "__main__":
    main()
"""
    greetings_file.write_text(original_content)
    
    # Create modification step
    modification_step = {
        "action": "modify",
        "file": "greetings.py",
        "what": "Add title parameter",
        "how": "Add a title parameter to the greet function that prepends the title to the name if provided"
    }
    
    # Run the modification with timing
    start_time = time.time()
    try:
        print(f"Applying modification to {greetings_file}...")
        result = apply_modification(
            modification_step=modification_step,
            project_path=project_dir,
            retrieved_context=""
        )
        
        duration = time.time() - start_time
        print(f"Modification completed in {duration:.2f} seconds")
        
        # Check the result
        if hasattr(result, 'unified_diff'):
            print(f"SUCCESS: Got unified diff ({len(result.unified_diff)} chars)")
            print(f"Preview: {result.unified_diff[:200]}...")
        else:
            print(f"WARNING: Unexpected result type: {type(result)}")
            print(f"Result: {result}")
        
        return {
            "success": True,
            "duration": duration,
            "result": result
        }
    except Exception as e:
        duration = time.time() - start_time
        error_details = {
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc(),
            "duration": duration
        }
        print(f"ERROR: {type(e).__name__}: {e}")
        print(traceback.format_exc())
        return {
            "success": False,
            "duration": duration,
            "error": error_details
        }
    finally:
        # Save diagnostics immediately
        save_diagnostics()

# Helper to analyze diagnostics
def analyze_diagnostics():
    """Analyze the collected diagnostic data."""
    print("\n=== Diagnostic Analysis ===\n")
    
    try:
        with open("i2c_diagnostics.json", "r") as f:
            data = json.load(f)
        
        # Analyze API calls
        api_calls = data.get("api_calls", [])
        print(f"Total API calls: {len(api_calls)}")
        
        # Group by function
        function_counts = {}
        for call in api_calls:
            func = call["data"]["function"]
            function_counts[func] = function_counts.get(func, 0) + 1
        
        print("\nAPI calls by function:")
        for func, count in sorted(function_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {func}: {count} calls")
        
        # Analyze timeouts
        timeouts = data.get("timeouts", [])
        print(f"\nTotal timeouts: {len(timeouts)}")
        
        if timeouts:
            print("\nTimeout details:")
            for timeout in timeouts:
                func = timeout["data"]["function"]
                duration = timeout["data"]["duration"]
                print(f"  {func}: timed out after {duration:.2f} seconds")
        
        # Analyze prompt sizes
        prompt_sizes = data.get("prompt_sizes", [])
        if prompt_sizes:
            print("\nPrompt sizes:")
            for prompt in prompt_sizes:
                func = prompt["data"]["function"]
                length = prompt["data"]["length"]
                tokens = prompt["data"]["estimated_tokens"]
                print(f"  {func}: {length} chars (~{tokens} tokens)")
        
        # Analyze memory usage
        memory_snapshots = data.get("memory_snapshots", [])
        if memory_snapshots and len(memory_snapshots) >= 2:
            first = memory_snapshots[0]["data"]
            last = memory_snapshots[-1]["data"]
            
            print("\nMemory usage:")
            print(f"  Initial: {first.get('rss_mb', 0):.2f} MB")
            print(f"  Final: {last.get('rss_mb', 0):.2f} MB")
            print(f"  Difference: {(last.get('rss_mb', 0) - first.get('rss_mb', 0)):.2f} MB")
        
        return data
    except Exception as e:
        print(f"Error analyzing diagnostics: {e}")
        return None

# Main function
def main():
    """Run diagnostic tests and analyze results."""
    print("=== Code Modification Diagnostics ===")
    print("Running diagnostics...")
    
    # Run the test
    result = test_simple_modification()
    
    # Analyze the results
    analysis = analyze_diagnostics()
    
    # Save final results
    with open("modification_diagnostics_results.json", "w") as f:
        json.dump({
            "test_result": result,
            "analysis_summary": {
                "api_call_count": len(analysis.get("api_calls", [])),
                "timeout_count": len(analysis.get("timeouts", [])),
                "error_count": len(analysis.get("errors", []))
            }
        }, f, indent=2, default=str)
    
    print("\nDiagnostics complete. Results saved to:")
    print("- i2c_diagnostics.json (detailed logs)")
    print("- modification_diagnostics_results.json (summary)")

if __name__ == "__main__":
    main()