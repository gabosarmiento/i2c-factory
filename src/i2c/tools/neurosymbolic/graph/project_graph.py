# src/i2c/tools/neurosymbolic/graph/project_graph.py

import ast
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import traceback

from i2c.tools.neurosymbolic.utils.ast_helpers import extract_imports, extract_definitions


class ProjectGraph:
    """Builds and maintains the semantic graph of a Python project."""

    def __init__(self, project_path: Path, target_file: Optional[str] = None):
        self.project_path: Path = project_path
        self.target_file: Optional[str] = target_file  # Optional target file to focus on
        self.nodes: Dict[str, Dict[str, Any]] = {}  # rel_path -> metadata
        self.edges: Dict[str, List[Dict[str, str]]] = {}  # from_rel_path -> list of edges
        self.parse_errors: Dict[str, str] = {}  # Track files with parse errors
        
        # Always skip these directories
        self.skip_dirs: Set[str] = {
            "output",        # Skip ALL output directories
            "__pycache__",   # Skip Python cache dirs
            ".git",          # Skip git directory
            "venv",          # Skip virtual environments
            ".venv",
            ".pytest_cache",
            "node_modules"
        }

    def build(self) -> None:
        """
        Build graph focusing only on relevant files.
        If target_file is specified, only includes files directly related to the target.
        """
        if self.target_file:
            # Target-focused approach: Only analyze the target file and its immediate imports
            self._build_targeted_graph()
        else:
            # Limited but more complete approach for when no target is specified
            self._build_limited_graph()

    def _build_targeted_graph(self) -> None:
        """Build a minimal graph focused on the target file and its direct dependencies."""
        if not self.target_file:
            print("[ProjectGraph] No target file specified, cannot build targeted graph")
            return
            
        # Convert string to Path if needed
        target_path = self.target_file if isinstance(self.target_file, Path) else Path(self.target_file)
        
        # Make sure we have an absolute path for the target
        if not target_path.is_absolute():
            target_path = self.project_path / target_path
            
        # Get relative path from project root
        try:
            rel_target = target_path.relative_to(self.project_path)
        except ValueError:
            # If target is outside project root, use it as-is
            rel_target = target_path
        
        # Process the target file first
        try:
            self._process_file(target_path, rel_target)
            print(f"[ProjectGraph] Processed target file: {rel_target}")
        except Exception as e:
            print(f"[ProjectGraph] Error processing target file {target_path}: {e}")
            return
            
        # Find immediate dependencies - files that target imports
        # This would need imports analysis, skipping for simplicity
            
        # Find immediate dependents - files that import the target
        # Skip for now - would require parsing many files
            
        print(f"[ProjectGraph] Built targeted graph with {len(self.nodes)} nodes")
        
        # Build relationships
        self._build_relationships()

    def _build_limited_graph(self) -> None:
        """Build a limited graph, skipping known problematic directories."""
        file_count = 0
        processed_count = 0
        
        # Find files to analyze
        for abs_path in self.project_path.rglob("*.py"):
            file_count += 1
            
            try:
                # Skip files in excluded directories
                if any(skip_dir in str(abs_path) for skip_dir in self.skip_dirs):
                    continue
                    
                # Process file
                rel_path = abs_path.relative_to(self.project_path)
                self._process_file(abs_path, rel_path)
                processed_count += 1
                
            except Exception as e:
                print(f"[ProjectGraph] Error examining path {abs_path}: {e}")
                
            # Limit number of files analyzed to prevent excessive processing
            if processed_count >= 100:  # Reasonable limit
                print(f"[ProjectGraph] Reached file limit (100), stopping graph building")
                break

        print(f"[ProjectGraph] Processed {processed_count} of {file_count} Python files")
        
        # Build relationships
        self._build_relationships()

    def _process_file(self, abs_path: Path, rel_path: Path) -> None:
        """Parse a single file into AST, extract imports & definitions."""
        key = str(rel_path)
        
        try:
            # 1. Read file content
            try:
                content = abs_path.read_text(encoding="utf-8", errors='replace')
            except Exception as e:
                print(f"[ProjectGraph] Error reading {abs_path}: {e}")
                self.parse_errors[key] = f"File read error: {e}"
                return
                
            # 2. Parse AST
            try:
                tree = ast.parse(content, filename=str(abs_path))
            except SyntaxError as e:
                # For syntax errors, create a minimal node with just the content
                self.nodes[key] = {
                    "path": key,
                    "imports": [],
                    "definitions": {},
                    "content": content,
                    "tree": None,
                    "parse_error": f"Syntax error: {e}"
                }
                print(f"[ProjectGraph] Syntax error in {abs_path}: {e}")
                self.parse_errors[key] = f"Syntax error: {e}"
                return
            except Exception as e:
                print(f"[ProjectGraph] Parse error in {abs_path}: {e}")
                self.parse_errors[key] = f"Parse error: {e}"
                return
                
            # 3. Extract data from AST
            try:
                imports = extract_imports(tree)
                definitions = extract_definitions(tree)
            except Exception as e:
                print(f"[ProjectGraph] Error extracting data from {abs_path}: {e}")
                # Fall back to empty imports/definitions
                imports = []
                definitions = {}
                
            # 4. Store the node
            self.nodes[key] = {
                "path": key,
                "imports": imports,
                "definitions": definitions,
                "content": content,
                "tree": tree,
            }
            
        except Exception as e:
            # Catch-all for any other errors
            print(f"[ProjectGraph] Unexpected error processing {abs_path}: {e}")
            self.parse_errors[key] = f"Unexpected error: {e}"
            return

    def _build_relationships(self) -> None:
        """For every node, resolve its imports to other files and record edges."""
        for src, meta in self.nodes.items():
            # Skip nodes with parse errors (no imports)
            if "parse_error" in meta:
                continue
                
            for imp in meta.get("imports", []):
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
        try:
            parts = module_name.split(".")
            candidate = self.project_path.joinpath(*parts).with_suffix(".py")
            if candidate.exists():
                return str(candidate.relative_to(self.project_path))
                
            # Also check for __init__.py in package directories
            init_path = self.project_path.joinpath(*parts, "__init__.py")
            if init_path.exists():
                return str(init_path.relative_to(self.project_path))
                
        except Exception as e:
            print(f"[ProjectGraph] Error resolving import {module_name}: {e}")
            
        return None

    def get_related_files(self, file_path: str) -> List[Dict[str, str]]:
        """
        Returns a list of dicts:
          - files this file imports from
          - files that import this file
        Each dict has keys: path, relationship ('imports_from' or 'imported_by'), name.
        """
        related: List[Dict[str, str]] = []

        try:
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
        except Exception as e:
            print(f"[ProjectGraph] Error getting related files for {file_path}: {e}")
            
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

        try:
            node_meta = self.nodes.get(file_path)
            if not node_meta:
                return patterns
                
            # Skip if there was a parse error
            if "parse_error" in node_meta or node_meta.get("tree") is None:
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

            # Naming conventions - collect variable names
            for n in ast.walk(tree):
                if isinstance(n, ast.Assign):
                    for t in n.targets:
                        if isinstance(t, ast.Name):
                            patterns["naming"].append(t.id)
        except Exception as e:
            print(f"[ProjectGraph] Error extracting patterns from {file_path}: {e}")
            
        return patterns