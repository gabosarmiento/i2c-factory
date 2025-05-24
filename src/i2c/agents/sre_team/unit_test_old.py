# /agents/sre_team/unit_test.py
# Agent for generating unit tests.

import os
import ast
from pathlib import Path

from agno.agent import Agent
from builtins import llm_middle

class UnitTestGeneratorAgent(Agent):
    """Generates basic unit tests for Python functions found in the generated code."""
    def __init__(self, **kwargs):
        # No retry params here
        super().__init__(
            name="UnitTestGenerator",
            model=llm_middle,
            description="Generates basic Python unit tests for given functions.",
            instructions=[
                "You are an AI assistant that generates basic Python unit tests.",
                "You will be given source code and a specific function name.",
                "Generate a simple test case for that function using the `unittest` framework.",
                "Focus on testing basic functionality and common edge cases (like None input).",
                "Output ONLY the raw Python code for the test case, including necessary imports.",
                "Do NOT include markdown fences or any explanations — only the test code.",
            ],
            **kwargs
        )
        print("🧪 [UnitTestGeneratorAgent] Initialized.")

    def _find_python_functions(self, code_content: str) -> list[str]:
        """Parses Python code using AST to find top-level function names."""
        # ... (no changes needed here) ...
        functions = []
        try:
            tree = ast.parse(code_content)
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
        except SyntaxError as e:
            print(f"   ⚠️ Warning: Could not parse Python code in AST: {e}")
        except Exception as e:
            print(f"   ⚠️ Warning: Error parsing Python code with AST: {e}")
        return functions

    def generate_test_code(self, module_name: str, function_name: str, source_code: str) -> str | None:
        """Generates test code for a single function using the LLM."""
        print(f"   -> Generating test for function: {function_name} in {module_name}.py")
        prompt = (
            f"Source Code for module '{module_name}.py':\n"
            f"```python\n{source_code}\n```\n\n"
            f"Function to test: `{function_name}`\n\n"
            f"Generate a Python `unittest` test case for the function `{function_name}`."
            f"Include necessary imports (unittest, and from '{module_name}' import {function_name})."
            f"Output ONLY the raw Python code for the test class."
        )
        try:
            # Use direct agent.run()
            response = self.run(prompt) # <<< REVERTED >>>
            test_code = response.content if hasattr(response, 'content') else str(response)

            # Basic cleaning and validation (remains the same)
            test_code = test_code.strip()
            # ... (cleaning logic) ...
            if test_code.startswith("```") and test_code.endswith("```"):
                 test_code = test_code[3:-3].strip()
                 first_line_end = test_code.find('\n')
                 if first_line_end != -1 and test_code[:first_line_end].strip().lower() == 'python':
                      test_code = test_code[first_line_end+1:].strip()

            if "import unittest" in test_code and f"from {module_name} import" in test_code and "class Test" in test_code:
                 print(f"      ✅ Test code generated for {function_name}")
                 return test_code
            else:
                 print(f"      ⚠️ Generated test code for {function_name} seems incomplete or malformed.")
                 # Raise error or return None? Let's return None and log warning.
                 return None

        except Exception as e:
            # Catch general exceptions from self.run()
            print(f"   ❌ Error generating test for {function_name}: {e}")
            # Return None to indicate failure for this specific test case
            return None

    def generate_tests(self, code_map: dict[str, str]) -> dict[str, str]:
        """Generates unit tests for Python files in the code map."""
        print("🤖 [UnitTestGeneratorAgent] Generating unit tests...")
        updated_code_map = code_map.copy()
        total_funcs_found = 0
        tests_generated_count = 0
        tests_skipped_count = 0

        for file_path_str, code_content in code_map.items():
            file_path = Path(file_path_str)
            if file_path.suffix == ".py" and not file_path.stem.startswith("test_"):
                module_name = file_path.stem
                print(f"   Analysing {file_path_str} for functions...")
                functions_to_test = self._find_python_functions(code_content)
                total_funcs_found += len(functions_to_test)

                if not functions_to_test:
                    print(f"      No top-level functions found to test in {file_path_str}.")
                    continue

                test_file_content_parts = ["import unittest"]
                imports_needed = set()
                test_cases_generated_for_module = []
                test_file_path = file_path.parent / f"test_{module_name}.py"
                module_had_successful_tests = False

                for func_name in functions_to_test:
                    # Call generate_test_code which now uses direct .run()
                    # and returns None on failure
                    test_case_code = self.generate_test_code(module_name, func_name, code_content)
                    if test_case_code:
                        imports_needed.add(f"from {module_name} import {func_name}")
                        test_cases_generated_for_module.append(test_case_code)
                        module_had_successful_tests = True
                        tests_generated_count += 1
                    else:
                        # Error/skip already logged in generate_test_code
                        tests_skipped_count += 1

                # Assemble the test file if any tests were generated for this module
                if module_had_successful_tests:
                    test_file_content_parts.extend(sorted(list(imports_needed)))
                    test_file_content_parts.append("\n")
                    test_file_content_parts.extend(test_cases_generated_for_module)
                    # ... (rest of assembly logic) ...
                    test_file_content_parts.append("\n") # Add newline at the end before runner
                    test_file_content_parts.append("if __name__ == '__main__':")
                    test_file_content_parts.append("    unittest.main()")

                    final_test_content = "\n".join(test_file_content_parts)
                    updated_code_map[str(test_file_path)] = final_test_content
                    print(f"   ➕ Added/Updated test file: {test_file_path}")


        # --- Summary Reporting ---
        if total_funcs_found == 0:
             print("✅ [UnitTestGeneratorAgent] No functions found to generate tests for.")
        elif tests_generated_count == total_funcs_found:
             print(f"✅ [UnitTestGeneratorAgent] Successfully generated test cases for all {total_funcs_found} found functions.")
        else:
             print(f"⚠️ [UnitTestGeneratorAgent] Finished generating tests. Generated: {tests_generated_count}/{total_funcs_found}. Skipped {tests_skipped_count} due to errors.")

        return updated_code_map

# Instantiate the agent for easy import

# Instantiate the agent for easy import
unit_test_generator = UnitTestGeneratorAgent()

# Add quality constraints as an attribute after instantiation
unit_test_generator.quality_constraints = [
    "Ensure tests do not have duplicate unittest.main() calls",
    "Use consistent data models across all files",
    "Avoid creating duplicate implementations of the same functionality",
    "If creating a CLI app, use a single approach for the interface",
    "Use consistent file naming for data storage (e.g., todos.json)"
]
