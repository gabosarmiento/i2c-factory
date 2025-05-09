# src/i2c/tools/neurosymbolic/validators/dependency_validator.py
from typing import Dict, List
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
        self._build_dependency_maps()
        
        return {
            "valid": True,
            "errors": self._check_circular_deps(file_path) 
                    + self._check_unused_imports(file_path)
                    + self._check_missing_references(file_path)
        }
    
    def _build_dependency_maps(self):
        """Build import relationship maps from graph"""
        for source, edges in self.graph.edges.items():
            for edge in edges:
                self._import_map[source].add(edge['target'])
                self._reverse_deps[edge['target']].add(source)
    
    def _check_circular_deps(self, file_path: str) -> List[str]:
        """Detect circular dependencies using Tarjan's algorithm"""
        visited = set()
        stack = []
        index = {}
        lowlink = {}
        cycles = []
        
        def strongconnect(node):
            nonlocal index, lowlink, stack
            index[node] = len(index)
            lowlink[node] = index[node]
            stack.append(node)
            
            for neighbor in self._import_map.get(node, []):
                if neighbor not in index:
                    strongconnect(neighbor)
                    lowlink[node] = min(lowlink[node], lowlink[neighbor])
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
        
        strongconnect(file_path)
        return [f"Circular dependency: {' → '.join(cycle)}" for cycle in cycles]

    def _check_unused_imports(self, file_path: str) -> List[str]:
        """Identify unused imports using AST analysis"""
        # Implementation requires AST analysis of actual code content
        return []  # Placeholder

    def _check_missing_references(self, file_path: str) -> List[str]:
        """Verify all imported references exist in target files"""
        errors = []
        for edge in self.graph.edges.get(file_path, []):
            target_defs = self.graph.nodes[edge['target']]['definitions']
            if edge['name'] not in target_defs:
                errors.append(f"Missing reference: {edge['name']} in {edge['target']}")
        return errors