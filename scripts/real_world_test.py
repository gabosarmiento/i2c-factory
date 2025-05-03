# scripts/real_world_test.py
"""Real-world test of Feature Pipeline with actual LLM calls"""

import sys, os
from pathlib import Path
import time
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))
# Configure environment
os.environ['GROQ_API_KEY'] = 'your_groq_api_key_here'  # Replace with actual key
os.environ['EMBEDDING_MODEL_NAME'] = 'all-MiniLM-L6-v2'
from db_utils import (
    get_db_connection,
    get_or_create_table,
    TABLE_CODE_CONTEXT,
    SCHEMA_CODE_CONTEXT,
    TABLE_KNOWLEDGE_BASE,
    SCHEMA_KNOWLEDGE_BASE,
)
# kick off / open your LanceDB
db = get_db_connection()
code_table = get_or_create_table(db, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT)
kb_table   = get_or_create_table(db, TABLE_KNOWLEDGE_BASE, SCHEMA_KNOWLEDGE_BASE)
# 
# Setup path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))



def test_real_feature_implementation():
    """Test with real LLM calls and actual code generation"""
    print("=== Real-World Feature Pipeline Test ===")
    
    from workflow.feature_integration import FeatureIntegration
    from agents.budget_manager import BudgetManagerAgent
    from models.user_story import UserStory, AcceptanceCriteria, StoryPriority, StoryStatus
    
    # Setup
    project_path = Path("./real_test_output")
    project_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize with real budget
    budget_manager = BudgetManagerAgent(session_budget=2.0)  # $2 budget
    
    try:
        # Create feature integration
        feature_integration = FeatureIntegration(project_path, budget_manager)
    
        # Create a realistic user story
        real_story = UserStory(
            title="REST API Endpoint for User Profile",
            description="Create a REST API endpoint to retrieve and update user profile information",
            as_a="backend developer",
            i_want="to create GET and PUT endpoints for user profiles",
            so_that="frontend applications can manage user data",
            acceptance_criteria=[
                AcceptanceCriteria(
                    description="GET /api/users/{id}/profile returns user profile data",
                    verification_steps=[
                        "Send GET request with valid user ID",
                        "Verify response includes name, email, and bio",
                        "Verify 404 response for non-existent user"
                    ]
                ),
                AcceptanceCriteria(
                    description="PUT /api/users/{id}/profile updates user profile",
                    verification_steps=[
                        "Send PUT request with updated profile data",
                        "Verify data is saved correctly",
                        "Verify validation for required fields"
                    ]
                ),
                AcceptanceCriteria(
                    description="Endpoints require authentication",
                    verification_steps=[
                        "Test requests without auth token return 401",
                        "Test requests with valid token succeed"
                    ]
                )
            ],
            priority=StoryPriority.HIGH,
            tags=["api", "user-management", "backend"]
        )
        
        # Save and process story
        story_id = feature_integration.story_manager.create_story(real_story)
        feature_integration.story_manager.update_story_status(story_id, StoryStatus.READY)
        
        print(f"📝 Created story: {story_id}")
        print(f"🚀 Processing story with real LLM calls...")
        
        start_time = time.time()
        success, result = feature_integration.pipeline.process_story(story_id)
        duration = time.time() - start_time
        
        if success:
            print(f"✅ Story processed successfully in {duration:.2f} seconds")
            
            # Check generated files
            if "implementation" in result and "code_map" in result["implementation"]:
                print("\n📁 Generated files:")
                for file_path, content in result["implementation"]["code_map"].items():
                    full_path = project_path / file_path
                    print(f"\n=== {file_path} ===")
                    print(content[:500] + "..." if len(content) > 500 else content)
                    
                    # Verify file exists
                    if full_path.exists():
                        print(f"✅ File created at {full_path}")
                    else:
                        print(f"❌ File not found at {full_path}")
        else:
            print(f"❌ Processing failed: {result.get('error')}")
        
        # Show budget usage
        tokens, cost = budget_manager.get_session_consumption()
        print(f"\n💰 Total cost: ${cost:.4f} ({tokens} tokens)")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_real_feature_implementation()