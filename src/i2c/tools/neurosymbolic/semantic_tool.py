# src/i2c/tools/neurosymbolic/semantic_tool.py

import os
import types
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from agno.tools import Function, Toolkit

class SemanticGraphTool(Toolkit):
    """Agno tool for semantic graph analysis and validation"""

    def __init__(self, project_path=None):
        self.project_path = Path(project_path) if project_path else None
        self.graph = None
        self.validators = []

        # Create Functions instead of plain function objects
        functions = {
            "initialize": Function(
                name="initialize",
                entrypoint=self.initialize,
                description="Initialize the semantic graph for a project"
            ),
            "validate_modification": Function(
                name="validate_modification",
                entrypoint=self.validate_modification,
                description="Validate a code modification against semantic rules"
            ),
            "get_context_for_file": Function(
                name="get_context_for_file",
                entrypoint=self.get_context_for_file,
                description="Get semantic context for a specific file"
            )
        }

        # Call Toolkit's __init__ with the created functions
        super().__init__(
            name="SemanticGraphTool",
            tools=[]  # Empty because we're setting functions directly
        )
        
        # Set our functions dict
        self.functions = functions
        
        print("Semantic graph tool initialized successfully")

    def initialize(self, project_path):
        """Initialize or rebuild the semantic graph and report how many .py files were analyzed."""
        from i2c.tools.neurosymbolic.graph.project_graph import ProjectGraph
        from i2c.tools.neurosymbolic.validators.type_validator import TypeValidator
        from i2c.tools.neurosymbolic.validators.dependency_validator import DependencyValidator
        from i2c.tools.neurosymbolic.validators.pattern_validator import PatternValidator

        # Build the graph
        self.project_path = Path(project_path)
        self.graph = ProjectGraph(self.project_path)
        self.graph.build()

        # Instantiate validators
        self.validators = [
            TypeValidator(self.graph),
            DependencyValidator(self.graph),
            PatternValidator(self.graph),
        ]

        # Return number of files analyzed (for smoke test)
        return {"files_analyzed": len(self.graph.nodes)}

    def validate_modification(self, file_path: str, modification_type: str, content: str) -> dict:
        """
        Validate a proposed code modification by running all registered validators.
        Returns a dict with:
          - valid: True if all validators passed
          - errors: flattened list of all errors from any validator
        """
        if not self.graph:
            return {"valid": False, "errors": ["Semantic graph not initialized"]}

        all_errors = []
        overall_valid = True

        for validator in self.validators:
            result = validator.validate(file_path, modification_type, content)
            if not result.get("valid", True):
                overall_valid = False
                all_errors.extend(result.get("errors", []))

        return {"valid": overall_valid, "errors": all_errors}

    def get_context_for_file(self, file_path: str) -> dict:
        """
        Extract semantic context for a file: related files, patterns, and types.
        """
        if not self.graph:
            return {"status": "error", "message": "Graph not initialized"}

        related = self.graph.get_related_files(file_path)
        patterns = self.graph.extract_patterns(file_path)

        # Build a simple type environment from graph definitions
        types_env = {}
        for rel in related:
            node = self.graph.nodes.get(rel["path"])
            if node:
                types_env.update(node.get("definitions", {}))

        return {
            "status": "completed",
            "related_files": related,
            "patterns": patterns,
            "types": types_env,
        }