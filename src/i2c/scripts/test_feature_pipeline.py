# src/i2c/scripts/test_feature_pipeline.py
"""Test script for Feature Pipeline functionality"""

import os
from pathlib import Path
import groq
from i2c.bootstrap import initialize_environment, PROJECT_ROOT

# 1) Shared env & builtins bootstrap
initialize_environment()

# 2) Stub Groq run method if missing
# ─── AGNO Groq stub ───────────────────────────────────────────────
from agno.models.groq import Groq
from types import SimpleNamespace

# If AGNO.Groq doesn’t have create_completion, give it one that returns a minimal “choices+usage” shape
if not hasattr(Groq, "create_completion"):
    def _stub_create_completion(self, *, messages, max_tokens=None):
        # mirror the shape your pipeline expects
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="stub"))],
            usage=SimpleNamespace(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        )
    Groq.create_completion = _stub_create_completion

# Also alias chat→create_completion if your pipeline uses it
Groq.chat = Groq.create_completion


# ─── Embedder stub ────────────────────────────────────────────────
from sentence_transformers import SentenceTransformer

# Your pipeline calls get_embedding_and_usage(); if it's missing, fall back to .encode()
if not hasattr(SentenceTransformer, "get_embedding_and_usage"):
    def _stub_get_embedding_and_usage(self, text: str):
        vec = self.encode(text)
        return vec, SimpleNamespace(tokens=len(text.split()))
    SentenceTransformer.get_embedding_and_usage = _stub_get_embedding_and_usage

# 3) Environment variables for testing
os.environ['EMBEDDING_MODEL_NAME'] = 'all-MiniLM-L6-v2'
# Use PROJECT_ROOT for all output paths
os.environ['DEFAULT_PROJECT_ROOT'] = str(PROJECT_ROOT / 'test_output')

# 4) Absolute imports from our package
from i2c.workflow.feature_integration import FeatureIntegration
from i2c.agents.budget_manager import BudgetManagerAgent
from i2c.models.user_story import UserStory, AcceptanceCriteria, StoryPriority
from i2c.cli.controller import canvas
import json


def test_basic_functionality():
    """Test basic feature pipeline functionality"""
    print("\n=== Testing Basic Feature Pipeline Functionality ===\n")
    # Create test project directory under test_output
    project_path = PROJECT_ROOT / 'test_output' / 'feature_test'
    project_path.mkdir(parents=True, exist_ok=True)

    # Initialize budget manager with test budget
    budget_manager = BudgetManagerAgent(session_budget=0.5)  # $0.50 budget

    try:
        feature_integration = FeatureIntegration(project_path, budget_manager)
        print("✅ Feature integration initialized successfully")

        # Create a simple test story
        test_story = UserStory(
            title="Simple Calculator Function",
            description="Create a basic calculator function that can add two numbers",
            as_a="developer",
            i_want="a function that adds two numbers",
            so_that="I can perform basic arithmetic operations",
            acceptance_criteria=[
                AcceptanceCriteria(
                    description="Function accepts two numeric parameters",
                    verification_steps=["Test with integers", "Test with floats"]
                ),
                AcceptanceCriteria(
                    description="Function returns the sum of the two numbers",
                    verification_steps=["Verify correct sum calculation"]
                ),
                AcceptanceCriteria(
                    description="Function handles edge cases",
                    verification_steps=["Test with zero", "Test with negative numbers"]
                )
            ],
            priority=StoryPriority.MEDIUM,
            tags=["calculator", "arithmetic"]
        )

        # Save the story
        story_id = feature_integration.story_manager.create_story(test_story)
        print(f"✅ Created test story: {story_id}")

        # Update to READY status
        from i2c.models.user_story import StoryStatus
        feature_integration.story_manager.update_story_status(story_id, StoryStatus.READY)
        print(f"✅ Updated story status to READY")

        # Process the story
        print("\n🚀 Processing story through pipeline...")
        success, result = feature_integration.pipeline.process_story(story_id)

        if success:
            print("✅ Story processed successfully!")
            print("\n📊 Results:")
            print(json.dumps(result, indent=2, default=str))

            # Check generated files
            if "implementation" in result and "code_map" in result["implementation"]:
                print("\n📁 Generated files:")
                for file_path, content in result["implementation"]["code_map"].items():
                    print(f"  - {file_path}")
                    full_path = project_path / file_path
                    if full_path.exists():
                        print(f"    ✅ File exists at {full_path}")
                    else:
                        print(f"    ❌ File not found at {full_path}")
        else:
            print(f"❌ Story processing failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


def test_with_real_input():
    """Test with real user input simulation"""
    print("\n=== Testing with Real User Input ===\n")
    project_path = PROJECT_ROOT / 'test_output' / 'feature_test_real'
    project_path.mkdir(parents=True, exist_ok=True)
    budget_manager = BudgetManagerAgent(session_budget=1.0)  # $1.00 budget

    try:
        feature_integration = FeatureIntegration(project_path, budget_manager)
        user_input = "As a user, I want to upload images, so that I can share photos with my friends"
        print(f"📝 User input: {user_input}")
        result = feature_integration.handle_feature_request(user_input)
        if result.get("success"):
            print("✅ Feature request processed successfully!")
            print(f"Story ID: {result['story_id']}")
        else:
            print(f"❌ Feature request failed: {result.get('error')}")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


def test_cli_demo():
    """Test the CLI demo script"""
    print("\n=== Testing CLI Demo ===\n")
    try:
        from i2c.cli.demo import run_demo
        demo_path = PROJECT_ROOT / 'test_output' / 'demo_project'
        demo_path.mkdir(parents=True, exist_ok=True)
        print("Running demo with setup phase...")
        run_demo(demo_path, skip_setup=False)
    except Exception as e:
        print(f"❌ Demo test failed: {e}")
        import traceback
        traceback.print_exc()


def check_dependencies():
    """Check if all required dependencies are installed"""
    print("\n=== Checking Dependencies ===\n")
    dependencies = {
        'sentence_transformers': 'sentence-transformers',
        'rich': 'rich',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'lancedb': 'lancedb',
        'agno': 'agno',
        'jsonschema': 'jsonschema',
    }
    missing = []
    for module, package in dependencies.items():
        try:
            __import__(module)
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is NOT installed")
            missing.append(package)
    if missing:
        print(f"\n⚠️ Missing dependencies: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        return False
    return True


def main():
    """Main test runner"""
    print("🏭 i2c Factory Feature Pipeline Test Suite")
    print("=" * 50)
    if not check_dependencies():
        print("\n❌ Cannot proceed without required dependencies")
        return
    try:
        test_basic_functionality()
        test_with_real_input()
        # test_cli_demo()  # Uncomment to test full demo
        print("\n✅ All tests completed!")
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
