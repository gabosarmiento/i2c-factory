# src/i2c/scripts/test_cli_interaction.py
"""Test the CLI interaction flow"""

from i2c.bootstrap import initialize_environment

# 1) Shared env & builtins bootstrap (incl. TOKENIZERS_PARALLELISM, builtins.llm_*)
initialize_environment()

def test_cli_interaction():
    """Test the enhanced CLI with feature pipeline"""
    # Import enhancement function from the i2c package
    from i2c.workflow.feature_integration import enhance_workflow_with_features

    # Get the enhanced CLI session runner
    enhanced_run = enhance_workflow_with_features()

    print("=== Interactive Feature Pipeline CLI ===")
    print("Try these commands:")
    print("Use 'story As a user, I want login functionality, so that I can access my account'")
    print("Use 'f add password reset feature'")
    print("Use 'r' to refine")
    print("Use 'q' to quit")

    # Run the enhanced session
    enhanced_run()

if __name__ == "__main__":
    test_cli_interaction()

