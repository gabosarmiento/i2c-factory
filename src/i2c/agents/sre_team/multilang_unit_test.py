# agents/sre_team/multilang_unit_test.py
"""Enhanced multi‑language unit‑test generator with proper language detection,
markdown fence stripping, and robust error handling."""

import ast
import re
from pathlib import Path
from agno.agent import Agent
from builtins import llm_middle

_LANG_TEMPLATES = {
    "python": "Generate a Python `unittest` test case for `{func}` in `{module}.py`. "
              "Include imports and **output only raw python code**.",
    "typescript": "Generate a Jest test case for `{func}` from `{module}.ts`. Include imports – output raw TS.",
    "javascript": "Generate a Mocha+Chai test case for `{func}` from `{module}.js`. Include imports.",
    "go": "Generate a Go test for `{func}` from `{module}.go` using the testing package.",
    "java": "Generate a JUnit 5 test method for `{func}` in class `{module}`.",
}

class MultiLangTestGeneratorAgent(Agent):
    """Generate unit tests for Python, TypeScript, JavaScript, Go, Java."""

    def __init__(self, **kw):
        super().__init__(
            name="MultiLangTestGenerator",
            model=llm_middle,
            description="Generates unit tests across multiple programming languages.",
            instructions=[
                "You are an expert test generator for multiple programming languages.",
                "Generate high-quality, executable unit tests for given functions.",
                "Follow language-specific testing conventions and frameworks.",
                "Output clean, properly formatted code without markdown fences.",
                "Include necessary imports and proper test structure."
            ],
            **kw
        )
        print("🧪 [MultiLangTestGeneratorAgent] Ready for multi-language test generation.")

    def _detect_language_from_extension(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext = Path(file_path).suffix.lower()
        language_map = {
            '.py': 'python',
            '.ts': 'typescript', 
            '.js': 'javascript',
            '.go': 'go',
            '.java': 'java'
        }
        return language_map.get(ext, 'unknown')

    def _get_test_file_name(self, file_path: str, language: str) -> str:
        """Generate appropriate test file name for the language."""
        p = Path(file_path)
        if language == "python":
            return str(p.parent / f"test_{p.stem}.py")
        elif language == "typescript":
            return str(p.parent / f"{p.stem}.test.ts")
        elif language == "javascript":
            return str(p.parent / f"{p.stem}.test.js")
        elif language == "go":
            return str(p.parent / f"{p.stem}_test.go")
        elif language == "java":
            return str(p.parent / f"{p.stem}Test.java")
        else:
            return str(p.parent / f"test_{p.stem}.txt")

    # ------------ Function discovery helpers ------------ #
    def _py_funcs(self, code: str) -> list[str]:
        """Extract Python function names using AST."""
        try:
            tree = ast.parse(code)
            return [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
        except Exception as e:
            print(f"   ⚠️ Python AST parsing failed: {e}")
            return []

    def _go_funcs(self, code: str) -> list[str]:
        """Extract Go function names using regex."""
        try:
            pattern = r'func\s+(\w+)\s*\('
            matches = re.findall(pattern, code)
            return [match for match in matches if not match.startswith('Test')]
        except Exception as e:
            print(f"   ⚠️ Go function extraction failed: {e}")
            return []

    def _js_funcs(self, code: str) -> list[str]:
        """Extract JavaScript/TypeScript function names."""
        try:
            functions = []
            # Match various JS/TS function patterns
            patterns = [
                r'function\s+(\w+)\s*\(',           # function name()
                r'export\s+function\s+(\w+)\s*\(',  # export function name()
                r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>', # const name = () =>
                r'(\w+)\s*:\s*function\s*\(',       # name: function()
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, code)
                functions.extend(matches)
            
            return list(set(functions))  # Remove duplicates
        except Exception as e:
            print(f"   ⚠️ JavaScript function extraction failed: {e}")
            return []

    def _java_methods(self, code: str) -> list[str]:
        """Extract Java method names."""
        try:
            # Match public/private methods but not constructors
            pattern = r'(?:public|private|protected)\s+(?:static\s+)?(?!class|interface)\w+\s+(\w+)\s*\([^)]*\)\s*\{'
            matches = re.findall(pattern, code)
            return matches
        except Exception as e:
            print(f"   ⚠️ Java method extraction failed: {e}")
            return []

    def _extract_functions(self, code: str, language: str) -> list[str]:
        """Extract function names based on language."""
        if language == "python":
            return self._py_funcs(code)
        elif language == "go":
            return self._go_funcs(code)
        elif language in ["javascript", "typescript"]:
            return self._js_funcs(code)
        elif language == "java":
            return self._java_methods(code)
        else:
            print(f"   ⚠️ Function extraction not implemented for {language}")
            return []

    # ------------ Test generation ------------ #
    def _clean_response(self, test_code: str) -> str:
        """Remove markdown fences and clean up response."""
        test_code = test_code.strip()
        
        # Remove markdown code fences
        if test_code.startswith("```"):
            lines = test_code.split('\n')
            # Remove first line (```language)
            lines = lines[1:]
            # Remove last line if it's just ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            test_code = '\n'.join(lines).strip()
        
        return test_code

    def _generate_test_for_function(self, language: str, module: str, func: str, code: str) -> str:
        """Generate test code for a single function."""
        template = _LANG_TEMPLATES.get(language, "Generate a test for `{func}` from `{module}`.")
        prompt = f"Source code from {module}.{language}:\n```{language}\n{code}\n```\n\n{template.format(func=func, module=module)}"
        
        try:
            response = self.run(prompt)
            raw_test = response.content if hasattr(response, 'content') else str(response)
            return self._clean_response(raw_test)
        except Exception as e:
            print(f"   ❌ Error generating test for {func}: {e}")
            return ""

    def _consolidate_tests(self, tests: list[str], language: str) -> str:
        """Consolidate multiple test functions into a single test file."""
        if not tests:
            return ""
        
        # Filter out empty tests
        valid_tests = [test for test in tests if test.strip()]
        if not valid_tests:
            return ""
        
        if language == "python":
            # For Python, ensure single unittest.main()
            combined = "\n\n".join(valid_tests)
            
            # Remove duplicate unittest.main() calls
            if combined.count("unittest.main()") > 1:
                # Remove all unittest.main() and add one at the end
                combined = re.sub(r'if __name__ == ["\']__main__["\']:\s*unittest\.main\(\)', '', combined)
                combined = re.sub(r'unittest\.main\(\)', '', combined)
                combined = combined.strip() + "\n\nif __name__ == '__main__':\n    unittest.main()"
            
            return combined
        else:
            # For other languages, just join the tests
            return "\n\n".join(valid_tests)

    # ------------ Public API ------------ #
    def generate_tests(self, code_map: dict[str, str]) -> dict[str, str]:
        """Generate unit tests for all supported files in the code map."""
        print("🤖 [MultiLangTestGeneratorAgent] Generating multi-language unit tests...")
        updated_map = code_map.copy()
        
        for file_path, content in code_map.items():
            # Skip existing test files
            if self._is_test_file(file_path):
                print(f"   ⚪ Skipping existing test file: {file_path}")
                continue
            
            language = self._detect_language_from_extension(file_path)
            if language == "unknown":
                print(f"   ⚪ Skipping unsupported file: {file_path}")
                continue
            
            print(f"   🔍 Processing {file_path} ({language})")
            
            # Extract functions/methods
            functions = self._extract_functions(content, language)
            if not functions:
                print(f"      No functions found in {file_path}")
                continue
            
            print(f"      Found {len(functions)} function(s): {functions}")
            
            # Generate tests for each function
            test_parts = []
            module_name = Path(file_path).stem
            
            for func_name in functions:
                test_code = self._generate_test_for_function(language, module_name, func_name, content)
                if test_code:
                    test_parts.append(test_code)
            
            # Consolidate and save tests
            if test_parts:
                consolidated_tests = self._consolidate_tests(test_parts, language)
                if consolidated_tests:
                    test_file_path = self._get_test_file_name(file_path, language)
                    updated_map[test_file_path] = consolidated_tests
                    print(f"   ✅ Generated test file: {test_file_path}")
            else:
                print(f"      No tests generated for {file_path}")
        
        tests_generated = len(updated_map) - len(code_map)
        print(f"✅ [MultiLangTestGeneratorAgent] Generated {tests_generated} test file(s)")
        return updated_map

    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is already a test file."""
        name = Path(file_path).name.lower()
        return (name.startswith('test_') or 
                name.endswith('_test.py') or 
                '.test.' in name or 
                name.endswith('test.js') or 
                name.endswith('test.ts') or 
                name.endswith('Test.java'))

# Export enhanced multi-language unit test generator
unit_test_generator = MultiLangTestGeneratorAgent()

# Add quality constraints
unit_test_generator.quality_constraints = [
    "Generate tests that follow language-specific conventions",
    "Ensure proper imports and test structure", 
    "Include meaningful test cases and assertions",
    "Handle edge cases and error conditions",
    "Use appropriate testing frameworks for each language"
]