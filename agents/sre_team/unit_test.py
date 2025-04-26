# /agents/sre_team/unit_test.py
# Agent for generating unit tests.

import os
import ast
from pathlib import Path

from agno.agent import Agent
from llm_providers import llm_middle # Using middle tier for test generation

class UnitTestGeneratorAgent(Agent):
    """
    Generates basic unit tests for Python functions found in the generated code.
    Uses the structure provided by the user.
    """
    def __init__(self, **kwargs):
        super().__init__(
            name="UnitTestGenerator",
            model=llm_middle, # Use the imported llm_middle instance
            description="Generates basic Python unit tests for given functions.",
            instructions=[
                "You are an AI assistant that generates basic Python unit tests.",
                "You will be given source code and a specific function name.",
                "Generate a simple test case for that function using the `unittest` framework.",
                "Focus on testing basic functionality and common edge cases (like None input).",
                "Output ONLY the raw Python code for the test case, including necessary imports.",
                "Do NOT include markdown fences or any explanations — only the test code.",
            ],
            # No temperature here - it's configured on the llm_middle object itself
            # No api_key here
            **kwargs
        )
        print("🧪 [UnitTestGeneratorAgent] Initialized.")

    def _find_python_functions(self, code_content: str) -> list[str]:
        """Parses Python code using AST to find top-level function names."""
        functions = []
        try:
            tree = ast.parse(code_content)
            # Iterate through top-level nodes in the module body
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
        except SyntaxError as e:
            print(f"   ⚠️ Warning: Could not parse Python code to find functions due to SyntaxError: {e}")
        except Exception as e:
            print(f"   ⚠️ Warning: Error parsing Python code with AST: {e}")
        return functions

    def generate_test_code(self, module_name: str, function_name: str, source_code: str) -> str | None:
        """Generates test code for a single function using the LLM."""
        print(f"   -> Generating test for function: {function_name} in {module_name}.py")
        # Construct the prompt for the LLM based on the simplified structure
        prompt = (
            f"Source Code for module '{module_name}.py':\n"
            f"```python\n{source_code}\n```\n\n"
            f"Function to test: `{function_name}`\n\n"
            f"Generate a Python `unittest` test case for the function `{function_name}`."
            f"Include necessary imports (unittest, and from '{module_name}' import {function_name})."
            f"Output ONLY the raw Python code for the test class."
        )
        try:
            # Use the agent's run method (inherited from Agno Agent)
            response = self.run(prompt)
            test_code = response.content if hasattr(response, 'content') else str(response)

            # Basic cleaning (though prompt requests raw code)
            test_code = test_code.strip()
            if test_code.startswith("```") and test_code.endswith("```"):
                 test_code = test_code[3:-3].strip()
                 first_line_end = test_code.find('\n')
                 if first_line_end != -1 and test_code[:first_line_end].strip().lower() == 'python':
                      test_code = test_code[first_line_end+1:].strip()

            # Basic validation
            if "import unittest" in test_code and f"from {module_name} import" in test_code and "class Test" in test_code:
                 print(f"      ✅ Test code generated for {function_name}")
                 return test_code
            else:
                 print(f"      ⚠️ Generated test code for {function_name} seems incomplete or malformed.")
                 # print(f"         Raw Response: {test_code[:200]}") # Optional debug
                 return None # Treat malformed test as failure

        except Exception as e:
            print(f"   ❌ Error generating test for {function_name}: {e}")
            return None

    def generate_tests(self, code_map: dict[str, str]) -> dict[str, str]:
        """
        Generates unit tests for Python files in the code map.

        Args:
            code_map: The original dictionary mapping file paths to code content.

        Returns:
            An updated dictionary including generated test files (e.g., 'test_module.py').
        """
        print("🤖 [UnitTestGeneratorAgent] Generating unit tests...")
        updated_code_map = code_map.copy()
        generated_any_tests = False

        for file_path_str, code_content in code_map.items():
            file_path = Path(file_path_str)
            # Only process Python files, exclude test files themselves
            if file_path.suffix == ".py" and not file_path.stem.startswith("test_"):
                module_name = file_path.stem
                print(f"   Analysing {file_path_str} for functions...")
                functions_to_test = self._find_python_functions(code_content)

                if not functions_to_test:
                    print(f"      No top-level functions found to test in {file_path_str}.")
                    continue

                # Prepare to collect test code parts for a single test file per module
                test_file_content_parts = ["import unittest"]
                imports_needed = set()
                test_cases_generated = []
                test_file_path = file_path.parent / f"test_{module_name}.py"
                test_file_generated_for_module = False

                # Generate test cases for each function found in the module
                for func_name in functions_to_test:
                    # Call the refactored generation method
                    test_case_code = self.generate_test_code(module_name, func_name, code_content)
                    if test_case_code:
                        imports_needed.add(f"from {module_name} import {func_name}")
                        test_cases_generated.append(test_case_code)
                        test_file_generated_for_module = True
                        generated_any_tests = True # Mark that we generated at least one test overall

                # Assemble the test file if any tests were generated for this module
                if test_file_generated_for_module:
                    test_file_content_parts.extend(sorted(list(imports_needed)))
                    test_file_content_parts.append("\n") # Add newline after imports
                    test_file_content_parts.extend(test_cases_generated)
                    test_file_content_parts.append("\n") # Add newline at the end before runner
                    # Add standard unittest runner boilerplate
                    test_file_content_parts.append("if __name__ == '__main__':")
                    test_file_content_parts.append("    unittest.main()")

                    final_test_content = "\n".join(test_file_content_parts)
                    updated_code_map[str(test_file_path)] = final_test_content
                    print(f"   ➕ Added test file to map: {test_file_path}")

        if not generated_any_tests:
             print("✅ [UnitTestGeneratorAgent] No new tests generated.")
        else:
             print(f"✅ [UnitTestGeneratorAgent] Finished generating tests.")
        return updated_code_map

# Instantiate the agent for easy import
unit_test_generator = UnitTestGeneratorAgent()
