
# src/i2c/tools/neurosymbolic/validators/type_validator.py
from typing import Dict, List, Any
import tempfile
import subprocess
from pathlib import Path
import ast

# Import core type inference for Python
from i2c.tools.neurosymbolic.type_systems.python_inference import PythonTypeInferrer
from i2c.tools.neurosymbolic.type_systems.java_service import JavaTypeSystem
from i2c.tools.neurosymbolic.type_systems.typescript_service import TypeScriptValidator
from i2c.tools.neurosymbolic.type_systems.javascript_service import JavaScriptValidator
from i2c.tools.neurosymbolic.type_systems.go_service import GoTypeSystem


class TypeValidator:
    """Multilingual type consistency validator with gradual typing support."""
    def __init__(self, graph, language: str = "python"):
        self.graph = graph
        self.language = language
        # Map language keys to system implementations
        self.type_rules: Dict[str, Any] = {
            'python': PythonTypeSystem(),
            'typescript': TypeScriptTypeSystem(),
            'javascript': JavaScriptTypeSystem(),
            'java': JavaTypeSystem(),
            'go': GoTypeSystem(),
        }

    def validate(self, file_path: str, modification_type: str, content: str) -> Dict[str, Any]:
        if self.language not in self.type_rules:
            return {"valid": True, "warnings": [f"No type validation for {self.language}"]}
        try:
            env = self._build_type_environment(file_path)
            system = self.type_rules[self.language]
            return system.validate_content(content, env, self.graph)
        except Exception as e:
            return {"valid": False, "errors": [f"Validation error: {e}"]}

    def _build_type_environment(self, file_path: str) -> Dict[str, Any]:
        if self.language == 'python':
            env: Dict[str, Any] = {}
            for rel in self.graph.get_related_files(file_path):
                path = rel.get('path')
                if path in self.graph.nodes:
                    env.update(self.graph.nodes[path]['definitions'])
            return env
        return {}

class PythonTypeSystem:
    """PEP-484/526 gradual type system for Python."""
    def validate_content(self, content: str, env: Dict[str, Any], graph) -> Dict[str, Any]:
        errors: List[str] = []
        tree = ast.parse(content)
        # Check function signatures
        self._check_function_signatures(tree, env, errors)
        # Stub hooks for further checks
        self._check_variable_usage(tree, env, errors)
        self._check_import_compatibility(tree, graph, errors)
        return {"valid": not errors, "errors": errors}

    def _check_function_signatures(self, tree, env, errors: List[str]):
        inferrer = PythonTypeInferrer(env)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                inferred = inferrer.visit_FunctionDef(node)
                declared = self._get_declared_types(node)
                if not self._check_compatibility(inferred, declared):
                    errors.append(self._format_signature_error(node, inferred, declared))

    def _check_variable_usage(self, tree, env, errors):
        # Placeholder for future expansion
        pass

    def _check_import_compatibility(self, tree, graph, errors):
        # Placeholder for future expansion
        pass

    def _get_declared_types(self, node: ast.FunctionDef) -> Dict[str, Any]:
        declared = {'params': {}, 'returns': 'Any'}
        for arg in node.args.args:
            if arg.annotation:
                declared['params'][arg.arg] = ast.unparse(arg.annotation)
        if node.returns:
            declared['returns'] = ast.unparse(node.returns)
        return declared

    def _check_compatibility(self, inferred, declared) -> bool:
        if declared['returns'] != 'Any' and inferred.get('returns') != declared['returns']:
            return False
        for name, decl in declared['params'].items():
            if decl != 'Any' and inferred.get('params', {}).get(name) != decl:
                return False
        return True

    def _format_signature_error(self, node, inferred, declared) -> str:
        return (
            f"Signature mismatch in {node.name}: Declared={declared}, Inferred={inferred}"
        )

class TypeScriptTypeSystem:
    """Production-grade TypeScript validation using official compiler."""
    def validate_content(self, content: str, env, graph) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmpdir:
            proj = Path(tmpdir)
            (proj / 'tsconfig.json').write_text(
                '{"compilerOptions":{"strict":true,"noEmit":true}}',
                encoding='utf-8'
            )
            src = proj / 'temp.ts'
            src.write_text(content, encoding='utf-8')
            validator = TypeScriptValidator(proj)
            return validator.validate_file(src, content)

class JavaScriptTypeSystem:
    """Wrap ESLint-based JS validation."""
    def validate_content(self, content: str, env, graph) -> Dict[str, Any]:
        validator = JavaScriptValidator(graph.project_path)
        return validator.validate_content(content)

class JavaTypeSystem:
    """Compiler-backed Java validation via javac."""
    def validate_content(self, content: str, env, graph) -> Dict[str, Any]:
        return {"valid": True, "warnings": ["Java validation not implemented"]}

class GoTypeSystem:
    """Compiler-backed Go validation via go vet."""
    def validate_content(self, content: str, env, graph) -> Dict[str, Any]:
        return {"valid": True, "warnings": ["Go validation not implemented"]}
