# src/i2c/tools/neurosymbolic/utils/ast_helpers.py
import ast
from typing import Dict, List, Tuple

def extract_imports(tree: ast.AST) -> List[Dict]:
    """Extract import statements from AST"""
    imports = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    'name': alias.name,
                    'alias': alias.asname,
                    'lineno': node.lineno
                })
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imports.append({
                    'name': f"{node.module}.{alias.name}",
                    'alias': alias.asname,
                    'lineno': node.lineno
                })
                
    return imports

def extract_definitions(tree: ast.AST) -> Dict:
    """Extract all top-level definitions from AST"""
    definitions = {}
    
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef):
            definitions[node.name] = {
                'type': 'function',
                'parameters': [arg.arg for arg in node.args.args],
                'returns': _get_return_type(node.returns),
                'lineno': node.lineno
            }
        elif isinstance(node, ast.ClassDef):
            definitions[node.name] = {
                'type': 'class',
                'bases': [base.id for base in node.bases],
                'lineno': node.lineno
            }
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    definitions[target.id] = {
                        'type': 'variable',
                        'value_type': _infer_type(node.value),
                        'lineno': node.lineno
                    }
                    
    return definitions

def _get_return_type(returns_node: ast.AST) -> str:
    """Infer return type from AST node"""
    if isinstance(returns_node, ast.Name):
        return returns_node.id
    return 'Any'

def _infer_type(node: ast.AST) -> str:
    """Infer variable type from assignment value"""
    if isinstance(node, ast.Constant):
        return type(node.value).__name__
    if isinstance(node, ast.Call):
        return _get_call_return_type(node)
    return 'Any'

def _get_call_return_type(node: ast.Call) -> str:
    """Infer return type from function call"""
    if isinstance(node.func, ast.Name):
        # Placeholder for type inference system
        return node.func.id if node.func.id in ['str', 'int'] else 'Any'
    return 'Any'