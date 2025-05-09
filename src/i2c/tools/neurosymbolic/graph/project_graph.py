# src/i2c/tools/neurosymbolic/graph/project_graph.py

import ast
from pathlib import Path
from typing import Dict, List, Optional, Any

from i2c.tools.neurosymbolic.utils.ast_helpers import extract_imports, extract_definitions


class ProjectGraph:
    """Builds and maintains the semantic graph of a Python project."""

    def __init__(self, project_path: Path):
        self.project_path: Path = project_path
        self.nodes: Dict[str, Dict[str, Any]] = {}  # rel_path -> metadata
        self.edges: Dict[str, List[Dict[str, str]]] = {}  # from_rel_path -> list of edges

    def build(self) -> None:
        """Parse every .py file into nodes, then resolve cross-file imports into edges."""
        # 1) Collect nodes
        for abs_path in self.project_path.rglob("*.py"):
            try:
                rel_path = abs_path.relative_to(self.project_path)
                self._process_file(abs_path, rel_path)
            except Exception as e:
                print(f"[ProjectGraph] Error processing {abs_path}: {e}")

        # 2) Build import edges
        self._build_relationships()

    def _process_file(self, abs_path: Path, rel_path: Path) -> None:
        """Parse a single file into AST, extract imports & definitions."""
        content = abs_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(abs_path))

        imports = extract_imports(tree)
        definitions = extract_definitions(tree)

        key = str(rel_path)
        self.nodes[key] = {
            "path": key,
            "imports": imports,
            "definitions": definitions,
            "content": content,
            "tree": tree,
        }

    def _build_relationships(self) -> None:
        """For every node, resolve its imports to other files and record edges."""
        for src, meta in self.nodes.items():
            for imp in meta["imports"]:
                target = self._resolve_import(str(src), imp["name"])
                if target:
                    self.edges.setdefault(src, []).append({
                        "target": target,
                        "type": "import",
                        "name": imp["name"],
                        "alias": imp.get("alias", "")
                    })

    def _resolve_import(self, from_rel: str, module_name: str) -> Optional[str]:
        """
        Turn a module path like 'pkg.sub' into a relative file path 'pkg/sub.py',
        if that file exists in the project.
        """
        parts = module_name.split(".")
        candidate = self.project_path.joinpath(*parts).with_suffix(".py")
        if candidate.exists():
            return str(candidate.relative_to(self.project_path))
        return None

    def get_related_files(self, file_path: str) -> List[Dict[str, str]]:
        """
        Returns a list of dicts:
          - files this file imports from
          - files that import this file
        Each dict has keys: path, relationship ('imports_from' or 'imported_by'), name.
        """
        related: List[Dict[str, str]] = []

        # Outgoing (imports_from)
        for edge in self.edges.get(file_path, []):
            related.append({
                "path": edge["target"],
                "relationship": "imports_from",
                "name": edge["name"],
            })

        # Incoming (imported_by)
        for src, eds in self.edges.items():
            for edge in eds:
                if edge["target"] == file_path:
                    related.append({
                        "path": src,
                        "relationship": "imported_by",
                        "name": edge["name"],
                    })

        return related

    def extract_patterns(self, file_path: str) -> Dict[str, Any]:
        """
        Simple pattern extraction:
          - function_patterns: list of function names in this file
          - error_handling: occurrences of try/except blocks
          - naming: stub for future detailed naming conventions
        """
        patterns: Dict[str, Any] = {
            "function_patterns": [],
            "error_handling": [],
            "naming": []
        }

        node_meta = self.nodes.get(file_path)
        if not node_meta:
            return patterns

        tree = node_meta["tree"]

        # Function names
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef):
                patterns["function_patterns"].append(n.name)

        # Error handling blocks
        for n in ast.walk(tree):
            if isinstance(n, ast.Try):
                patterns["error_handling"].append("try/except block")

        # Placeholder for naming conventions
        # e.g. collect all variable names:
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if hasattr(t, "id"):
                        patterns["naming"].append(t.id)

        return patterns
