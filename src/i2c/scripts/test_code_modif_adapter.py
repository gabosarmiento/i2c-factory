from i2c.bootstrap import initialize_environment
initialize_environment()
def test_adapter():
    from pathlib import Path
    import tempfile
    import os
    from i2c.workflow.modification.code_executor import execute_modification_steps
    
    # Create a temporary test project
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        
        # Create a simple Python file
        test_file = project_path / "test.py"
        test_file.write_text("def hello():\n    return 'world'\n")
        
        # Create a simple modification plan
        modification_plan = [
            {
                "action": "modify",
                "file": "test.py",
                "what": "Add a greeting parameter",
                "how": "Update the function to take a name parameter and return 'Hello, {name}!'"
            }
        ]
        
        # Execute the modification
        modified_code_map, files_to_delete = execute_modification_steps(
            modification_plan=modification_plan,
            project_path=project_path,
            session_state={}
        )
        
        # Print the results
        print("Modified files:")
        for file_path, content in modified_code_map.items():
            print(f"- {file_path}:")
            print(content)
            
        print("\nFiles to delete:")
        for file_path in files_to_delete:
            print(f"- {file_path}")
        
        # Verify the results match expectations
        expected_result = "def hello(name='world'):\n    return f'Hello, {name}!'\n"
        actual_result = modified_code_map.get("test.py", "")
        
        if actual_result == expected_result:
            print("\nTest passed! ✅")
        else:
            print("\nTest failed! ❌")
            print("Expected:")
            print(expected_result)
            print("Actual:")
            print(actual_result)

if __name__ == "__main__":
    test_adapter()