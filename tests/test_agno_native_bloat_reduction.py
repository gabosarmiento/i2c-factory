#!/usr/bin/env python3
"""
Test AGNO-native approach vs content consumption for context bloat reduction.
"""

import sys
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent / "src"
sys.path.insert(0, str(project_root))

# Initialize environment first
from i2c.bootstrap import initialize_environment
initialize_environment()

from i2c.workflow.orchestration_team import build_orchestration_team


class MockKnowledgeBase:
    """Mock knowledge base that simulates large content"""
    
    def retrieve_knowledge(self, query, limit=5):
        # Simulate large knowledge chunks (like the original bloat)
        large_content = "def example_function():\n    " + "# This is example code\n    " * 100
        
        return [
            {
                "source": "best_practices.md",
                "content": large_content
            },
            {
                "source": "patterns.md", 
                "content": large_content
            }
        ] * limit  # Multiply to simulate more chunks


def test_agno_native_vs_legacy():
    """Test AGNO-native approach vs legacy content consumption"""
    
    print("🧪 Testing AGNO-native knowledge access vs content consumption")
    print("=" * 70)
    
    # Sample objective and session state
    objective = {
        "task": "Create a user authentication system",
        "architectural_context": {
            "system_type": "fullstack_web_app",
            "architecture_pattern": "clean_architecture"
        }
    }
    
    session_state = {
        "objective": objective,
        "knowledge_base": MockKnowledgeBase(),
        "project_path": "/tmp/test"
    }
    
    print("📊 Building orchestration team with AGNO-native approach...")
    
    # Build team using AGNO-native approach (after our changes)
    try:
        team = build_orchestration_team(session_state=session_state)
        
        # Measure instruction size
        instructions_text = "\n".join(team.instructions)
        instruction_size = len(instructions_text)
        
        print(f"✅ Team created successfully")
        print(f"📏 Instruction size: {instruction_size:,} characters")
        print(f"🔧 Team has knowledge access: {team.knowledge is not None}")
        print(f"🔧 Agentic context enabled: {team.enable_agentic_context}")
        
        # Check for content bloat indicators
        has_knowledge_chunks = "[Knowledge " in instructions_text
        has_large_content = len(instructions_text) > 10000  # Arbitrary threshold
        
        print(f"🔍 Has knowledge chunks in instructions: {has_knowledge_chunks}")
        print(f"🔍 Instructions over 10KB: {has_large_content}")
        
        if not has_knowledge_chunks and not has_large_content:
            print("🎉 SUCCESS: AGNO-native approach eliminated content bloat!")
            print("   - No knowledge chunks embedded in instructions")
            print("   - Reasonable instruction size")
            print("   - Knowledge available through AGNO's native access")
            return True
        else:
            print("⚠️  WARNING: Some bloat indicators still present")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Team creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_session_state_bloat_reduction():
    """Test if session_state bloat is reduced in workflows"""
    
    print("\n🧪 Testing session state bloat reduction...")
    print("=" * 50)
    
    # Simulate the agentic_orchestrator pattern
    from i2c.workflow.agentic_orchestrator import execute_agentic_evolution
    import tempfile
    
    # Test objective
    objective = {
        "task": "Create a simple web app",
        "constraints": ["Use modern patterns"]
    }
    
    # Create session state with knowledge base
    session_state = {
        "knowledge_base": MockKnowledgeBase(),
        "project_path": "/tmp/test",
        "architectural_context": {"system_type": "fullstack_web_app"}
    }
    
    print("📊 Measuring session_state before and after workflow...")
    
    original_size = len(str(session_state))
    print(f"📏 Original session_state size: {original_size:,} characters")
    
    try:
        # Test if our changes prevent retrieved_context bloat
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # This should NOT create massive retrieved_context anymore
            result = await execute_agentic_evolution(
                objective=objective,
                project_path=project_path,
                session_state=session_state
            )
            
            # Check final session state
            final_session_state = result.get("session_state", session_state)
            final_size = len(str(final_session_state))
            
            print(f"📏 Final session_state size: {final_size:,} characters")
            
            # Check for retrieved_context bloat
            has_retrieved_context = "retrieved_context" in final_session_state
            if has_retrieved_context:
                retrieved_size = len(str(final_session_state["retrieved_context"]))
                print(f"📏 retrieved_context size: {retrieved_size:,} characters")
            else:
                print("✅ No retrieved_context in final session state")
            
            # Calculate growth
            growth = final_size - original_size
            growth_percent = (growth / original_size) * 100 if original_size > 0 else 0
            
            print(f"📈 Session state growth: {growth:,} chars ({growth_percent:.1f}%)")
            
            if growth < 5000:  # Reasonable growth threshold
                print("🎉 SUCCESS: Session state bloat is under control!")
                return True
            else:
                print("⚠️  WARNING: Significant session state growth detected")
                return False
                
    except Exception as e:
        print(f"❌ ERROR: Workflow test failed: {e}")
        return False


if __name__ == "__main__":
    import tempfile
    import asyncio
    
    print("🚀 Testing AGNO-native approach for context bloat reduction")
    print("=" * 70)
    
    # Test 1: Orchestration team bloat reduction
    test1_success = test_agno_native_vs_legacy()
    
    # Test 2: Session state bloat reduction  
    test2_success = asyncio.run(test_session_state_bloat_reduction()) if hasattr(asyncio, 'run') else False
    
    print("\n" + "=" * 70)
    print("🏁 FINAL RESULTS:")
    print(f"   Orchestration team bloat reduction: {'✅ PASS' if test1_success else '❌ FAIL'}")
    print(f"   Session state bloat reduction: {'✅ PASS' if test2_success else '❌ FAIL'}")
    
    if test1_success and test2_success:
        print("\n🎉 SUCCESS: AGNO-native approach successfully reduces context bloat!")
        print("   The system now uses dynamic knowledge access instead of content consumption.")
        print("   This should significantly improve performance and reduce agent confusion.")
    else:
        print("\n⚠️  Some tests failed - additional optimization may be needed.")
    
    print("=" * 70)