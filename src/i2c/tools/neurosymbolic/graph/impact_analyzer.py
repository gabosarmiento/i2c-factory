# src/i2c/tools/neurosymbolic/graph/impact_analyzer.py
from typing import Dict, List, Set
from collections import deque

def analyze_impact(graph, file_path: str, change_type: str) -> Dict[str, List[str]]:
    """Analyze potential impact of code modifications using BFS traversal"""
    visited: Set[str] = set()
    queue = deque([file_path])
    impact = {
        'direct_dependents': [],
        'transitive_dependents': [],
        'breaking_changes': []
    }
    
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
            
        visited.add(current)
        
        # Get all files that import this file
        for importer in graph.edges:
            for edge in graph.edges[importer]:
                if edge['target'] == current and importer not in impact['direct_dependents']:
                    impact['direct_dependents'].append(importer)
                    queue.append(importer)
        
        # Check for API contract changes
        if change_type == 'api_modification':
            impact['breaking_changes'] += _detect_breaking_changes(graph, current)
            
    impact['transitive_dependents'] = list(visited - set([file_path]))
    return impact

def _detect_breaking_changes(graph, file_path: str) -> List[str]:
    """Identify potential breaking API changes"""
    breaking = []
    node = graph.nodes[file_path]
    
    for def_name, def_info in node['definitions'].items():
        if def_info['type'] == 'function' and 'parameters' in def_info:
            original_params = set(def_info['parameters'])
            # Compare with previous version
            # Implementation requires version tracking
            breaking.append(f"Modified signature: {def_name}")
            
    return breaking