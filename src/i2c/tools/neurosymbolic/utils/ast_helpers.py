# Updated src/i2c/tools/neurosymbolic/utils/ast_helpers.py

import ast
from typing import Dict, List, Tuple, Any, Optional

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
            if node.module:  # Add null check
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
            # Fix for Python 3.11 compatibility with ast.ClassDef.bases
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(f"{_get_attribute_name(base)}")
                    
            definitions[node.name] = {
                'type': 'class',
                'bases': bases,
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

def _get_attribute_name(node: ast.Attribute) -> str:
    """
    Safely extract name from an attribute node, handling both simple and complex cases.
    For example, handles 'module.Class' properly.
    """
    if isinstance(node.value, ast.Name):
        return f"{node.value.id}.{node.attr}"
    elif isinstance(node.value, ast.Attribute):
        return f"{_get_attribute_name(node.value)}.{node.attr}"
    return f"???.{node.attr}"  # Fallback

def _get_return_type(returns_node: Optional[ast.AST]) -> str:
    """Infer return type from AST node"""
    if returns_node is None:
        return 'Any'
        
    if isinstance(returns_node, ast.Name):
        return returns_node.id
    elif isinstance(returns_node, ast.Attribute):
        return _get_attribute_name(returns_node)
    elif isinstance(returns_node, ast.Subscript):
        # Handle types like List[int], Dict[str, Any], etc.
        if isinstance(returns_node.value, ast.Name):
            return f"{returns_node.value.id}[...]"
        elif isinstance(returns_node.value, ast.Attribute):
            return f"{_get_attribute_name(returns_node.value)}[...]"
            
    return 'Any'

def _infer_type(node: ast.AST) -> str:
    """Infer variable type from assignment value"""
    if isinstance(node, ast.Constant):
        return type(node.value).__name__ if node.value is not None else 'None'
    if isinstance(node, ast.Call):
        return _get_call_return_type(node)
    if isinstance(node, ast.List):
        return 'List'
    if isinstance(node, ast.Dict):
        return 'Dict'
    if isinstance(node, ast.Set):
        return 'Set'
    if isinstance(node, ast.Tuple):
        return 'Tuple'
    return 'Any'

def _get_call_return_type(node: ast.Call) -> str:
    """Infer return type from function call"""
    if isinstance(node.func, ast.Name):
        # Placeholder for type inference system
        return node.func.id if node.func.id in ['str', 'int', 'bool', 'float', 'list', 'dict', 'set'] else 'Any'
    elif isinstance(node.func, ast.Attribute):
        return _get_attribute_name(node.func)
    return 'Any'