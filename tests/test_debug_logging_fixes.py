#!/usr/bin/env python3
"""
Test debug logging fixes for session state
"""

import sys
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(project_root))

# Initialize environment first
from i2c.bootstrap import initialize_environment
initialize_environment()

def test_reduced_debug_logging():
    """Test that debug logging is less verbose and doesn't show None values repeatedly"""
    
    print("🧪 Testing reduced debug logging...")
    
    from i2c.agents.core_agents import get_rag_enabled_agent
    from unittest.mock import Mock
    
    # Create mock session state with some keys (but not the problematic ones)
    session_state = {
        'knowledge_base': Mock(),
        'architectural_context': {'system_type': 'fullstack_web_app'},
        'backend_api_routes': {'GET': [{'path': '/api/test'}]},
        'some_other_key': 'value',
        'another_key': None  # This should not spam logs
    }
    
    # Capture output
    output_buffer = io.StringIO()
    
    try:
        with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
            # This should trigger the debug logging
            agent = get_rag_enabled_agent("code_builder", session_state=session_state)
    except Exception as e:
        # Expected since we're using mocks
        pass
    
    output = output_buffer.getvalue()
    
    # Count debug lines
    debug_lines = [line for line in output.split('\n') if 'DEBUG:' in line or '🔍 DEBUG:' in line]
    
    print(f"📊 Debug lines generated: {len(debug_lines)}")
    
    # Check for improvements
    improvements = []
    
    # Should not spam individual key-value pairs
    individual_key_logs = [line for line in debug_lines if "session_state['" in line and "'] =" in line]
    if len(individual_key_logs) == 0:
        improvements.append("✅ No individual key-value spam logging")
    else:
        improvements.append(f"❌ Still logging {len(individual_key_logs)} individual key-value pairs")
    
    # Should show summary of important keys
    summary_logs = [line for line in debug_lines if "Important session keys present:" in line]
    if len(summary_logs) > 0:
        improvements.append("✅ Shows summary of important keys")
    else:
        improvements.append("❌ No summary of important keys shown")
    
    # Should not mention project_context or validation_results as None
    none_logs = [line for line in debug_lines if ("project_context" in line and "None" in line) or 
                                                 ("validation_results" in line and "None" in line)]
    if len(none_logs) == 0:
        improvements.append("✅ No more project_context/validation_results = None spam")
    else:
        improvements.append(f"❌ Still logging project_context/validation_results = None ({len(none_logs)} times)")
    
    # Print improvements
    for improvement in improvements:
        print(f"  {improvement}")
    
    # Overall assessment
    success_count = sum(1 for imp in improvements if imp.startswith("✅"))
    total_count = len(improvements)
    
    if success_count == total_count:
        print("✅ Debug logging improvements are working correctly!")
        return True
    else:
        print(f"⚠️ Debug logging partially improved ({success_count}/{total_count})")
        return False

def test_workflow_controller_important_keys():
    """Test that workflow controller no longer lists legacy keys as important"""
    
    print("\n🧪 Testing workflow controller important keys...")
    
    # Read the workflow controller file
    workflow_controller_path = Path(__file__).parent.parent / "src" / "i2c" / "workflow" / "workflow_controller.py"
    content = workflow_controller_path.read_text()
    
    # Check for legacy keys
    legacy_keys = ["project_context", "validation_results"]
    found_legacy = []
    
    for key in legacy_keys:
        if f"'{key}'" in content and "important_keys" in content:
            # Check if it's in the important_keys list
            lines = content.split('\n')
            in_important_keys = False
            for i, line in enumerate(lines):
                if "important_keys = [" in line:
                    # Check next few lines for the key
                    for j in range(i, min(i+10, len(lines))):
                        if f"'{key}'" in lines[j] and "]" not in lines[j]:
                            in_important_keys = True
                            break
                    break
            
            if in_important_keys:
                found_legacy.append(key)
    
    if not found_legacy:
        print("✅ Legacy keys (project_context, validation_results) removed from important_keys")
        return True
    else:
        print(f"❌ Legacy keys still in important_keys: {found_legacy}")
        return False

if __name__ == "__main__":
    print("🔧 Debug Logging Fixes Validation Test")
    print("=" * 50)
    
    # Run the tests
    logging_success = test_reduced_debug_logging()
    workflow_success = test_workflow_controller_important_keys()
    
    print("\n" + "=" * 50)
    print("📋 Final Results:")
    print(f"  - Debug Logging Fixes: {'✅ PASSED' if logging_success else '❌ FAILED'}")
    print(f"  - Workflow Controller: {'✅ PASSED' if workflow_success else '❌ FAILED'}")
    
    overall_success = logging_success and workflow_success
    print(f"  - Overall: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n🎉 Debug logging issues are resolved!")
        print("   You should see much less noisy debug output.")
    else:
        print("\n⚠️  Some issues detected. Check the test output above.")
    
    sys.exit(0 if overall_success else 1)