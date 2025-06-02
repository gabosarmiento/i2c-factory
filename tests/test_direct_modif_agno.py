# test_direct_modification.py
"""
Test to isolate where the modification breakdown occurs
"""
from i2c.bootstrap import initialize_environment
initialize_environment()

from pathlib import Path
import tempfile
import signal

def test_direct_modification_team():
    """Test the modification team directly, bypassing orchestration"""
    
    # Create temporary test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Create test file
        test_file = project_path / "test_file.py"
        test_file.write_text("""def add(a, b):
    return a + b

def main():
    print(add(1, 2))

if __name__ == "__main__":
    main()
""")
        
        print("=== ORIGINAL FILE ===")
        print(test_file.read_text())
        
        # Test direct modification
        from i2c.agents.modification_team.code_modification_manager_agno import apply_modification
        
        step = {
            "file": "test_file.py", 
            "action": "modify",
            "what": "Add type hints to add function",
            "how": "Add : int parameters and -> int return type to the add function"
        }
        
        print("=== MODIFICATION STEP ===")
        print(f"Step: {step}")
        
        # Test with session state
        session_state = {
            "project_path": str(project_path),
            "use_retrieval_tools": True,
            "skip_unit_tests": False,
            "skip_quality_checks": False,
            "test_mode": True
        }
        
        print("=== CALLING APPLY_MODIFICATION ===")
        
        # Add timeout protection
        def timeout_handler(signum, frame):
            raise TimeoutError("Team execution timed out")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)  # 30 second timeout
        
        try:
            result = apply_modification(
                modification_step=step,
                project_path=project_path,
                retrieved_context="",
                session_state=session_state
            )
            signal.alarm(0)  # Cancel timeout
            
            print("=== MODIFICATION RESULT ===")
            print(f"Result type: {type(result)}")
            print(f"Result: {result}")
            
            # Check if file was actually modified
            print("=== MODIFIED FILE ===")
            if test_file.exists():
                modified_content = test_file.read_text()
                print(modified_content)
                
                # Check for type hints
                if "def add(a:" in modified_content and ") ->" in modified_content:
                    print("✅ SUCCESS: Type hints were added!")
                    return True
                else:
                    print("❌ FAILURE: No type hints found in modified file")
                    return False
            else:
                print("❌ FAILURE: Original file no longer exists")
                return False
                
        except TimeoutError:
            print("❌ TIMEOUT: Team execution hung for 30+ seconds")
            return False
        except Exception as e:
            signal.alarm(0)
            print(f"❌ EXCEPTION in apply_modification: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_orchestration_vs_direct():
    """Compare orchestration vs direct modification"""
    
    print("\n" + "="*60)
    print("TESTING DIRECT MODIFICATION (BYPASS ORCHESTRATION)")
    print("="*60)
    
    direct_success = test_direct_modification_team()
    
    print(f"\nDirect modification result: {'✅ SUCCESS' if direct_success else '❌ FAILED'}")
    
    if direct_success:
        print("\n🔍 DIAGNOSIS: Orchestration layer is the problem")
        print("   → The modification team works correctly")
        print("   → Issue is in orchestration → modification bridge")
    else:
        print("\n🔍 DIAGNOSIS: Modification team is broken")
        print("   → Problem is deeper in the modification agents")
        print("   → Need to check code_modification_manager_agno")
    
    return direct_success

if __name__ == "__main__":
    success = test_orchestration_vs_direct()
    print(f"\n{'='*60}")
    print(f"FINAL RESULT: {'DIRECT MODIFICATION WORKS' if success else 'DIRECT MODIFICATION BROKEN'}")
    print(f"{'='*60}")