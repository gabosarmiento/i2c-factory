# scripts/verify_installation.py
"""Verify Feature Pipeline installation and functionality"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))


def verify_installation():
    """Verify all components are properly installed"""
    checks = []
    
    # Check file structure
    required_files = [
        "models/user_story.py",
        "story_manager.py",
        "workflow/feature_pipeline.py",
        "workflow/feature_integration.py",
        "cli/rich_output.py",
        "cli/demo.py",
        "agents/knowledge/knowledge_manager.py",
        "agents/knowledge/documentation_retriever.py",
        "agents/knowledge/best_practices_agent.py"
    ]
    
    print("=== Verifying File Structure ===")
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"✅ {file_path}")
            checks.append(True)
        else:
            print(f"❌ {file_path} - NOT FOUND")
            checks.append(False)
    
    # Check imports
    print("\n=== Verifying Imports ===")
    try:
        from models.user_story import UserStory
        print("✅ UserStory model imports correctly")
        checks.append(True)
    except ImportError as e:
        print(f"❌ UserStory import failed: {e}")
        checks.append(False)
    
    try:
        from workflow.feature_pipeline import FeaturePipeline
        print("✅ FeaturePipeline imports correctly")
        checks.append(True)
    except ImportError as e:
        print(f"❌ FeaturePipeline import failed: {e}")
        checks.append(False)
    
    # Summary
    success_count = sum(checks)
    total_checks = len(checks)
    print(f"\n=== Summary ===")
    print(f"Passed: {success_count}/{total_checks} checks")
    
    if success_count == total_checks:
        print("✅ All checks passed! Feature Pipeline is ready to use.")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
    
    return success_count == total_checks


if __name__ == "__main__":
    verify_installation()