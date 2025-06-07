import json
from pathlib import Path
from i2c.bootstrap import initialize_environment
initialize_environment()
from i2c.workflow.scenario_processor import ScenarioProcessor

def test_knowledge_accumulation():
    """Test to track knowledge accumulation through workflow steps"""
    
   
    
    # Create test scenario with multiple knowledge steps
    test_scenario = {
        "project_name": "test_knowledge_accumulation",
        "steps": [
            {
                "type": "knowledge",
                "name": "Load AGNO Knowledge", 
                "doc_path": "src/i2c/docs/agno_cheat_sheet.pdf",
                "doc_type": "AGNO Framework",
                "project_name": "test_knowledge_accumulation",
                "force_refresh": False
            },
            {
                "type": "initial_generation",
                "name": "Create API with 2 endpoints",
                "prompt": "Create FastAPI app with /health and /users endpoints using AGNO patterns",
                "project_name": "test_knowledge_accumulation"
            },
            {
                "type": "knowledge",
                "name": "Load More AGNO Knowledge",
                "doc_path": "src/i2c/docs/agno_guide.pdf", 
                "doc_type": "AGNO Advanced Guide",
                "project_name": "test_knowledge_accumulation",
                "force_refresh": False
            },
            {
                "type": "agentic_evolution",
                "objective": {
                    "task": "Add /posts endpoint using advanced AGNO patterns",
                    "constraints": ["Keep existing endpoints"]
                },
                "project_name": "test_knowledge_accumulation"
            }
        ]
    }
    
    # Save scenario
    scenario_path = Path("test_knowledge_scenario.json")
    with open(scenario_path, 'w') as f:
        json.dump(test_scenario, f, indent=2)
    
    # Run with knowledge tracking
    processor = ScenarioProcessor(str(scenario_path))
    
    # Hook into knowledge processing
    original_process_knowledge = processor._process_knowledge_step
    knowledge_evolution = []
    
    def track_knowledge_step(step):
        # Track before
        before_size = len(str(processor.session_state.get("knowledge_context", "")))
        before_retrieved = len(str(processor.session_state.get("retrieved_context", "")))
        
        # Run original
        result = original_process_knowledge(step)
        
        # Track after  
        after_size = len(str(processor.session_state.get("knowledge_context", "")))
        after_retrieved = len(str(processor.session_state.get("retrieved_context", "")))
        
        knowledge_evolution.append({
            "step": step.get("name", "Unknown"),
            "knowledge_context_before": before_size,
            "knowledge_context_after": after_size,
            "retrieved_context_before": before_retrieved,
            "retrieved_context_after": after_retrieved,
            "knowledge_growth": after_size - before_size,
            "retrieved_growth": after_retrieved - before_retrieved
        })
        
        return result
    
    processor._process_knowledge_step = track_knowledge_step
    
    # Run scenario
    processor.process_scenario()
    
    # Analyze knowledge accumulation
    print("=== KNOWLEDGE ACCUMULATION ANALYSIS ===")
    for step_data in knowledge_evolution:
        print(f"Step: {step_data['step']}")
        print(f"  Knowledge context: {step_data['knowledge_context_before']} → {step_data['knowledge_context_after']} (growth: {step_data['knowledge_growth']})")
        print(f"  Retrieved context: {step_data['retrieved_context_before']} → {step_data['retrieved_context_after']} (growth: {step_data['retrieved_growth']})")
        print()

if __name__ == "__main__":
    test_knowledge_accumulation()