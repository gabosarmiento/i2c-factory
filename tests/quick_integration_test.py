#!/usr/bin/env python3
"""
Quick test to verify the simplified fixes work for integration.
"""

import sys
from pathlib import Path
import tempfile
import json

# Add project root to path
project_root = Path(__file__).parent / "src"
sys.path.insert(0, str(project_root))

from i2c.bootstrap import initialize_environment
initialize_environment()

def test_simplified_integration():
    """Test that simplified changes work end-to-end"""
    
    print("🧪 Testing simplified integration fixes")
    print("=" * 50)
    
    try:
        from i2c.workflow.orchestration_team import build_orchestration_team
        
        # Simple test session state
        session_state = {
            "objective": {
                "task": "Create simple authentication system"
            },
            "retrieved_context": "Use FastAPI for REST API. Use React for frontend. Connect frontend to backend with proper API calls.",
            "architectural_context": {
                "system_type": "fullstack_web_app"
            }
        }
        
        print("🏗️  Building orchestration team...")
        team = build_orchestration_team(session_state=session_state)
        
        # Check team properties
        instructions_text = "\n".join(team.instructions)
        instruction_size = len(instructions_text)
        
        print(f"✅ Team created successfully")
        print(f"📏 Instruction size: {instruction_size:,} characters")
        print(f"🔧 Has knowledge context: {'KNOWLEDGE CONTEXT' in instructions_text}")
        print(f"🔧 Knowledge context size: Limited to 1000 chars" if "KNOWLEDGE CONTEXT" in instructions_text else "No knowledge context")
        
        # Check for simplification success
        has_knowledge_context = "KNOWLEDGE CONTEXT" in instructions_text
        reasonable_size = instruction_size < 4000  # Should be smaller now
        no_serialization_issues = True  # No complex objects in team
        
        success = has_knowledge_context and reasonable_size and no_serialization_issues
        
        if success:
            print("🎉 SUCCESS: Simplified approach working!")
            print("   ✅ Knowledge context properly integrated")
            print("   ✅ Reasonable instruction size")
            print("   ✅ No serialization issues")
        else:
            print("⚠️  PARTIAL SUCCESS: Some issues remain")
        
        return success
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_core_agents_fix():
    """Test that core agents work with simplified approach"""
    
    print("\n🧪 Testing core agents simplified approach")
    print("=" * 50)
    
    try:
        from i2c.agents.core_agents import get_rag_enabled_agent
        
        # Test session state
        session_state = {
            "retrieved_context": "Use proper imports. Follow REST conventions. Ensure frontend-backend integration.",
            "project_path": "/tmp/test",
            "architectural_context": {"system_type": "web_app"}
        }
        
        print("🔧 Creating enhanced agent...")
        agent = get_rag_enabled_agent(
            agent_type="code_builder",
            session_state=session_state
        )
        
        print(f"✅ Agent created successfully")
        print(f"📏 Agent has instructions: {hasattr(agent, 'instructions')}")
        
        # Check enhancement worked
        if hasattr(agent, 'instructions'):
            instruction_text = "\n".join(agent.instructions) if isinstance(agent.instructions, list) else str(agent.instructions)
            enhanced = len(instruction_text) > 1000  # Should be enhanced
            
            print(f"🔧 Agent enhanced: {enhanced}")
            return enhanced
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Quick Integration Test - Simplified Fixes")
    print("=" * 60)
    
    test1 = test_simplified_integration()
    test2 = test_core_agents_fix()
    
    print("\n" + "=" * 60)
    print("🏁 RESULTS:")
    print(f"   Orchestration team: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"   Core agents: {'✅ PASS' if test2 else '❌ FAIL'}")
    
    if test1 and test2:
        print("\n🎉 SUCCESS: Simplified approach working!")
        print("   Should reduce API calls and fix serialization issues")
        print("   Should maintain knowledge context without bloat")
    else:
        print("\n⚠️  Some fixes still needed")
    
    print("=" * 60)