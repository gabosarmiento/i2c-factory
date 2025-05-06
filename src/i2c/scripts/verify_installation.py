# src/i2c/scripts/verify_installation.py
"""Verify Feature Pipeline installation and functionality"""

import sys
from pathlib import Path
from dotenv import load_dotenv
from i2c.bootstrap import initialize_environment, PROJECT_ROOT

# 1) Bootstrap env & builtins (incl. PROJECT_ROOT)
initialize_environment()

# 2) Load any .env in the project root
load_dotenv(PROJECT_ROOT / ".env")

def verify_installation():
    """Verify all components are properly installed"""
    checks = []

    # Base package directory
    pkg_root = PROJECT_ROOT / "src" / "i2c"

    # 3) Check file structure
    required_files = [
        "models/user_story.py",
        "story_manager.py",
        "workflow/feature_pipeline.py",
        "workflow/feature_integration.py",
        "cli/rich_output.py",
        "cli/demo.py",
        "agents/knowledge/knowledge_manager.py",
        "agents/knowledge/documentation_retriever.py",
        "agents/knowledge/best_practices_agent.py",
    ]
    print("=== Verifying File Structure ===")
    for rel in required_files:
        path = pkg_root / rel
        if path.exists():
            print(f"✅ {rel}")
            checks.append(True)
        else:
            print(f"❌ {rel} — not found at {path}")
            checks.append(False)

    # 4) Check imports
    print("\n=== Verifying Imports ===")
    try:
        from i2c.models.user_story import UserStory
        print("✅ UserStory model imports correctly")
        checks.append(True)
    except ImportError as e:
        print(f"❌ UserStory import failed: {e}")
        checks.append(False)

    try:
        from i2c.workflow.feature_pipeline import FeaturePipeline
        print("✅ FeaturePipeline imports correctly")
        checks.append(True)
    except ImportError as e:
        print(f"❌ FeaturePipeline import failed: {e}")
        checks.append(False)

    # 5) Summary
    passed = sum(checks)
    total  = len(checks)
    print(f"\n=== Summary ===\nPassed: {passed}/{total} checks")
    if passed == total:
        print("✅ All checks passed! Feature Pipeline is ready to use.")
    else:
        print("❌ Some checks failed. Please fix the issues above.")

    return passed == total

if __name__ == "__main__":
    success = verify_installation()
    sys.exit(0 if success else 1)
