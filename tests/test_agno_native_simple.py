#!/usr/bin/env python3
"""
Simple test to verify AGNO-native approach reduces context bloat.
Based on tests/test_knowledge_accumulation.py pattern.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent / "src"
sys.path.insert(0, str(project_root))

from i2c.bootstrap import initialize_environment
initialize_environment()

from i2c.workflow.scenario_processor import ScenarioProcessor
import tempfile
import json


def test_agno_native_bloat_reduction():
    """Test AGNO-native approach vs content consumption bloat"""
    
    print("🧪 Testing AGNO-native context bloat reduction")
    print("=" * 60)
    
    # Simple test scenario (like tests/test_knowledge_accumulation.py)
    simple_scenario = {
        "description": "Simple test for AGNO-native approach",
        "objective": "Create a basic Python calculator app",
        "language": "python",
        "constraints": ["Keep it simple", "Use functions"],
        "context": "This is a test scenario to verify context bloat reduction"
    }
    
    # Create temporary project directory
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        print(f"📁 Test project: {project_path}")
        print(f"📋 Scenario: {simple_scenario['objective']}")
        
        # Initialize scenario processor
        processor = ScenarioProcessor()
        
        # Measure initial session state
        print("\n📊 BEFORE: Measuring initial session state...")
        initial_session_state = {
            "scenario": simple_scenario,
            "project_path": str(project_path),
            "language": simple_scenario["language"]
        }
        
        initial_size = len(str(initial_session_state))
        print(f"📏 Initial session_state size: {initial_size:,} characters")
        print(f"🔍 Initial keys: {list(initial_session_state.keys())}")
        
        try:
            # Process scenario with our AGNO-native changes
            print("\n🚀 Processing scenario with AGNO-native approach...")
            
            result = processor.process_scenario(
                scenario_data=simple_scenario,
                project_path=project_path
            )
            
            print(f"✅ Scenario processing completed")
            print(f"📊 Result success: {result.get('success', False)}")
            
            # Measure final session state from processor
            final_session_state = getattr(processor, 'session_state', {})
            final_size = len(str(final_session_state))
            
            print(f"\n📊 AFTER: Final session state analysis...")
            print(f"📏 Final session_state size: {final_size:,} characters")
            print(f"🔍 Final keys: {list(final_session_state.keys())}")
            
            # Check for bloat indicators
            has_retrieved_context = "retrieved_context" in final_session_state
            has_knowledge_summary = "knowledge_summary" in final_session_state
            has_knowledge_base = "knowledge_base" in final_session_state
            
            print(f"\n🔍 BLOAT ANALYSIS:")
            print(f"   retrieved_context (bloat): {has_retrieved_context}")
            print(f"   knowledge_summary (light): {has_knowledge_summary}")
            print(f"   knowledge_base (AGNO): {has_knowledge_base}")
            
            # Calculate growth
            growth = final_size - initial_size
            growth_percent = (growth / initial_size) * 100 if initial_size > 0 else 0
            
            print(f"\n📈 SESSION STATE GROWTH:")
            print(f"   Size change: {initial_size:,} → {final_size:,} characters")
            print(f"   Growth: +{growth:,} characters ({growth_percent:.1f}%)")
            
            # Check specific bloat patterns
            if has_retrieved_context:
                retrieved_size = len(str(final_session_state["retrieved_context"]))
                print(f"   ⚠️  retrieved_context size: {retrieved_size:,} characters")
            
            if has_knowledge_summary:
                summary_size = len(str(final_session_state["knowledge_summary"]))
                print(f"   ✅ knowledge_summary size: {summary_size:,} characters")
            
            # Evaluate success
            success_indicators = [
                not has_retrieved_context,  # No content bloat
                growth < 10000,  # Reasonable growth (<10KB)
                has_knowledge_base or has_knowledge_summary  # Has knowledge access
            ]
            
            success = all(success_indicators)
            
            print(f"\n🏁 FINAL RESULT:")
            if success:
                print("🎉 SUCCESS: AGNO-native approach working!")
                print("   ✅ No retrieved_context bloat")
                print("   ✅ Reasonable session state growth")
                print("   ✅ Knowledge access available")
            else:
                print("⚠️  PARTIAL SUCCESS: Some improvements needed")
                print(f"   - No content bloat: {'✅' if not has_retrieved_context else '❌'}")
                print(f"   - Reasonable growth: {'✅' if growth < 10000 else '❌'}")
                print(f"   - Knowledge access: {'✅' if (has_knowledge_base or has_knowledge_summary) else '❌'}")
            
            return success
            
        except Exception as e:
            print(f"❌ ERROR: Scenario processing failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_orchestration_team_bloat():
    """Test orchestration team instruction bloat"""
    
    print("\n🧪 Testing orchestration team instruction bloat")
    print("=" * 60)
    
    try:
        from i2c.workflow.orchestration_team import build_orchestration_team
        
        # Mock knowledge base with realistic content
        class MockKnowledgeBase:
            def retrieve_knowledge(self, query, limit=5):
                # This simulates what would cause bloat
                large_content = "def example():\n    " + "# Code example\n    " * 50
                return [{"source": "test.md", "content": large_content}] * limit
        
        # Test session state
        session_state = {
            "objective": {
                "task": "Create authentication system",
                "architectural_context": {"system_type": "web_app"}
            },
            "knowledge_base": MockKnowledgeBase()
        }
        
        print("🏗️  Building orchestration team...")
        
        team = build_orchestration_team(session_state=session_state)
        
        # Analyze instructions
        instructions_text = "\n".join(team.instructions)
        instruction_size = len(instructions_text)
        
        print(f"✅ Team created successfully")
        print(f"📏 Instruction size: {instruction_size:,} characters")
        print(f"🔧 Has knowledge access: {team.knowledge is not None}")
        print(f"🔧 Agentic context: {team.enable_agentic_context}")
        
        # Check for bloat patterns
        has_content_chunks = "[Knowledge " in instructions_text
        has_agno_guidance = "knowledge base through the Team" in instructions_text
        is_reasonable_size = instruction_size < 5000  # Under 5KB
        
        print(f"\n🔍 INSTRUCTION ANALYSIS:")
        print(f"   Content chunks embedded: {has_content_chunks}")
        print(f"   AGNO-native guidance: {has_agno_guidance}")
        print(f"   Reasonable size (<5KB): {is_reasonable_size}")
        
        success = has_agno_guidance and not has_content_chunks and is_reasonable_size
        
        print(f"\n🏁 ORCHESTRATION RESULT:")
        if success:
            print("🎉 SUCCESS: Orchestration team uses AGNO-native approach!")
        else:
            print("⚠️  NEEDS IMPROVEMENT: Still has bloat patterns")
        
        return success
        
    except Exception as e:
        print(f"❌ ERROR: Orchestration team test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 AGNO-Native Context Bloat Reduction Test")
    print("=" * 70)
    
    # Run tests
    test1_success = test_agno_native_bloat_reduction()
    test2_success = test_orchestration_team_bloat()
    
    print("\n" + "=" * 70)
    print("🏁 SUMMARY RESULTS:")
    print(f"   Scenario processing: {'✅ PASS' if test1_success else '❌ FAIL'}")
    print(f"   Orchestration team: {'✅ PASS' if test2_success else '❌ FAIL'}")
    
    if test1_success and test2_success:
        print("\n🎉 OVERALL SUCCESS!")
        print("   AGNO-native approach successfully reduces context bloat")
        print("   System should have better performance and less agent confusion")
    else:
        print("\n⚠️  MIXED RESULTS - some optimizations working, others need refinement")
    
    print("=" * 70)