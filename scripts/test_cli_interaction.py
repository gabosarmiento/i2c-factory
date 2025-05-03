# scripts/test_cli_interaction.py
"""Test the CLI interaction flow"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def test_cli_interaction():
    """Test the enhanced CLI with feature pipeline"""
    from workflow.feature_integration import enhance_workflow_with_features
    
    # Get the enhanced session runner
    enhanced_run = enhance_workflow_with_features()
    
    print("=== Testing Enhanced CLI Interaction ===")
    print("Try these commands:")
    print("1. Create a new project")
    print("2. Use 'story As a user, I want login functionality, so that I can access my account'")
    print("3. Use 'f add password reset feature'")
    print("4. Use 'r' to refine")
    print("5. Use 'q' to quit")
    
    # Run the enhanced session
    enhanced_run()


if __name__ == "__main__":
    test_cli_interaction()