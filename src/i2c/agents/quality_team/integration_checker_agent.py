# /agents/quality_team/integration_checker_agent.py
# Agent responsible for basic cross-file consistency checks (imports vs. calls).
# Refined version based on user suggestion.

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Any

# Import CLI for logging
try:
    from i2c.cli.controller import canvas
except ImportError:
    class FallbackCanvas: # Basic fallback logger
        def warning(self, msg): print(f"[WARN_INT] {msg}")
        def error(self, msg): print(f"[ERROR_INT] {msg}")
        def info(self, msg): print(f"[INFO_INT] {msg}")
        def success(self, msg): print(f"[SUCCESS_INT] {msg}")
    canvas = FallbackCanvas()

class _ProjectStructureVisitor(ast.NodeVisitor):
    """
    AST Visitor that collects:
      - defined functions and methods (bare names)
      - defined classes (bare names)
      - import aliases/names
      - function/method calls (bare names)
    """
    def __init__(self, relative_path: str):
        self.relative_path = relative_path
        self.defined_functions: Set[str] = set()
        self.defined_classes: Set[str] = set()
        self.imports: Set[str] = set()      # alias or name imported
        self.calls: Set[str] = set()        # bare call names

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.defined_functions.add(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.defined_functions.add(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.defined_classes.add(node.name)
        # Store defined method names without class qualification
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.defined_functions.add(item.name) # Store bare method name
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            # Store the name used to refer to the import in this file
            self.imports.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        # Store the names actually imported (or their aliases)
        for alias in node.names:
            self.imports.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        func = node.func
        call_name = None
        if isinstance(func, ast.Name): # Direct call: my_func()
            call_name = func.id
        elif isinstance(func, ast.Attribute): # Attribute/Method call: obj.method() or module.func()
            # Collect only the final attribute name (method or function name)
            call_name = func.attr
        if call_name:
            self.calls.add(call_name)
        self.generic_visit(node)


class IntegrationCheckerAgent:
    """
    Performs basic cross-file consistency checks in a Python project:
      - Scans .py files using AST.
      - Builds a set of all defined functions, classes, and imported names.
      - Checks if bare function/method call names exist in the global set (or are built-ins).
    """
    COMMON_BUILTINS = {
        'print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict', 'set',
        'tuple', 'open', 'super', 'isinstance', 'hasattr', 'getattr', 'setattr',
        'Exception', 'ValueError', 'TypeError', 'AttributeError', 'NameError',
        'KeyError', 'IndexError', 'RuntimeError', 'NotImplementedError',
        '__init__', '__str__', '__repr__', '__eq__', '__len__', # Common dunder methods often called
        'append', 'extend', 'insert', 'remove', 'pop', 'clear', 'index', 'count', # List methods
        'get', 'keys', 'values', 'items', 'update', 'popitem', # Dict methods
        'add', 'update', 'remove', 'discard', 'pop', 'clear', # Set methods
        'format', 'strip', 'lstrip', 'rstrip', 'join', 'split', 'replace', # String methods
        'lower', 'upper', 'capitalize', 'startswith', 'endswith',
        # Add more common library functions if needed (e.g., 'json.loads', 'os.path.join')
        # but be careful not to make the list too large or hide real issues.
        'loads', 'dumps', # from json
        'join', 'exists', 'isdir', 'isfile', 'splitext', 'basename', 'dirname', # from os.path
    }

    SKIP_DIRS = {'__pycache__', '.git', '.venv', 'node_modules'}

    def __init__(self):
        print("🔗 [IntegrationCheckerAgent] Initialized.")

    def _parse_file(self, file_path: Path, project_root: Path) -> _ProjectStructureVisitor | None:
        """Parses a single Python file using AST and returns the visitor."""
        try:
            # Ensure we don't read massive files
            if file_path.stat().st_size > 1 * 1024 * 1024: # 1MB limit
                 canvas.warning(f"[IntCheck] Skipping large file: {file_path.name}")
                 return None
            content = file_path.read_text(encoding='utf-8')
            if not content.strip():
                return None # Skip empty files
            tree = ast.parse(content, filename=str(file_path))
            # Use relative path from project root for clarity in reports
            rel_path = str(file_path.relative_to(project_root))
            visitor = _ProjectStructureVisitor(rel_path)
            visitor.visit(tree)
            return visitor
        except SyntaxError as e:
            canvas.warning(f"[IntCheck] SyntaxError parsing {file_path.relative_to(project_root)}: {e}")
        except Exception as e:
            canvas.warning(f"[IntCheck] Error parsing {file_path.relative_to(project_root)}: {e}")
        return None

    def check_integrations(self, project_path: Path) -> List[str]:
        """
        Scans all .py files under project_path, builds a symbol table,
        and reports any bare call name not found in definitions/imports/builtins.
        """
        canvas.info(f"🤖 [IntegrationCheckerAgent] Checking integrations in: {project_path}")
        issues: List[str] = []
        if not project_path.is_dir():
            return ["Project path is not a valid directory."]

        # 1) Parse files and collect data
        parsed_data: Dict[str, _ProjectStructureVisitor] = {}
        files_scanned_count = 0
        for file_path in project_path.rglob("*.py"):
            # Check if any part of the path relative to the project root is in SKIP_DIRS
            relative_parts = set(file_path.relative_to(project_path).parts)
            if relative_parts & self.SKIP_DIRS: # Efficient check using set intersection
                continue

            files_scanned_count += 1
            visitor = self._parse_file(file_path, project_path)
            if visitor:
                parsed_data[visitor.relative_path] = visitor
        canvas.info(f"[IntCheck] Scanned {files_scanned_count} Python files, successfully parsed {len(parsed_data)}.")

        if not parsed_data:
             canvas.warning("[IntegrationCheckerAgent] No Python files parsed. Skipping checks.")
             return issues # Return empty list

        # 2) Build global set of defined/imported symbols
        # This set contains names that *could* be valid targets for a call
        globally_known_symbols: Set[str] = set(self.COMMON_BUILTINS)
        for visitor in parsed_data.values():
            globally_known_symbols.update(visitor.defined_functions)
            globally_known_symbols.update(visitor.defined_classes)
            globally_known_symbols.update(visitor.imports) # Add all imported names/aliases

        # 3) Check calls made in each file against the global set
        canvas.info("[IntCheck] Checking function/method calls against known symbols...")
        for rel_path, visitor in parsed_data.items():
            # Check only the calls made within this specific file
            for call_name in sorted(visitor.calls):
                # If the bare name called is not defined/imported anywhere or a common built-in...
                if call_name not in globally_known_symbols:
                    # ...report it as a potential issue.
                    issue = (
                        f"Potential undefined call in '{rel_path}': Name '{call_name}' "
                        "might not be defined, imported, or is not a common built-in."
                    )
                    # Avoid adding duplicate warnings for the same call in the same file if AST visits it multiple times
                    if issue not in issues:
                         issues.append(issue)
                         canvas.warning(f"   [IntCheck] {issue}") # Log as warning

        # 4. Report Summary
        if not issues:
            canvas.success("[IntegrationCheckerAgent] No obvious undefined call issues found.")
        else:
            canvas.warning(f"[IntegrationCheckerAgent] Found {len(issues)} potential undefined call issue(s).")

        return issues


# Instantiate globally
integration_checker_agent = IntegrationCheckerAgent()
