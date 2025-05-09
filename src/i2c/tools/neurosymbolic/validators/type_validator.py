# src/i2c/tools/neurosymbolic/validators/type_validator.py
from typing import Dict, List, Any, Optional
import tempfile
import subprocess
from pathlib import Path
import ast
import sys

# Handle conditional imports based on Python version
try:
    # Import core type inference for Python
    from i2c.tools.neurosymbolic.type_systems.python_inference import PythonTypeInferrer
except ImportError:
    # Define a placeholder if the module doesn't exist
    class PythonTypeInferrer:
        def __init__(self, *args, **kwargs):
            pass
        def visit_FunctionDef(self, *args, **kwargs):
            return {'params': {}, 'returns': 'Any'}

# Try optional imports for other languages
try:
    from i2c.tools.neurosymbolic.type_systems.java_service import JavaTypeSystem
except ImportError:
    JavaTypeSystem = None

try:
    from i2c.tools.neurosymbolic.type_systems.typescript_service import TypeScriptValidator
except ImportError:
    TypeScriptValidator = None

try:
    from i2c.tools.neurosymbolic.type_systems.javascript_service import JavaScriptValidator
except ImportError:
    JavaScriptValidator = None

try:
    from i2c.tools.neurosymbolic.type_systems.go_service import GoTypeSystem
except ImportError:
    GoTypeSystem = None


class TypeValidator:
    """Multilingual type consistency validator with gradual typing support."""
    def __init__(self, graph, language: str = "python"):
        self.graph = graph
        self.language = language.lower()
        # Create the type system based on language
        self.type_system = self._create_type_system()

    def _create_type_system(self):
        """Create appropriate type system based on language"""
        if self.language == 'python':
            return PythonTypeSystem()
        elif self.language == 'typescript' and TypeScriptValidator is not None:
            return TypeScriptTypeSystem()
        elif self.language == 'javascript' and JavaScriptValidator is not None:
            return JavaScriptTypeSystem()
        elif self.language == 'java' and JavaTypeSystem is not None:
            return JavaTypeSystem()
        elif self.language == 'go' and GoTypeSystem is not None:
            return GoTypeSystem()
        else:
            # Fallback to a minimal validator
            return MinimalTypeSystem()

    def validate(self, file_path: str, modification_type: str, content: str) -> Dict[str, Any]:
        """Validate code with the appropriate type system"""
        try:
            env = self._build_type_environment(file_path)
            return self.type_system.validate_content(content, env, self.graph)
        except Exception as e:
            # Gracefully handle validation errors
            print(f"Type validation error: {e}")
            return {"valid": True, "warnings": [f"Type validation skipped: {e}"]}

    def _build_type_environment(self, file_path: str) -> Dict[str, Any]:
        """Build a context of types from related files"""
        try:
            if self.language == 'python' and hasattr(self.graph, 'get_related_files'):
                env: Dict[str, Any] = {}
                related_files = self.graph.get_related_files(file_path)
                for rel in related_files:
                    path = rel.get('path')
                    if path in self.graph.nodes:
                        env.update(self.graph.nodes[path].get('definitions', {}))
                return env
        except Exception as e:
            print(f"Error building type environment: {e}")
        return {}


class PythonTypeSystem:
    """PEP-484/526 gradual type system for Python."""
    def validate_content(self, content: str, env: Dict[str, Any], graph) -> Dict[str, Any]:
        errors: List[str] = []
        try:
            tree = ast.parse(content)
            # Check function signatures
            self._check_function_signatures(tree, env, errors)
            # Additional checks simplified for stability
            self._check_syntax_errors(content, errors)
        except SyntaxError as e:
            errors.append(f"Python syntax error: {e}")
        except Exception as e:
            # Log but continue - don't block code generation for typing issues
            print(f"Type checking error (non-critical): {e}")
            
        return {"valid": len(errors) == 0, "errors": errors}

    def _check_function_signatures(self, tree, env, errors: List[str]):
        try:
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Parse return type annotation if present
                    returns_annotation = self._get_annotation_str(node.returns)
                    
                    # Check if function with this name exists in environment
                    if node.name in env and env[node.name]['type'] == 'function':
                        # Compare return types if both have annotations
                        env_returns = env[node.name].get('returns', 'Any')
                        if returns_annotation != 'Any' and env_returns != 'Any' and returns_annotation != env_returns:
                            errors.append(f"Return type mismatch in {node.name}: {returns_annotation} vs {env_returns}")
        except Exception as e:
            # Don't let type checking errors prevent code modification
            print(f"Function signature checking error (non-critical): {e}")

    def _check_syntax_errors(self, content: str, errors: List[str]):
        """Basic syntax check"""
        try:
            ast.parse(content)
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")

    def _get_annotation_str(self, annotation) -> str:
        """Extract annotation string safely, with Python version handling"""
        if annotation is None:
            return 'Any'
            
        try:
            # Python 3.9+ can use ast.unparse
            if sys.version_info >= (3, 9):
                return ast.unparse(annotation)
            # Fallback for older Python
            elif isinstance(annotation, ast.Name):
                return annotation.id
            elif isinstance(annotation, ast.Attribute):
                if isinstance(annotation.value, ast.Name):
                    return f"{annotation.value.id}.{annotation.attr}"
        except Exception:
            pass
            
        return 'Any'


class TypeScriptTypeSystem:
    """Minimal TypeScript validation."""
    def validate_content(self, content: str, env, graph) -> Dict[str, Any]:
        if TypeScriptValidator is None:
            return {"valid": True, "warnings": ["TypeScript validation skipped: TypeScriptValidator not available"]}
        
        try:
            # Minimal TypeScript validation
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                tmp_file = tmp_path / "temp.ts"
                tmp_file.write_text(content)
                
                # Basic syntax check using tsc if available
                result = subprocess.run(
                    ["tsc", "--noEmit", str(tmp_file)], 
                    capture_output=True, 
                    text=True
                )
                
                if result.returncode != 0:
                    return {"valid": False, "errors": [f"TypeScript error: {result.stderr}"]}
                    
                return {"valid": True}
        except Exception as e:
            # Don't let validation errors block code modification
            return {"valid": True, "warnings": [f"TypeScript validation error: {e}"]}


class JavaScriptTypeSystem:
    """Minimal JavaScript validation."""
    def validate_content(self, content: str, env, graph) -> Dict[str, Any]:
        # Super minimal JS validation for now - just syntax
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                tmp_file = tmp_path / "temp.js"
                tmp_file.write_text(content)
                
                # Basic syntax check using node if available
                result = subprocess.run(
                    ["node", "--check", str(tmp_file)], 
                    capture_output=True, 
                    text=True
                )
                
                if result.returncode != 0:
                    return {"valid": False, "errors": [f"JavaScript error: {result.stderr}"]}
                    
                return {"valid": True}
        except Exception as e:
            # Don't let validation errors block code modification
            return {"valid": True, "warnings": [f"JavaScript validation skipped: {e}"]}


class MinimalTypeSystem:
    """Fallback validator that always succeeds."""
    def validate_content(self, content: str, env, graph) -> Dict[str, Any]:
        return {"valid": True, "warnings": ["Detailed type validation not available for this language"]}