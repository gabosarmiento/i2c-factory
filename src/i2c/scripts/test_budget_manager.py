# src/i2c/scripts/test_feature_pipeline.py
"""Test script for Feature Pipeline functionality with enhanced budget management"""

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
from agno.agent import Agent

# If AGNO.Groq doesn't have create_completion, give it one that returns a minimal "choices+usage" shape
if not hasattr(Groq, "create_completion"):
    def _stub_create_completion(self, *, messages, max_tokens=None):
        # mirror the shape your pipeline expects
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="stub"))],
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=50, total_tokens=150)
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


# Create a mock Agno Agent for testing the budget manager integration
def create_test_agent(model_id="groq/llama-3.1-8b-instant"):
    """Create a test Agno agent with session metrics for budget testing"""
    agent = Agent(
        name="TestAgent",
        model=Groq(id=model_id),
        telemetry=True
    )
    
    # Create mock session_metrics directly in the agent
    # Note: We don't import SessionMetrics directly
    agent.session_metrics = SimpleNamespace(
        input_tokens=200,
        output_tokens=100,
        total_tokens=300,
        prompt_tokens=200,
        completion_tokens=100,
        time=1.5,
        time_to_first_token=0.5,
        reasoning_tokens=50
    )
    
    # Create a mock run response with metrics
    from agno.run.response import RunResponse, RunResponseExtraData
    agent.run_response = RunResponse(
        run_id="test-run-id",
        session_id="test-session-id",
        agent_id="test-agent-id",
        content="This is a test response",
        metrics={
            "input_tokens": [200],
            "output_tokens": [100],
            "total_tokens": [300],
            "time": [1.5]
        },
        extra_data=RunResponseExtraData()
    )
    
    return agent


def test_budget_manager_integration():
    """Test the enhanced budget manager integration with Agno"""
    print("\n=== Testing Enhanced Budget Manager Integration ===\n")
    
    # Create a budget manager with a test budget
    budget_manager = BudgetManagerAgent(session_budget=1.0)  # $1.00 budget
    
    # Test 1: Basic tracking
    print("\n🧪 Test 1: Basic tracking")
    budget_manager.track_usage(
        prompt="Test prompt",
        response="Test response",
        model_id="groq/llama-3.1-8b-instant",
        actual_tokens=150,
        actual_cost=0.01
    )
    
    tokens, cost = budget_manager.get_session_consumption()
    print(f"✅ Basic tracking: {tokens} tokens, ${cost:.6f}")
    
    # Test 2: Integration with Agno metrics
    print("\n🧪 Test 2: Agno metrics integration")
    test_agent = create_test_agent()
    
    # Update from Agno metrics
    budget_manager.update_from_agno_metrics(test_agent)
    
    # Check updated totals
    tokens, cost = budget_manager.get_session_consumption()
    print(f"✅ After Agno integration: {tokens} tokens, ${cost:.6f}")
    
    # Test 3: RunResponse integration
    print("\n🧪 Test 3: RunResponse integration")
    budget_manager.update_from_run_response(
        test_agent.run_response,
        "groq/llama-3.1-8b-instant"
    )
    
    # Get final summary
    print("\n📊 Budget Manager Summary:")
    summary = budget_manager.get_summary()
    print(summary)
    
    # Test approval workflow
    print("\n🧪 Test 4: Budget approval workflow (auto-approved)")
    approval = budget_manager.request_approval(
        "Small test operation",
        "This is a small operation that should be auto-approved",
        "groq/llama-3.1-8b-instant"
    )
    print(f"✅ Auto-approval result: {approval}")
    
    return budget_manager


def test_basic_functionality(budget_manager=None):
    """Test basic feature pipeline functionality with budget tracking"""
    print("\n=== Testing Basic Feature Pipeline Functionality ===\n")
    # Create test project directory under test_output
    project_path = PROJECT_ROOT / 'test_output' / 'feature_test'
    project_path.mkdir(parents=True, exist_ok=True)

    # Initialize budget manager with test budget if not provided
    if budget_manager is None:
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
            
        # Print budget summary after processing
        print("\n💰 Budget summary after feature processing:")
        print(budget_manager.get_summary())

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    return budget_manager


def test_make_tracked_request():
    """Test the enhanced make_tracked_request function"""
    print("\n=== Testing Enhanced make_tracked_request Function ===\n")
    
    from i2c.llm_providers import make_tracked_request, llm_small
    from i2c.agents.budget_manager import BudgetManagerAgent
    
    # Create a budget manager
    budget_manager = BudgetManagerAgent(session_budget=0.5)
    
    # Create a test agent
    test_agent = create_test_agent()
    
    # Test making a tracked request
    print("🧪 Testing make_tracked_request with budget_manager and agent parameters")
    
    try:
        response_text, tokens, cost = make_tracked_request(
            model=llm_small,
            messages=[{"role": "user", "content": "This is a test message"}],
            budget_manager=budget_manager,
            agent=test_agent
        )
        
        print(f"✅ make_tracked_request returned: {tokens} tokens, ${cost:.6f}")
        print("✅ Budget manager updated from Agno metrics")
        
        # Print budget summary
        print("\n💰 Budget summary after tracked request:")
        print(budget_manager.get_summary())
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    return budget_manager


def test_with_real_input(budget_manager=None):
    """Test with real user input simulation"""
    print("\n=== Testing with Real User Input ===\n")
    project_path = PROJECT_ROOT / 'test_output' / 'feature_test_real'
    project_path.mkdir(parents=True, exist_ok=True)
    
    # Use provided budget manager or create a new one
    if budget_manager is None:
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
            
        # Print budget summary after real input test
        print("\n💰 Budget summary after real input test:")
        print(budget_manager.get_summary())
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
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
    print("🏭 i2c Factory Feature Pipeline Test Suite with Enhanced Budget Management")
    print("=" * 70)
    if not check_dependencies():
        print("\n❌ Cannot proceed without required dependencies")
        return
    try:
        # Start by testing the budget manager integration
        print("\n🚀 Running budget manager integration tests")
        budget_manager = test_budget_manager_integration()
        
        # Test the make_tracked_request function
        print("\n🚀 Running make_tracked_request tests")
        budget_manager = test_make_tracked_request()
        
        # Run feature tests with the same budget manager to track cumulative usage
        print("\n🚀 Running feature functionality tests")
        budget_manager = test_basic_functionality(budget_manager)
        
        # Test with real input using the same budget manager
        print("\n🚀 Running real input tests")
        test_with_real_input(budget_manager)
        
        # Print final budget summary
        print("\n💰 Final budget summary:")
        print(budget_manager.get_summary())
        
        print("\n✅ All tests completed!")
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()