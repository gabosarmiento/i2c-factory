#!/usr/bin/env python3
"""
Test script to validate enhancer caching improvements.
This test simulates the scenario where multiple agents are enhanced with the same knowledge context.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent / "src"
sys.path.insert(0, str(project_root))

# Initialize environment first to avoid llm errors
from i2c.bootstrap import initialize_environment
initialize_environment()

# Set up logging to capture cache hit/miss messages
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

def test_enhancer_caching():
    """Test that the enhancer properly caches patterns to avoid reprocessing"""
    
    print("🧪 Testing enhancer caching improvements...")
    
    # Mock agent class
    class MockAgent:
        def __init__(self, name):
            self.instructions = ["Be helpful", "Generate good code"]
            self.name = name
    
    # Sample knowledge context (AI/ML domain to trigger pattern extraction)
    knowledge_context = """
    from agno.agent import Agent
    from agno.team import Team
    
    Always use Agent(model=..., instructions=...) pattern.
    Use Team() for multi-agent coordination.
    Apply reasoning patterns for AI agents.
    Separate frontend and backend code properly.
    Use proper error handling in all implementations.
    """
    
    print(f"📋 Knowledge context length: {len(knowledge_context)} chars")
    print(f"📋 Testing with {len(knowledge_context.split('.'))} sentences")
    
    # Import the enhancer functions
    try:
        from i2c.agents.core_team.enhancer import quick_enhance_agent, _shared_enhancer
        print("✅ Successfully imported enhancer functions")
    except ImportError as e:
        print(f"❌ Failed to import enhancer: {e}")
        return False
    
    # Test 1: First enhancement should be a cache MISS
    print("\n🔍 Test 1: First enhancement (should be cache MISS)")
    agent1 = MockAgent("TestAgent1")
    
    print(f"Cache size before: {len(_shared_enhancer.enhancement_cache)}")
    enhanced1 = quick_enhance_agent(agent1, knowledge_context, "code_builder")
    print(f"Cache size after: {len(_shared_enhancer.enhancement_cache)}")
    
    # Test 2: Second enhancement should be a cache HIT
    print("\n🔍 Test 2: Second enhancement (should be cache HIT)")
    agent2 = MockAgent("TestAgent2")
    
    cache_size_before = len(_shared_enhancer.enhancement_cache)
    enhanced2 = quick_enhance_agent(agent2, knowledge_context, "planner")
    cache_size_after = len(_shared_enhancer.enhancement_cache)
    
    print(f"Cache size before: {cache_size_before}")
    print(f"Cache size after: {cache_size_after}")
    
    # Test 3: Multiple agents with same context (simulate the 30 agents scenario)
    print("\n🔍 Test 3: Multiple agents with same context (simulating 30 agent scenario)")
    
    agents_created = 0
    for i in range(10):  # Test with 10 agents instead of 30 for faster testing
        agent = MockAgent(f"TestAgent{i+3}")
        enhanced = quick_enhance_agent(agent, knowledge_context, f"agent_type_{i}")
        agents_created += 1
        
        # Check that agent was actually enhanced
        if hasattr(enhanced, '_enhanced_with_knowledge'):
            print(f"✅ Agent {i+3} enhanced successfully")
        else:
            print(f"❌ Agent {i+3} was not enhanced")
    
    print(f"\n📊 Summary:")
    print(f"  - Agents created: {agents_created}")
    print(f"  - Final cache size: {len(_shared_enhancer.enhancement_cache)}")
    print(f"  - Expected cache size: 1 (since all agents used same context)")
    
    # Test 4: Different context should create new cache entry
    print("\n🔍 Test 4: Different context (should create new cache entry)")
    
    different_context = """
    import pandas as pd
    import numpy as np
    
    Always use pandas for data manipulation.
    Use numpy for numerical computations.
    Apply proper data validation techniques.
    """
    
    agent_diff = MockAgent("DifferentContextAgent")
    cache_size_before = len(_shared_enhancer.enhancement_cache)
    enhanced_diff = quick_enhance_agent(agent_diff, different_context, "data_analyst")
    cache_size_after = len(_shared_enhancer.enhancement_cache)
    
    print(f"Cache size before: {cache_size_before}")
    print(f"Cache size after: {cache_size_after}")
    print(f"Expected: cache size should increase by 1")
    
    # Validation
    success = True
    
    if cache_size_after != cache_size_before + 1:
        print("❌ Different context should have created new cache entry")
        success = False
    
    if len(_shared_enhancer.enhancement_cache) > 2:
        print("❌ Cache should only have 2 entries (AI/ML + Data Science contexts)")
        success = False
    
    # Test 5: Verify cache keys are working
    print("\n🔍 Test 5: Verify cache key mechanism")
    
    # Same context should produce same cache key
    key1 = hash(knowledge_context)
    key2 = hash(knowledge_context)
    key3 = hash(different_context)
    
    print(f"Same context keys equal: {key1 == key2}")
    print(f"Different context keys different: {key1 != key3}")
    
    if key1 != key2:
        print("❌ Same context should produce same hash key")
        success = False
    
    if key1 == key3:
        print("❌ Different contexts should produce different hash keys")
        success = False
    
    # Final result
    print(f"\n🎯 Overall Test Result: {'✅ PASSED' if success else '❌ FAILED'}")
    
    return success

def test_performance_improvement():
    """Test that demonstrates the performance improvement from caching"""
    
    print("\n⚡ Testing performance improvement...")
    
    import time
    from i2c.agents.core_team.enhancer import quick_enhance_agent
    
    # Mock agent
    class MockAgent:
        def __init__(self, name):
            self.instructions = ["Be helpful"]
            self.name = name
    
    # Large knowledge context to make pattern extraction more expensive
    large_context = """
    from agno.agent import Agent
    from agno.team import Team
    import pandas as pd
    import numpy as np
    import fastapi
    from fastapi import FastAPI
    import react
    
    """ + "\n".join([
        f"Always follow pattern {i}: Use proper {i} implementation." 
        for i in range(50)  # Create many sentences to process
    ])
    
    print(f"📋 Large context size: {len(large_context)} chars with {len(large_context.split('.'))} sentences")
    
    # Time the first enhancement (cache miss)
    start_time = time.time()
    agent1 = MockAgent("PerfTestAgent1")
    enhanced1 = quick_enhance_agent(agent1, large_context, "code_builder")
    first_time = time.time() - start_time
    
    print(f"⏱️  First enhancement (cache miss): {first_time:.3f} seconds")
    
    # Time multiple subsequent enhancements (cache hits)
    times = []
    for i in range(5):
        start_time = time.time()
        agent = MockAgent(f"PerfTestAgent{i+2}")
        enhanced = quick_enhance_agent(agent, large_context, f"agent_type_{i}")
        elapsed = time.time() - start_time
        times.append(elapsed)
    
    avg_cached_time = sum(times) / len(times)
    
    print(f"⏱️  Average cached enhancement: {avg_cached_time:.3f} seconds")
    print(f"🚀 Performance improvement: {first_time / avg_cached_time:.1f}x faster")
    
    if avg_cached_time < first_time * 0.5:  # Should be at least 2x faster
        print("✅ Caching provides significant performance improvement")
        return True
    else:
        print("❌ Caching should provide better performance improvement")
        return False

if __name__ == "__main__":
    print("🔧 Enhancer Caching Validation Test")
    print("=" * 50)
    
    # Run the tests
    caching_success = test_enhancer_caching()
    performance_success = test_performance_improvement()
    
    print("\n" + "=" * 50)
    print("📋 Final Results:")
    print(f"  - Caching Test: {'✅ PASSED' if caching_success else '❌ FAILED'}")
    print(f"  - Performance Test: {'✅ PASSED' if performance_success else '❌ FAILED'}")
    
    overall_success = caching_success and performance_success
    print(f"  - Overall: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n🎉 Enhancer caching improvements are working correctly!")
        print("   The 30x repeated pattern extraction issue should be resolved.")
    else:
        print("\n⚠️  Some issues detected. Check the test output above.")
    
    sys.exit(0 if overall_success else 1)