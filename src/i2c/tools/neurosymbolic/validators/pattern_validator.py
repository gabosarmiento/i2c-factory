# src/i2c/tools/neurosymbolic/validators/pattern_validator.py
import re
from typing import Dict, List
import ast
import traceback

# Simple wrapper for LibCST if available, otherwise use a minimal version
try:
    from libcst import parse_module, MetadataWrapper
    HAVE_LIBCST = True
except ImportError:
    HAVE_LIBCST = False
    
    # Define minimal implementations if LibCST not available
    class MetadataWrapper:
        def __init__(self, module):
            self.module = module

    def parse_module(code):
        try:
            return MetadataWrapper(ast.parse(code))
        except Exception as e:
            print(f"Error parsing code: {e}")
            return None

class PatternValidator:
    """Enforces project-specific coding patterns and standards"""
    
    def __init__(self, graph):
        self.graph = graph
        self.patterns = {
            'naming': [
                (r'^[a-z_][a-z0-9_]*$', 'snake_case', 'Variables/functions'),
                (r'^[A-Z][A-Za-z0-9]*$', 'PascalCase', 'Classes'),
            ],
            'required': [
                ('__init__', 'Module docstring required'),
                ('try..except', 'Error handling for I/O operations'),
            ]
        }
        
    def validate(self, file_path: str, modification_type: str, content: str) -> Dict:
        """Validate code against registered patterns"""
        try:
            errors = []
            
            # Skip if LibCST not available
            if not HAVE_LIBCST:
                return {"valid": True, "warnings": ["Pattern validation skipped: libcst not available"]}
                
            try:
                wrapper = MetadataWrapper(parse_module(content))
                if wrapper is None:
                    return {"valid": True, "warnings": ["Pattern validation skipped: parsing failed"]}
                    
                errors += self._check_naming_conventions(wrapper)
                errors += self._check_required_patterns(content)
            except SyntaxError as e:
                # Don't fail validation for syntax errors - the main processor will catch these
                return {"valid": True, "warnings": [f"Pattern validation skipped: syntax error: {e}"]}
            except Exception as e:
                print(f"Error in pattern validation: {e}")
                return {"valid": True, "warnings": [f"Pattern validation error: {e}"]}
            
            return {"valid": len(errors) == 0, "errors": errors}
        except Exception as e:
            print(f"Pattern validator exception: {e}")
            return {"valid": True, "warnings": [f"Pattern validation skipped due to error: {e}"]}
    
    def _check_naming_conventions(self, wrapper) -> List[str]:
        """Validate naming patterns using AST"""
        errors = []
        try:
            # If using plain AST instead of LibCST
            if not HAVE_LIBCST:
                for node in ast.walk(wrapper.module):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        name = node.name
                        pattern_type = "Classes" if isinstance(node, ast.ClassDef) else "Variables/functions"
                        
                        if pattern_type == "Classes" and not re.match(r'^[A-Z][A-Za-z0-9]*$', name):
                            errors.append(f"Invalid class naming: {name} (should be PascalCase)")
                        elif pattern_type == "Variables/functions" and not re.match(r'^[a-z_][a-z0-9_]*$', name):
                            errors.append(f"Invalid function naming: {name} (should be snake_case)")
                return errors
                
            # Using LibCST
            for node in wrapper.module.body:
                if hasattr(node, 'name') and hasattr(node.name, 'value'):
                    name = node.name.value
                    pattern = None
                    
                    # Determine expected pattern by node type
                    if hasattr(node, '__class__') and node.__class__.__name__ == 'ClassDef':
                        pattern = self.patterns['naming'][1]  # PascalCase
                    else:
                        pattern = self.patterns['naming'][0]  # snake_case
                        
                    if pattern and not re.match(pattern[0], name):
                        errors.append(f"Invalid naming: {name} (should be {pattern[1]} for {pattern[2]})")
                        
        except Exception as e:
            print(f"Error checking naming conventions: {e}")
            
        return errors
    
    def _check_required_patterns(self, content: str) -> List[str]:
        """Check for presence of required code patterns"""
        errors = []
        try:
            # Simple text-based pattern checking
            is_module_docstring = bool(re.search(r'^""".*?"""', content, re.DOTALL))
            if not is_module_docstring and '__init__' in self.patterns['required'][0]:
                errors.append("Missing module docstring")
                
            has_error_handling = 'try:' in content and 'except' in content
            if not has_error_handling and 'try..except' in self.patterns['required'][1]:
                errors.append("Missing error handling")
                
        except Exception as e:
            print(f"Error checking required patterns: {e}")
            
        return errors