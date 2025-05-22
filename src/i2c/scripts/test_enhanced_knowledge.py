# test_enhanced_knowledge.py
from i2c.bootstrap import initialize_environment
initialize_environment()
import asyncio
from pathlib import Path
from i2c.agents.knowledge.knowledge_team import build_knowledge_team
from i2c.agents.budget_manager import BudgetManagerAgent

async def test_enhanced_knowledge():
    """Test the enhanced knowledge system"""
    
    # Create session state with required components
    session_state = {
        "budget_manager": BudgetManagerAgent(session_budget=5.0),
        "knowledge_space": "test_project",
        "project_context": None,
        "db_path": "./data/lancedb"
    }
    
    # Build knowledge team
    knowledge_team = build_knowledge_team(session_state=session_state)
    
    # Get the lead agent
    lead_agent = knowledge_team.members[0]
    
    # Test documentation ingestion
    docs_path = Path("/Users/caroco/Gabo-Dev/idea_to_code_factory/src/i2c/docs")  # Change to your actual docs path
    if docs_path.exists():
        print("🔄 Testing enhanced knowledge ingestion...")
        
        # First run - should process all files
        result1 = await lead_agent.ingest_project_documentation(docs_path, force_refresh=False)
        print(f"First run: {result1}")
        
        # Second run - should use cache
        result2 = await lead_agent.ingest_project_documentation(docs_path, force_refresh=False)
        print(f"Second run (cached): {result2}")
        
        print("✅ Test completed!")
    else:
        print(f"❌ Docs path {docs_path} not found")

if __name__ == "__main__":
    asyncio.run(test_enhanced_knowledge())