# scripts/test_feature_pipeline.py
"""Test script for Feature Pipeline functionality"""

import sys
import os
from pathlib import Path
import groq
if not hasattr(groq.Groq, "run"):
    groq.Groq.run = lambda *_, **__: {
        "choices": [{"message": {"content": "stub"}}]
    }

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Load LLMs and set builtins
from llm_providers import initialize_groq_providers
import builtins
(
    builtins.llm_highest,
    builtins.llm_middle,
    builtins.llm_small,
    builtins.llm_xs
) = initialize_groq_providers()

# Set environment variables
os.environ['EMBEDDING_MODEL_NAME'] = 'all-MiniLM-L6-v2'
os.environ['DEFAULT_PROJECT_ROOT'] = './test_output'

# Import required modules
from workflow.feature_integration import FeatureIntegration
from agents.budget_manager import BudgetManagerAgent
from models.user_story import UserStory, AcceptanceCriteria, StoryPriority
from cli.controller import canvas
import json


def test_basic_functionality():
    """Test basic feature pipeline functionality"""
    print("\n=== Testing Basic Feature Pipeline Functionality ===\n")
    
    # Create test project directory
    project_path = Path("./test_output/feature_test")
    project_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize budget manager with test budget
    budget_manager = BudgetManagerAgent(session_budget=0.5)  # $0.50 for testing
    
    try:
        # Initialize feature integration
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
        
        # Update story to READY status
        from models.user_story import StoryStatus
        feature_integration.story_manager.update_story_status(story_id, StoryStatus.READY)
        print(f"✅ Updated story status to READY")
        
        # Process the story
        print("\n🚀 Processing story through pipeline...")
        success, result = feature_integration.pipeline.process_story(story_id)
        
        if success:
            print("✅ Story processed successfully!")
            
            # Print results
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
    
    # Print budget usage
    tokens, cost = budget_manager.get_session_consumption()
    print(f"\n💰 Budget used: {tokens} tokens, ${cost:.4f}")


def test_with_real_input():
    """Test with real user input simulation"""
    print("\n=== Testing with Real User Input ===\n")
    
    project_path = Path("./test_output/feature_test_real")
    project_path.mkdir(parents=True, exist_ok=True)
    
    budget_manager = BudgetManagerAgent(session_budget=1.0)  # $1.00 for testing
    
    try:
        feature_integration = FeatureIntegration(project_path, budget_manager)
        
        # Simulate user input for a feature request
        user_input = "As a user, I want to upload images, so that I can share photos with my friends"
        
        print(f"📝 User input: {user_input}")
        result = feature_integration.handle_feature_request(user_input)
        
        if result["success"]:
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
        from cli.demo import run_demo
        demo_path = Path("./test_output/demo_project")
        demo_path.mkdir(parents=True, exist_ok=True)
        
        # Run demo with setup
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
    
    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Cannot proceed without required dependencies")
        return
    
    # Run tests
    try:
        test_basic_functionality()
        test_with_real_input()
        #test_cli_demo()  # Uncomment to test full demo
        
        print("\n✅ All tests completed!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()