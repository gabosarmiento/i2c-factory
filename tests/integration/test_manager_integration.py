from pathlib import Path
from i2c.agents.modification_team.code_modification_manager_agno import apply_modification

def test_create_file():
    # Test file creation
    test_step = {
        'action': 'create',
        'file': 'test_created_file.py',
        'what': 'Create a simple test file',
        'how': 'Create a file with a main function that prints Hello World'
    }
    
    result = apply_modification(test_step, Path("./"))
    if hasattr(result, 'unified_diff'):
        print("=== CREATE TEST SUCCEEDED ===")
        print(f"Patch:\n{result.unified_diff}")
    else:
        print("=== CREATE TEST FAILED ===")
        print(f"Error: {result}")

def test_modify_file():
    # First ensure the file exists
    test_file = Path("./test_file_to_modify.py")
    if not test_file.exists():
        test_file.write_text("def say_hello():\n    print('Hello!')")
    
    # Test file modification
    test_step = {
        'action': 'modify',
        'file': 'test_file_to_modify.py',
        'what': 'Add a parameter to the function',
        'how': 'Add a name parameter with default value "World"'
    }
    
    result = apply_modification(test_step, Path("./"))
    if hasattr(result, 'unified_diff'):
        print("=== MODIFY TEST SUCCEEDED ===")
        print(f"Patch:\n{result.unified_diff}")
    else:
        print("=== MODIFY TEST FAILED ===")
        print(f"Error: {result}")

if __name__ == "__main__":
    print("Testing file creation...")
    test_create_file()
    
    print("\nTesting file modification...")
    test_modify_file()