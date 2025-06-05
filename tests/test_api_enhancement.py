#!/usr/bin/env python3
"""
Test API route enhancement for frontend generation
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent / "src"
sys.path.insert(0, str(project_root))

# Initialize environment first
from i2c.bootstrap import initialize_environment
initialize_environment()

def test_api_enhancement():
    """Test the frontend API enhancement functionality"""
    
    print("🧪 Testing API route enhancement for frontend generation...")
    
    # Mock session state with backend API routes (like what would be extracted)
    session_state = {
        'backend_api_routes': {
            'GET': [
                {'path': '/api/health', 'function': 'health_check', 'full_path': '/api/health'},
                {'path': '/conflict-risk/{participant_id}', 'function': 'get_conflict_risk', 'full_path': '/conflict-risk/{participant_id}'},
                {'path': '/conflict-prevention/rules', 'function': 'get_conflict_prevention_rules', 'full_path': '/conflict-prevention/rules'}
            ],
            'POST': [
                {'path': '/analyze-communication-patterns', 'function': 'analyze_communication_patterns', 'full_path': '/analyze-communication-patterns'},
                {'path': '/conflict-prevention/check', 'function': 'check_conflict_prevention', 'full_path': '/conflict-prevention/check'}
            ]
        }
    }
    
    # Test the API enhancement function
    from i2c.utils.api_route_tracker import enhance_frontend_generation_with_apis
    
    original_prompt = """
    Generate a React component for a Dashboard that shows conflict risk analysis.
    The component should fetch data and display it in a user-friendly way.
    """
    
    enhanced_prompt = enhance_frontend_generation_with_apis(
        original_prompt, session_state, "dashboard"
    )
    
    print("📋 Original prompt length:", len(original_prompt))
    print("📋 Enhanced prompt length:", len(enhanced_prompt))
    
    # Check if API routes are included
    api_endpoints = [
        '/api/health',
        '/conflict-risk/{participant_id}',
        '/conflict-prevention/rules',
        '/analyze-communication-patterns',
        '/conflict-prevention/check'
    ]
    
    found_endpoints = []
    for endpoint in api_endpoints:
        if endpoint in enhanced_prompt:
            found_endpoints.append(endpoint)
    
    print(f"\n✅ Found {len(found_endpoints)}/{len(api_endpoints)} API endpoints in enhanced prompt:")
    for endpoint in found_endpoints:
        print(f"  - {endpoint}")
    
    # Check for critical instructions
    critical_instructions = [
        "Use ONLY the endpoints listed above",
        "fetch() with proper error handling",
        "loading states",
        "Content-Type: application/json"
    ]
    
    found_instructions = []
    for instruction in critical_instructions:
        if instruction in enhanced_prompt:
            found_instructions.append(instruction)
    
    print(f"\n✅ Found {len(found_instructions)}/{len(critical_instructions)} critical instructions:")
    for instruction in found_instructions:
        print(f"  - {instruction}")
    
    # Test with no API routes
    print("\n🧪 Testing with no API routes in session state...")
    empty_session = {}
    enhanced_empty = enhance_frontend_generation_with_apis(original_prompt, empty_session, "component")
    
    if enhanced_empty == original_prompt:
        print("✅ Correctly returns original prompt when no API routes available")
    else:
        print("❌ Should return original prompt when no API routes available")
    
    # Overall assessment
    success_rate = (len(found_endpoints) / len(api_endpoints) + len(found_instructions) / len(critical_instructions)) / 2
    
    print(f"\n🎯 API Enhancement Test Result: {success_rate:.1%} success rate")
    
    if success_rate >= 0.8:
        print("✅ API enhancement is working correctly!")
        return True
    else:
        print("❌ API enhancement needs improvement")
        return False

if __name__ == "__main__":
    test_api_enhancement()