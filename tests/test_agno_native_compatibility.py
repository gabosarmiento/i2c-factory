#!/usr/bin/env python3
"""
Test AGNO-native approach maintains full system compatibility.
Validates that our architectural changes work without breaking existing functionality.
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

def test_core_agents_agno_compatibility():
    """Test that core agents work with AGNO-native approach"""
    
    print("🧪 Testing core agents AGNO compatibility")
    print("=" * 50)
    
    try:
        from i2c.agents.core_agents import get_rag_enabled_agent
        
        # Mock knowledge base
        class MockKnowledgeBase:
            def retrieve_knowledge(self, query, limit=5):
                return [{"source": "test.md", "content": "test content"}]
        
        # Test session state with both old and new patterns
        session_state = {
            "knowledge_base": MockKnowledgeBase(),
            "retrieved_context": "legacy context content",
            "project_path": "/tmp/test",
            "architectural_context": {"system_type": "web_app"}
        }
        
        print("🔧 Creating RAG-enabled agent...")
        
        # This should work with AGNO-native approach
        agent = get_rag_enabled_agent(
            agent_type="code_builder",
            session_state=session_state,
            base_instructions=["Build code based on requirements"]
        )
        
        print(f"✅ Agent created successfully")
        print(f"📏 Agent has instructions: {hasattr(agent, 'instructions')}")
        print(f"🔍 Agent has knowledge access: {hasattr(agent, 'knowledge') or 'knowledge' in str(agent)}")
        
        # Check that instructions don't contain bloated content
        if hasattr(agent, 'instructions'):
            instructions_text = "\n".join(agent.instructions) if isinstance(agent.instructions, list) else str(agent.instructions)
            instruction_size = len(instructions_text)
            has_content_bloat = instruction_size > 10000  # Threshold
            
            print(f"📏 Instruction size: {instruction_size:,} characters")
            print(f"🔍 Has content bloat: {has_content_bloat}")
            
            return not has_content_bloat
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_orchestration_team_agno_native():
    """Test orchestration team AGNO-native approach"""
    
    print("\n🧪 Testing orchestration team AGNO-native")
    print("=" * 50)
    
    try:
        from i2c.workflow.orchestration_team import build_orchestration_team
        
        # Mock knowledge base
        class MockKnowledgeBase:
            def retrieve_knowledge(self, query, limit=5):
                large_content = "def example():\n    " + "# example code\n    " * 100
                return [{"source": "test.md", "content": large_content}] * limit
        
        session_state = {
            "objective": {
                "task": "Create authentication system",
                "architectural_context": {"system_type": "web_app"}
            },
            "knowledge_base": MockKnowledgeBase(),
            "project_path": "/tmp/test"
        }
        
        print("🏗️  Building orchestration team...")
        team = build_orchestration_team(session_state=session_state)
        
        # Analyze the team
        instructions_text = "\n".join(team.instructions)
        instruction_size = len(instructions_text)
        
        # Check for AGNO-native indicators
        has_agno_guidance = "knowledge base through the Team" in instructions_text
        has_content_chunks = "[Knowledge " in instructions_text
        has_knowledge_access = team.knowledge is not None
        has_agentic_context = getattr(team, 'enable_agentic_context', False)
        is_reasonable_size = instruction_size < 5000
        
        print(f"✅ Team created successfully")
        print(f"📏 Instruction size: {instruction_size:,} characters")
        print(f"🔧 AGNO guidance: {has_agno_guidance}")
        print(f"🔧 Content chunks: {has_content_chunks}")
        print(f"🔧 Knowledge access: {has_knowledge_access}")
        print(f"🔧 Agentic context: {has_agentic_context}")
        print(f"🔧 Reasonable size: {is_reasonable_size}")
        
        # Success criteria
        success = (
            has_agno_guidance and           # Has AGNO guidance
            not has_content_chunks and      # No content bloat
            has_knowledge_access and        # Knowledge available
            has_agentic_context and         # Agentic context enabled
            is_reasonable_size              # Reasonable size
        )
        
        if success:
            print("🎉 SUCCESS: Orchestration team uses AGNO-native approach perfectly!")
        else:
            print("⚠️  PARTIAL: Some AGNO-native features missing")
        
        return success
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backward_compatibility():
    """Test that existing patterns still work for compatibility"""
    
    print("\n🧪 Testing backward compatibility")
    print("=" * 50)
    
    try:
        from i2c.agents.core_team.enhancer import AgentKnowledgeEnhancer
        
        # Test that enhancer can still work with retrieved_context
        enhancer = AgentKnowledgeEnhancer()
        
        # Mock agent
        class MockAgent:
            def __init__(self):
                self.instructions = ["Initial instruction"]
        
        mock_agent = MockAgent()
        
        # Test enhancement with knowledge context
        enhanced_agent = enhancer.enhance_agent_with_knowledge(
            agent=mock_agent,
            knowledge_context="Test knowledge context for compatibility",
            agent_type="test_agent"
        )
        
        print(f"✅ Enhancement completed")
        print(f"🔧 Agent enhanced: {len(enhanced_agent.instructions) > 1}")
        
        # Test storage and retrieval
        session_state = {}
        enhancer.store_knowledge_context(
            session_state, 
            "Test stored context",
            "test_source"
        )
        
        stored_context = enhancer.get_knowledge_context(session_state)
        context_stored = stored_context == "Test stored context"
        
        print(f"🔧 Context storage works: {context_stored}")
        
        return len(enhanced_agent.instructions) > 1 and context_stored
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_validation_compatibility():
    """Test that validation still works with both patterns"""
    
    print("\n🧪 Testing validation compatibility")  
    print("=" * 50)
    
    try:
        from i2c.agents.knowledge.knowledge_validator import KnowledgeValidator
        
        validator = KnowledgeValidator()
        
        # Test with retrieved_context (legacy pattern)
        test_files = {"test.py": "def hello(): pass"}
        test_context = "Always use proper function naming"
        
        result = validator.validate_generation_output(
            generated_files=test_files,
            retrieved_context=test_context,
            task_description="Create a greeting function"
        )
        
        validation_works = hasattr(result, 'success') and hasattr(result, 'score')
        
        print(f"✅ Validation completed")
        print(f"🔧 Validation works: {validation_works}")
        print(f"🔧 Validation success: {result.success if validation_works else 'N/A'}")
        
        return validation_works
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def run_comprehensive_test():
    """Run all compatibility tests"""
    
    print("🚀 AGNO-Native Compatibility Test Suite")
    print("=" * 70)
    
    tests = [
        ("Core Agents AGNO Compatibility", test_core_agents_agno_compatibility),
        ("Orchestration Team AGNO-Native", test_orchestration_team_agno_native),
        ("Backward Compatibility", test_backward_compatibility),
        ("Validation Compatibility", test_validation_compatibility)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ TEST FAILED: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*70}")
    print("🏁 TEST RESULTS SUMMARY")
    print("=" * 30)
    
    passed = 0
    total = len(tests)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {test_name:30s}: {status}")
        if success:
            passed += 1
    
    overall_success = passed == total
    
    print(f"\n📊 OVERALL RESULT: {passed}/{total} tests passed")
    
    if overall_success:
        print("🎉 SUCCESS: AGNO-native approach is fully compatible!")
        print("   ✅ All core functionality working")
        print("   ✅ Context bloat eliminated")
        print("   ✅ Backward compatibility maintained")
        print("   ✅ Validation systems working")
        print("\n💡 The system should now have:")
        print("   • Significantly reduced agent prompt bloat")
        print("   • Better performance due to dynamic knowledge access")
        print("   • Less agent confusion from cumulative context")
        print("   • Maintained functionality for all existing features")
    else:
        print("⚠️  PARTIAL SUCCESS: Some areas need attention")
        failed_tests = [name for name, success in results.items() if not success]
        print(f"   Failed tests: {', '.join(failed_tests)}")
    
    print("=" * 70)
    return overall_success


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)