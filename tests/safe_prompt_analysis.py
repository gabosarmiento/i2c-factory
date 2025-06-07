#!/usr/bin/env python3
"""
SAFE DIAGNOSTIC ANALYSIS - No system imports, just measures data from logs
"""

def analyze_session_state_from_logs():
    """Based on the logs we observed, analyze the session state growth"""
    
    print("=" * 60)
    print("🔍 SESSION STATE GROWTH ANALYSIS")
    print("   (Based on observed scenario run logs)")
    print("=" * 60)
    
    # From the logs we saw these progressions:
    scenarios = [
        {
            "step": "Steps 1-2 (Knowledge Loading)",
            "keys": 4,
            "key_list": ["knowledge_base", "db", "embed_model", "db_path"],
            "estimated_size": 2000  # Relatively small
        },
        {
            "step": "Step 3 (Initial Generation)", 
            "keys": 18,
            "key_list": [
                "knowledge_base", "db", "embed_model", "db_path",
                "architectural_context", "system_type", "current_structured_goal",
                "project_path", "file_plan", "code_map", "retrieved_context",
                "knowledge_context", "generation_memory", "backend_api_routes",
                "api_route_summary", "project_context", "language", "objective"
            ],
            "estimated_size": 25000  # Much larger with context
        },
        {
            "step": "Steps 4+ (Agentic Evolution)",
            "keys": "18+",
            "key_list": [
                "All previous keys plus:",
                "reflection_memory", "reasoning_trajectory", "modified_files",
                "quality_results", "sre_results", "enhanced_objective"
            ],
            "estimated_size": 50000  # Very large with accumulated context
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📊 {scenario['step']}:")
        print(f"   Keys: {scenario['keys']}")
        print(f"   Estimated size: ~{scenario['estimated_size']:,} chars")
        
        if scenario['estimated_size'] > 30000:
            print(f"   ⚠️  LARGE: May cause prompt bloat")
        elif scenario['estimated_size'] > 15000:
            print(f"   ⚠️  MEDIUM: Getting substantial")
        else:
            print(f"   ✅ REASONABLE")

def analyze_agent_creation_issue():
    """Analyze the agent creation issue we observed"""
    
    print("\n" + "=" * 60)
    print("🤖 AGENT CREATION ANALYSIS")
    print("   (Based on observed 6x code_builder creation)")
    print("=" * 60)
    
    print("Observed behavior:")
    print("   🔍 Creating code_builder agent")
    print("   🔍 Creating knowledge-enhanced code_builder") 
    print("   🔍 Creating code_builder agent")
    print("   🔍 Creating knowledge-enhanced code_builder")
    print("   ... (repeated 6 times)")
    
    print("\n🎯 Likely causes:")
    print("   1. Session state too complex → agent initialization fails")
    print("   2. Knowledge enhancement fails → system retries")
    print("   3. Context injection overwhelms agent prompt capacity")
    print("   4. RAG retrieval returns too much content")
    
    print("\n💡 Evidence from logs:")
    print("   - Each creation shows same session state keys")
    print("   - Knowledge retrieval successful (8 items found)")
    print("   - But agent creation repeats instead of succeeding")

def recommend_safe_test_approach():
    """Recommend a careful testing approach"""
    
    print("\n" + "=" * 60)
    print("🧪 SAFE TESTING APPROACH")
    print("=" * 60)
    
    phases = [
        {
            "phase": "Phase 1: Measure",
            "actions": [
                "Add prompt size logging to get_rag_enabled_agent()",
                "Log final instruction count and character length",
                "Track session_state size at each step",
                "No functional changes"
            ]
        },
        {
            "phase": "Phase 2: Filter Test", 
            "actions": [
                "Create filtered_session_state() function",
                "Test with CodeBuilderAgent only",
                "Compare generation quality: full vs filtered context",
                "Measure: speed, accuracy, success rate"
            ]
        },
        {
            "phase": "Phase 3: Memory Integration",
            "actions": [
                "Add AGNO memory to one agent type",
                "Store successful patterns in memory",
                "Test memory retrieval vs session_state injection",
                "Gradual rollout to other agents"
            ]
        }
    ]
    
    for phase in phases:
        print(f"\n🎯 {phase['phase']}:")
        for action in phase['actions']:
            print(f"   • {action}")

def estimate_current_issues():
    """Estimate the scope of current issues"""
    
    print("\n" + "=" * 60)
    print("⚠️  CURRENT ISSUES ANALYSIS")
    print("=" * 60)
    
    issues = [
        {
            "issue": "Agent Creation Loops",
            "severity": "HIGH",
            "evidence": "6x code_builder creation in logs",
            "impact": "Wasted tokens, slow execution"
        },
        {
            "issue": "Context Accumulation", 
            "severity": "MEDIUM",
            "evidence": "4 → 18+ session keys growth",
            "impact": "Large prompts, potential confusion"
        },
        {
            "issue": "Knowledge Duplication",
            "severity": "MEDIUM", 
            "evidence": "Multiple context keys with similar info",
            "impact": "Redundant information in prompts"
        },
        {
            "issue": "No Context Filtering",
            "severity": "MEDIUM",
            "evidence": "All agents get all session_state",
            "impact": "Irrelevant information in prompts"
        }
    ]
    
    for issue in issues:
        print(f"\n🚨 {issue['issue']} ({issue['severity']})")
        print(f"   Evidence: {issue['evidence']}")
        print(f"   Impact: {issue['impact']}")

def suggest_immediate_action():
    """Suggest the safest immediate action"""
    
    print("\n" + "=" * 60)
    print("🚀 IMMEDIATE RECOMMENDED ACTION")
    print("=" * 60)
    
    print("1. ADD DIAGNOSTIC LOGGING (Zero risk):")
    print("   • Log session_state size in get_rag_enabled_agent()")
    print("   • Log final agent instruction count") 
    print("   • Log prompt character count")
    print("   • Run Jarvis scenario again with logging")
    
    print("\n2. IDENTIFY ROOT CAUSE:")
    print("   • Why 6x agent creation?")
    print("   • Which session keys cause issues?")
    print("   • At what size do prompts become problematic?")
    
    print("\n3. THEN TEST MINIMAL CHANGE:")
    print("   • Create session_state_filter() function")
    print("   • Test with ONE agent type (code_builder)")
    print("   • Compare: original vs filtered performance")
    print("   • Measure: success rate, quality, speed")
    
    print("\n✅ This approach is:")
    print("   • Low risk (logging first, changes later)")
    print("   • Incremental (one agent at a time)")
    print("   • Measurable (before/after comparison)")
    print("   • Reversible (easy to roll back)")

if __name__ == "__main__":
    analyze_session_state_from_logs()
    analyze_agent_creation_issue()
    recommend_safe_test_approach()
    estimate_current_issues()
    suggest_immediate_action()
    
    print("\n" + "=" * 60)
    print("✅ ANALYSIS COMPLETE - Ready for careful optimization")
    print("=" * 60)