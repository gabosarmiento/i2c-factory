# test_rag_integration_with_agno.py
from i2c.bootstrap import initialize_environment
initialize_environment()
import os
import re
from pathlib import Path
from i2c.workflow.scenario_processor import run_scenario

# After the knowledge step, add this check
def check_knowledge_loaded():
    from i2c.agents.knowledge.knowledge_manager import ExternalKnowledgeManager
    from i2c.workflow.modification.rag_config import get_embed_model
    
    embed_model = get_embed_model()
    knowledge_manager = ExternalKnowledgeManager(embed_model=embed_model)
    
    # Test retrieval
    results = knowledge_manager.retrieve_knowledge("AGNO agent team", limit=3)
    print(f"Knowledge test: Found {len(results)} chunks")
    for result in results:
        print(f"  - {result.get('source', 'Unknown')}: {result.get('content', '')[:100]}...")

check_knowledge_loaded()

def test_rag_integration():
    # Path to test scenario
    scenario_path = "test_scenarios/rag_test_scenario.json"
    
    # Create test directory
    os.makedirs(os.path.dirname(scenario_path), exist_ok=True)
    
    # Create test scenario
    with open(scenario_path, 'w') as f:
        f.write('''
{
  "name": "AGNO Integration Test",
  "steps": [
    {
      "type": "knowledge",
      "global": true,
      "name": "Add AGNO Knowledge",
      "doc_path": "src/i2c/docs/agno_cheat_sheet.pdf",
      "doc_type": "guide",
      "framework": "AGNO",
      "version": "1.0"
    },
    {
      "type": "initial_generation",
      "prompt": "Create a Python agent-based workflow using AGNO patterns. Implement a task prioritization agent and a task scheduling agent that work together to manage deadlines. Follow AGNO team collaboration patterns.",
      "project_name": "agno_workflow_test"
    }
  ]
}
        ''')
    
    # Run scenario
    print("Running RAG integration test scenario...")
    success = run_scenario(scenario_path, debug=True)
    
    if success:
      print("Checking if knowledge was loaded...")
      check_knowledge_loaded()
    
    # Validate results
    output_dir = Path("./output/agno_workflow_test")
    
    if success and output_dir.exists():
        print(f"✅ Scenario completed successfully")
        
        # Check for AGNO-specific patterns in code
        agno_patterns = [
            r'from agno\.agent import Agent',
            r'from agno\.team import Team',
            r'Agent\(',
            r'Team\(',
            r'model=.*',
            r'tools=\[',
            r'mode="(route|coordinate|collaborate)"',
            r'instructions='
        ]
        
        code_files = list(output_dir.glob("**/*.py"))
        print(f"Found {len(code_files)} Python files")
        
        # Count matches of AGNO patterns
        agno_pattern_matches = 0
        
        for file_path in code_files:
            with open(file_path, 'r') as f:
                content = f.read()
                for pattern in agno_patterns:
                    matches = re.findall(pattern, content)
                    agno_pattern_matches += len(matches)
        
        # Check log for RAG usage
        with open("scenario_debug.log", 'r') as f:
            log_content = f.read()
            rag_logs = re.findall(r'\[RAG\]', log_content)
        
        print(f"Found {agno_pattern_matches} AGNO pattern matches in code")
        print(f"Found {len(rag_logs)} RAG log entries")
        
        # Determine test result
        if agno_pattern_matches > 5 and rag_logs:
            print("✅ TEST PASSED: RAG integration successfully applied AGNO knowledge")
            return True
        else:
            print("❌ TEST FAILED: Not enough evidence of RAG integration")
            return False
    else:
        print("❌ TEST FAILED: Scenario execution failed")
        return False


if __name__ == "__main__":
    test_rag_integration()