#!/usr/bin/env python3
"""
SAFE DIAGNOSTIC TEST - Measures current prompt sizes without making changes.
This will help us understand the scope of the context accumulation problem.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from i2c.bootstrap import initialize_environment
initialize_environment()

from i2c.agents.core_agents import get_rag_enabled_agent
from i2c.workflow.scenario_processor import SessionKnowledgeBase

def simulate_session_state_growth():
    """Simulate how session_state grows during scenario execution"""
    
    print("=" * 60)
    print("🔍 PROMPT SIZE ANALYSIS - NO CHANGES TO SYSTEM")
    print("=" * 60)
    
    # Simulate minimal session state (like after knowledge steps)
    minimal_session_state = {
        "knowledge_base": "mock_knowledge_base", 
        "db": "mock_db",
        "embed_model": "mock_embed_model",
        "db_path": "./data/lancedb"
    }
    
    print(f"📊 Minimal session state: {len(minimal_session_state)} keys")
    
    # Simulate session state after initial generation 
    initial_gen_session_state = {
        **minimal_session_state,
        "architectural_context": {"system_type": "fullstack_web_app", "modules": {"backend": {}, "frontend": {}}},
        "system_type": "fullstack_web_app",
        "current_structured_goal": {"objective": "Build emotional intelligence system", "constraints": []},
        "project_path": "/test/project",
        "file_plan": ["backend/main.py", "frontend/src/App.jsx"],
        "code_map": {"backend/main.py": "# FastAPI app", "frontend/src/App.jsx": "// React app"},
        "retrieved_context": "Long retrieved context from knowledge base..." * 50,  # Simulate long context
        "knowledge_context": {"project_analysis": "Detailed analysis..." * 20},
        "generation_memory": ["step1", "step2", "step3"],
        "backend_api_routes": {"/api/health": "GET", "/api/users": "POST"},
        "api_route_summary": "Detailed API summary..." * 10
    }
    
    print(f"📊 After initial generation: {len(initial_gen_session_state)} keys")
    
    # Simulate session state after multiple agentic evolution steps
    evolved_session_state = {
        **initial_gen_session_state,
        "reflection_memory": [{"step": i, "success": True, "details": "Long details..." * 10} for i in range(5)],
        "modified_files": {"file1": "changes", "file2": "more changes", "file3": "even more changes"},
        "quality_results": {"issues": ["issue1", "issue2"], "metrics": "detailed metrics..." * 15},
        "sre_results": {"deployment": "ready", "tests": "passed", "details": "Long SRE analysis..." * 20},
        "reasoning_trajectory": ["reason1", "reason2", "reason3"] * 10
    }
    
    print(f"📊 After agentic evolution: {len(evolved_session_state)} keys")
    
    # Test prompt size for each scenario (WITHOUT actually creating agents)
    test_scenarios = [
        ("Minimal", minimal_session_state),
        ("After Initial Gen", initial_gen_session_state), 
        ("After Evolution", evolved_session_state)
    ]
    
    for scenario_name, session_state in test_scenarios:
        print(f"\n🧪 Testing {scenario_name}:")
        print(f"   Session keys: {len(session_state)}")
        
        # Calculate total session state size
        total_chars = 0
        for key, value in session_state.items():
            if isinstance(value, str):
                total_chars += len(value)
            elif isinstance(value, (list, dict)):
                total_chars += len(str(value))
        
        print(f"   Total session content: ~{total_chars:,} characters")
        
        # Estimate prompt impact
        if total_chars > 50000:
            print(f"   ⚠️  LARGE CONTEXT: May cause agent confusion")
        elif total_chars > 20000:
            print(f"   ⚠️  MEDIUM CONTEXT: Getting large")
        else:
            print(f"   ✅ REASONABLE SIZE")

def analyze_instruction_growth():
    """Analyze how agent instructions grow with enhancement"""
    
    print("\n" + "=" * 60)
    print("📋 INSTRUCTION GROWTH ANALYSIS")
    print("=" * 60)
    
    # Simulate what happens during agent enhancement
    base_instructions = [
        "Generate production-grade code",
        "Follow architectural patterns", 
        "Use best practices"
    ]
    
    # Simulate knowledge requirements being added
    knowledge_requirements = [
        "Use AGNO framework patterns from knowledge base",
        "Apply React component patterns for frontend",
        "Use FastAPI routing patterns for backend",
        "Follow TypeScript conventions for type safety",
        "Implement proper error handling based on examples"
    ] * 3  # Simulate multiple enhancements
    
    print(f"Base instructions: {len(base_instructions)} items")
    print(f"Knowledge requirements: {len(knowledge_requirements)} items")
    
    # This is what the enhancer does: requirements + current_instructions
    final_instructions = knowledge_requirements + base_instructions
    print(f"Final instructions: {len(final_instructions)} items")
    
    # Calculate total instruction text
    total_instruction_text = "\n".join(final_instructions)
    print(f"Total instruction text: {len(total_instruction_text):,} characters")
    
    if len(final_instructions) > 20:
        print("⚠️  INSTRUCTION BLOAT: Too many instructions may confuse agent")
    else:
        print("✅ Reasonable instruction count")

def identify_optimization_opportunities():
    """Identify what could be optimized"""
    
    print("\n" + "=" * 60)
    print("🎯 OPTIMIZATION OPPORTUNITIES")
    print("=" * 60)
    
    opportunities = [
        "1. CONTEXT FILTERING: Filter session_state keys per agent type",
        "2. CONTENT LIMITS: Limit size of accumulating keys like retrieved_context", 
        "3. INSTRUCTION DEDUP: Prevent duplicate knowledge requirements",
        "4. AGNO MEMORY: Store long-term learnings in AGNO memory instead of session_state",
        "5. SELECTIVE ENHANCEMENT: Only enhance agents that need knowledge context"
    ]
    
    for opportunity in opportunities:
        print(f"   {opportunity}")
    
    print("\n🚀 RECOMMENDED FIRST STEP:")
    print("   Test context filtering for CodeBuilderAgent only")
    print("   Measure: prompt size before/after, generation quality, performance")

if __name__ == "__main__":
    simulate_session_state_growth()
    analyze_instruction_growth()
    identify_optimization_opportunities()
    print("\n✅ Diagnostic complete - no changes made to system")