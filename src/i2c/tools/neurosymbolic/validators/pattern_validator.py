# src/i2c/tools/neurosymbolic/validators/pattern_validator.py
import re
from typing import Dict, List
from libcst import parse_module, MetadataWrapper

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
        errors = []
        wrapper = MetadataWrapper(parse_module(content))
        
        errors += self._check_naming_conventions(wrapper)
        errors += self._check_required_patterns(content)
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    def _check_naming_conventions(self, wrapper: MetadataWrapper) -> List[str]:
        """Validate naming patterns using LibCST"""
        errors = []
        for node in wrapper.module.body:
            if hasattr(node, 'name'):
                name = node.name.value
                pattern = next((p for p in self.patterns['naming'] 
                              if re.match(p[0], name)), None)
                if not pattern:
                    errors.append(f"Invalid naming: {name} ({node.__class__.__name__})")
        return errors
    
    def _check_required_patterns(self, content: str) -> List[str]:
        """Check for presence of required code patterns"""
        errors = []
        for pattern, message in self.patterns['required']:
            if not re.search(pattern, content, re.DOTALL):
                errors.append(f"Missing required pattern: {message}")
        return errors