# src/i2c/tools/neurosymbolic/type_systems/python_inference.py

import ast
from typing import Dict, List, Union, Any
import sympy

class PythonTypeInferrer(ast.NodeVisitor):
    """Implements PEP 484-compliant gradual type inference with AST analysis."""
    
    def __init__(self, type_env: Dict[str, str]):
        """
        :param type_env: mapping of variable/function names → their declared or inferred types
        """
        self.type_env = type_env
        self.current_scope: Dict[str, str] = {}  # local variables within a function
        self.return_types: List[str] = []
        self.param_types: Dict[str, str] = {}

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """
        Infer a function’s parameter and return types.
        Returns: {'params': {param_name: type_str, ...}, 'returns': return_type_str}
        """
        # Reset per-function state
        self.current_scope.clear()
        self.return_types.clear()
        self.param_types.clear()

        # Parameters: use annotation if present, otherwise fallback to type_env or Any
        for arg in node.args.args:
            if arg.annotation:
                t = self._annotation_to_str(arg.annotation)
            else:
                t = self._infer_usage(arg.arg)
            self.param_types[arg.arg] = t
            self.current_scope[arg.arg] = t

        # Walk the body to collect return expressions
        for stmt in node.body:
            if isinstance(stmt, ast.Return) and stmt.value is not None:
                self.return_types.append(self._infer_expr(stmt.value))
            else:
                # descend into nested statements
                self.generic_visit(stmt)

        return {
            'params': dict(self.param_types),
            'returns': self._unify_types(set(self.return_types)) if self.return_types else 'None'
        }

    def _infer_usage(self, name: str) -> str:
        """Fallback lookup for names not annotated: first local, then global env."""
        return self.current_scope.get(name, self.type_env.get(name, 'Any'))

    def _infer_expr(self, node: ast.AST) -> str:
        """Recursively infer the type of an expression node."""
        if isinstance(node, ast.Name):
            return self._infer_usage(node.id)
        if isinstance(node, ast.Constant):
            return type(node.value).__name__
        if isinstance(node, ast.Call):
            # simplest heuristic: if calling a builtin casting function
            func = node.func
            if isinstance(func, ast.Name) and func.id in {'int','str','bool','float'}:
                return func.id
            # else unknown
            return 'Any'
        if isinstance(node, ast.BinOp):
            left = self._infer_expr(node.left)
            right = self._infer_expr(node.right)
            # if both sides same, return that, else Union
            return left if left == right else f"Union[{left},{right}]"
        if isinstance(node, ast.Attribute):
            base = self._infer_expr(node.value)
            return f"{base}.{node.attr}"
        if isinstance(node, ast.List):
            # infer element types
            elts = {self._infer_expr(e) for e in node.elts}
            et = self._unify_types(elts)
            return f"List[{et}]"
        # default fallback
        return 'Any'

    def _unify_types(self, types: set) -> str:
        """Unify a set of type names into a single string or Union."""
        if not types:
            return 'Any'
        if len(types) == 1:
            return types.pop()
        return f"Union[{','.join(sorted(types))}]"

    def _annotation_to_str(self, annotation: ast.AST) -> str:
        """Convert an annotation AST node to its string repr."""
        try:
            # available in Python 3.9+
            return ast.unparse(annotation)
        except Exception:
            # fallback for older Pythons
            if isinstance(annotation, ast.Name):
                return annotation.id
            return 'Any'
