# src/i2c/tools/neurosymbolic/semantic_tool.py

from agno.tools.base import BaseTool
from pathlib import Path

class SemanticGraphTool(BaseTool):
    """Agno tool for semantic graph analysis and validation"""
    
    def __init__(self, project_path=None):
        self.project_path = project_path
        self.graph = None
        self.validators = []
        
    def initialize(self, project_path):
        """Initialize or update the semantic graph"""
        from i2c.tools.neurosymbolic.graph.project_graph import ProjectGraph
        
        self.project_path = Path(project_path)
        self.graph = ProjectGraph(self.project_path)
        self.graph.build()
        
        # Initialize validators
        from i2c.tools.neurosymbolic.validators.type_validator import TypeValidator
        from i2c.tools.neurosymbolic.validators.dependency_validator import DependencyValidator
        from i2c.tools.neurosymbolic.validators.pattern_validator import PatternValidator
        
        self.validators = [
            TypeValidator(self.graph),
            DependencyValidator(self.graph),
            PatternValidator(self.graph)
        ]
        
        return {"status": "initialized", "files_analyzed": len(self.graph.nodes)}
        
    def validate_modification(self, file_path, modification_type, content):
        """Validate a proposed code modification"""
        if not self.graph:
            return {"status": "error", "message": "Graph not initialized"}
            
        # Run validators
        validation_results = []
        for validator in self.validators:
            result = validator.validate(file_path, modification_type, content)
            validation_results.append(result)
            
        # Analyze impact
        from i2c.tools.neurosymbolic.graph.impact_analyzer import analyze_impact
        impact = analyze_impact(self.graph, file_path, modification_type)
            
        return {
            "status": "completed",
            "results": validation_results,
            "impact": impact
        }
        
    def get_context_for_file(self, file_path):
        """Extract semantic context for a file"""
        if not self.graph:
            return {"status": "error", "message": "Graph not initialized"}
            
        # Get related files and their relationships
        related_files = self.graph.get_related_files(file_path)
        
        # Extract patterns
        patterns = self.graph.extract_patterns(file_path)
        
        # Get type information
        types = self.graph.get_type_environment(file_path)
        
        return {
            "status": "completed",
            "related_files": related_files,
            "patterns": patterns,
            "types": types
        }