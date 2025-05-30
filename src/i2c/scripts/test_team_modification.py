# test_team_modification.py
from pathlib import Path
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("team_test")

def test_team_modification():
    """Test the team-based modification system"""
    logger.info("Testing team-based modification system...")
    
    # Create a test project
    test_dir = Path("./team_test_project")
    test_dir.mkdir(exist_ok=True)
    
    # Create a test file
    test_file = test_dir / "calculator.py"
    test_file.write_text("""
# Simple calculator module
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
    
# TODO: Add more functions
""")
    logger.info(f"✅ Created test file at {test_file}")
    
    # Import the adapter
    try:
        from i2c.agents.modification_team.code_modification_manager_agno import apply_modification
        logger.info("✅ Successfully imported adapter")
    except ImportError as e:
        logger.error(f"❌ Failed to import adapter: {e}")
        return False
    
    # Create a test modification step
    modification_step = {
        "file": "calculator.py",
        "action": "modify",
        "what": "Add multiply and divide functions",
        "how": "Add two new functions: multiply(a, b) that returns a * b and divide(a, b) that returns a / b with error handling for division by zero"
    }
    
    # Add some context
    context = """
This is a simple calculator module with basic arithmetic functions.
The code follows a functional programming style with no classes.
Each function takes two parameters and returns the result of the operation.
Functions should include docstrings and follow PEP 8 style guidelines.
"""
    
    # Apply the modification
    logger.info(f"Applying modification: {modification_step['what']}")
    result = apply_modification(
        modification_step=modification_step,
        project_path=test_dir,
        retrieved_context=context
    )
    
    # Check the result
    if isinstance(result, dict) and "error" in result:
        logger.error(f"❌ Modification failed: {result['error']}")
        return False
    
    logger.info(f"✅ Modification succeeded")
    logger.info(f"Unified diff:\n{result.unified_diff}")
    
    # Apply the changes to the file
    if hasattr(result, "unified_diff") and result.unified_diff:
        # Read the original file
        original = test_file.read_text()
        
        # Apply the diff (simplified)
        # In a real scenario, you'd use a proper diff application library
        # This is a simplified version that assumes the diff adds lines at the end
        new_content = original + "\n" + "\n".join([
            line[1:].strip() for line in result.unified_diff.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ])
        
        # Write the updated file
        test_file.write_text(new_content)
        logger.info(f"✅ Applied changes to {test_file}")
        logger.info(f"New content:\n{new_content}")
    
    logger.info("Test completed successfully.")
    return True

if __name__ == "__main__":
    test_team_modification()