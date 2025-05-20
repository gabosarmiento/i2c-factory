# agents/sre_team/multilang_unit_test.py
"""Enhanced multi‑language unit‑test generator with Markdown‑fence stripping
and duplicate `unittest.main()` de‑duplication for Python files."""

import ast
from pathlib import Path
from agno.agent import Agent
from builtins import llm_middle

_LANG_TEMPLATES = {
    "python":     "Generate a Python `unittest` test case for `{func}` in `{module}.py`. "
                  "Include imports and **output only raw python code**.",
    "typescript": "Generate a Jest test case for `{func}` from `{module}.ts`. Include imports – output raw TS.",
    "javascript": "Generate a Mocha+Chai test case for `{func}` from `{module}.js`. Include imports.",
    "go":         "Generate a Go test for `{func}` from `{module}.go` using the testing package.",
    "java":       "Generate a JUnit 5 test method for `{func}` in class `{module}`.",
}


class MultiLangTestGeneratorAgent(Agent):
    """Generate unit tests for Python, TS, JS, Go, Java."""

    def __init__(self, **kw):
        super().__init__(
            name="MultiLangTestGenerator",
            model=llm_middle,
            description="Generates unit tests across languages.",
            instructions=[],
            **kw
        )
        print("🧪 [MultiLangTestGeneratorAgent] Ready.")

    # ------------ function discovery helpers ------------ #
    def _py_funcs(self, code:str):  # python
        try:
            tree = ast.parse(code)
            return [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
        except Exception:
            return []

    def _go_funcs(self, code:str):
        return [ln.split(" ")[1].split("(")[0] for ln in code.splitlines() if ln.strip().startswith("func ")]

    def _js_funcs(self, code:str):
        out = []
        for ln in code.splitlines():
            ln = ln.strip()
            if ln.startswith("function "):
                out.append(ln.split(" ")[1].split("(")[0])
            if ln.startswith("export function "):
                out.append(ln.split(" ")[2].split("(")[0])
        return out

    def _java_methods(self, code:str):
        return [ ln.split("(")[0].split()[-1]
                 for ln in code.splitlines()
                 if ln.strip().endswith(") {") and "class " not in ln ]

    # ------------ prompt + run ------------ #
    def _prompt(self, lang:str, module:str, func:str, code:str):
        header  = f"Source code from {module}.{lang}:\n```{lang}\n{code}\n```\n\n"
        return header + _LANG_TEMPLATES.get(lang, "")

    def _clean(self, test_code:str):
        """Remove markdown fences and leading ``` markers."""
        test_code = test_code.strip()
        if test_code.startswith("```"):
            # drop first ```lang and final ```
            test_code = re.sub(r"^```[a-zA-Z0-9_+]*", "", test_code, count=1, flags=re.MULTILINE).strip()
            if test_code.endswith("```"):
                test_code = test_code[:-3].rstrip()
        return test_code

    def _generate(self, lang:str, module:str, func:str, code:str):
        prompt = self._prompt(lang, module, func, code)
        resp = self.run(prompt)
        raw  = resp.content if hasattr(resp, "content") else str(resp)
        return self._clean(raw)

    # ------------ public API ------------ #
    def generate_tests(self, code_map:dict[str,str]) -> dict[str,str]:
        updated = code_map.copy()
        for fp, content in code_map.items():
            p = Path(fp)
            if p.stem.startswith("test_"):
                continue

            if p.suffix == ".py":
                lang, funcs, test_path = "python", self._py_funcs(content), p.parent / f"test_{p.stem}.py"
            elif p.suffix == ".ts":
                lang, funcs, test_path = "typescript", self._js_funcs(content), p.parent / f"{p.stem}.test.ts"
            elif p.suffix == ".js":
                lang, funcs, test_path = "javascript", self._js_funcs(content), p.parent / f"{p.stem}.test.js"
            elif p.suffix == ".go":
                lang, funcs, test_path = "go", self._go_funcs(content), p.parent / f"{p.stem}_test.go"
            elif p.suffix == ".java":
                lang, funcs, test_path = "java", self._java_methods(content), p.parent / f"{p.stem}Test.java"
            else:
                continue

            tests_out = []
            for f in funcs:
                tc = self._generate(lang, p.stem, f, content)
                if tc:
                    tests_out.append(tc)

            if tests_out:
                full = "\n\n".join(tests_out)
                # For Python – ensure only single unittest.main()
                if lang == "python" and full.count("unittest.main()") > 1:
                    parts = full.split("unittest.main()")
                    full = "unittest.main()".join(parts[:1] + ["# duplicate removed" + p for p in parts[1:-1]] + [parts[-1]])
                updated[str(test_path)] = full

        return updated


# Export instance so SRE team import remains unchanged
unit_test_generator = MultiLangTestGeneratorAgent()
