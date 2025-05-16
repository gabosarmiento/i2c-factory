# workflow/modification/test_and_quality.py
# Handles running unit test generation and code quality checks.

# Import necessary agent INSTANCES
from i2c.agents.sre_team import (
    unit_test_generator,
    code_quality_sentinel
)
# Import CLI controller
from i2c.cli.controller import canvas

# In workflow/test_and_quality.py or where unit_test_generator's generate_tests function is defined

# In workflow/test_and_quality.py or where unit_test_generator's generate_tests function is defined

def generate_unit_tests(code_map: dict) -> dict:
    """Generates unit tests for the provided code map."""
    canvas.step("Generating/Updating Unit Tests...")
    final_code_map_incl_tests = code_map # Default to original map
    try:
        final_code_map_incl_tests = unit_test_generator.generate_tests(code_map)
        
        # Post-process test files to remove duplicate unittest.main() calls
        for file_path, content in final_code_map_incl_tests.items():
            if file_path.startswith("test_") and file_path.endswith(".py"):
                # Check for duplicate unittest.main() calls
                if content.count("unittest.main()") > 1:
                    canvas.warning(f"Removing duplicate unittest.main() calls in {file_path}")
                    
                    # Split file into lines
                    lines = content.splitlines()
                    
                    # Find all lines with unittest.main()
                    main_call_indices = [i for i, line in enumerate(lines) if "unittest.main()" in line]
                    
                    # Keep only the last one
                    if len(main_call_indices) > 1:
                        for idx in main_call_indices[:-1]:
                            lines[idx] = "# " + lines[idx] + " # Removed duplicate"
                    
                    # Join lines back into a single string
                    final_code_map_incl_tests[file_path] = "\n".join(lines)
                    
    except Exception as e:
        canvas.error(f"Error during Unit Test Generation orchestration: {e}")
        canvas.warning("Proceeding without generated/updated unit tests due to error.")
        # Return the original map if test generation fails
    return final_code_map_incl_tests

def run_quality_checks(code_map_with_tests: dict) -> bool:
    """Runs code quality checks using the sentinel."""
    canvas.step("Performing SRE Code Quality Check...")
    issues_found = False
    try:
        issues = code_quality_sentinel.check_code(code_map_with_tests)
        if issues:
            issues_found = True
            canvas.warning("Code quality issues found:")
            for issue in issues: canvas.warning(f"  - {issue}")
            # Decide if issues should block further progress? For now, just warn.
        else:
            canvas.success("Code quality checks passed.")
        # Return True if checks ran without critical error, even if issues were found
        return True
    except Exception as e:
        canvas.error(f"Error during SRE Quality Check: {e}")
        # Return False to indicate a failure in the check itself
        return False

