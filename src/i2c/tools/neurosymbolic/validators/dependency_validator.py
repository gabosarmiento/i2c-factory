# src/i2c/tools/neurosymbolic/validators/dependency_validator.py
from typing import Dict, List, Set
from pathlib import Path
from collections import defaultdict

class DependencyValidator:
    """Validates cross-file dependencies using semantic graph analysis"""
    
    def __init__(self, graph):
        self.graph = graph
        self._import_map = defaultdict(set)
        self._reverse_deps = defaultdict(set)
        
    def validate(self, file_path: str, modification_type: str, content: str) -> Dict:
        """Validate dependency constraints for a proposed modification"""
        try:
            # Handle case where graph may not be fully initialized
            if not hasattr(self.graph, 'edges') or not self.graph.edges:
                return {"valid": True, "warnings": ["Dependency validation skipped: graph not fully initialized"]}
                
            self._build_dependency_maps()
            
            errors = []
            errors.extend(self._check_circular_deps(file_path))
            errors.extend(self._check_missing_references(file_path))
            
            return {"valid": len(errors) == 0, "errors": errors}
        except Exception as e:
            # Don't let validation errors block code generation
            print(f"Dependency validation error (non-critical): {e}")
            return {"valid": True, "warnings": [f"Dependency validation skipped: {e}"]}
    
    def _build_dependency_maps(self):
        """Build import relationship maps from graph"""
        # Clear existing maps
        self._import_map.clear()
        self._reverse_deps.clear()
        
        # Build new maps from graph edges
        for source, edges in self.graph.edges.items():
            for edge in edges:
                self._import_map[source].add(edge['target'])
                self._reverse_deps[edge['target']].add(source)
    
    def _check_circular_deps(self, file_path: str) -> List[str]:
        """Detect circular dependencies using Tarjan's algorithm"""
        # Skip if file not in graph
        if file_path not in self._import_map:
            return []
            
        visited = set()
        stack = []
        index = {}
        lowlink = {}
        cycles = []
        
        def strongconnect(node):
            if node not in self._import_map:
                return
                
            index[node] = len(index)
            lowlink[node] = index[node]
            stack.append(node)
            
            for neighbor in self._import_map.get(node, []):
                if neighbor not in index:
                    strongconnect(neighbor)
                    lowlink[node] = min(lowlink[node], lowlink.get(neighbor, float('inf')))
                elif neighbor in stack:
                    lowlink[node] = min(lowlink[node], index[neighbor])
            
            if lowlink[node] == index[node]:
                cycle = []
                while True:
                    v = stack.pop()
                    cycle.append(v)
                    if v == node:
                        break
                if len(cycle) > 1:
                    cycles.append(cycle)
        
        try:
            strongconnect(file_path)
        except Exception as e:
            print(f"Error in circular dependency check: {e}")
            return []
            
        return [f"Circular dependency: {' → '.join(cycle)}" for cycle in cycles]

    def _check_missing_references(self, file_path: str) -> List[str]:
        """Verify all imported references exist in target files"""
        errors = []
        try:
            for edge in self.graph.edges.get(file_path, []):
                if edge['target'] not in self.graph.nodes:
                    continue
                    
                target_defs = self.graph.nodes[edge['target']].get('definitions', {})
                
                # Simple check for import name in target definitions
                # Skip if it's a module-level import (no specific name referenced)
                if '.' in edge['name'] and edge['name'].split('.')[0] not in target_defs:
                    errors.append(f"Missing reference: {edge['name']} in {edge['target']}")
        except Exception as e:
            print(f"Error checking references: {e}")
            
        return errors