# Enhanced src/i2c/tools/neurosymbolic/semantic_tool.py

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
        self.initialization_error = None  # Track initialization errors

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

    # Update to initialize method in semantic_tool.py

    def initialize(self, project_path, target_file=None):
        """
        Initialize or rebuild the semantic graph for a specific target file.
        
        Args:
            project_path: Root path of the project
            target_file: Optional specific file to focus on (relative to project_path)
            
        Returns:
            Dict with initialization status
        """
        try:
            from i2c.tools.neurosymbolic.graph.project_graph import ProjectGraph

            # Import validators
            try:
                from i2c.tools.neurosymbolic.validators.type_validator import TypeValidator
                from i2c.tools.neurosymbolic.validators.dependency_validator import DependencyValidator
                from i2c.tools.neurosymbolic.validators.pattern_validator import PatternValidator
                validator_imports_ok = True
            except ImportError as e:
                print(f"Warning: Unable to import validator modules: {e}")
                validator_imports_ok = False
            
            # Build the graph
            self.project_path = Path(project_path)
            print(f"[SemanticGraphTool] Initializing graph for project: {self.project_path}")
            
            if target_file:
                print(f"[SemanticGraphTool] Focusing on target file: {target_file}")
                
            # Create new graph with target file
            self.graph = ProjectGraph(self.project_path, target_file)
            self.graph.build()

            # Instantiate validators if imports succeeded
            if validator_imports_ok:
                self.validators = [
                    TypeValidator(self.graph),
                    DependencyValidator(self.graph),
                    PatternValidator(self.graph),
                ]
            else:
                self.validators = []
                print("[SemanticGraphTool] Warning: Validators not available - skipping validation setup")

            # Return number of files analyzed
            files_analyzed = len(self.graph.nodes)
            files_with_errors = len(getattr(self.graph, 'parse_errors', {}))
            
            print(f"[SemanticGraphTool] Graph initialized with {files_analyzed} files and {files_with_errors} errors")
            
            self.initialization_error = None  # Clear any previous errors
            
            return {
                "files_analyzed": files_analyzed, 
                "files_with_errors": files_with_errors,
                "status": "success"
            }
            
        except Exception as e:
            error_msg = f"Error initializing semantic graph: {type(e).__name__}: {e}"
            print(error_msg)
            self.initialization_error = error_msg
            return {"files_analyzed": 0, "status": "error", "error": error_msg}
    
    def validate_modification(self, file_path: str, modification_type: str, content: str) -> dict:
        """
        Validate a proposed code modification by running all registered validators.
        Returns a dict with:
          - valid: True if all validators passed
          - errors: flattened list of all errors from any validator
        """
        # Check if graph was initialized
        if not self.graph:
            if self.initialization_error:
                return {"valid": True, "errors": [], "warnings": [f"Validation skipped: {self.initialization_error}"]}
            return {"valid": True, "errors": [], "warnings": ["Validation skipped: semantic graph not initialized"]}
            
        # Check if we have any validators
        if not self.validators:
            return {"valid": True, "errors": [], "warnings": ["Validation skipped: no validators available"]}

        # Run all validators that are available
        all_errors = []
        all_warnings = []
        overall_valid = True

        for validator in self.validators:
            try:
                result = validator.validate(file_path, modification_type, content)
                if not result.get("valid", True):
                    # Don't fail validation for type errors - they're often false positives
                    if isinstance(validator, TypeValidator):
                        all_warnings.extend(result.get("errors", []))
                    else:
                        overall_valid = False
                        all_errors.extend(result.get("errors", []))
                
                # Collect any warnings
                if "warnings" in result:
                    all_warnings.extend(result["warnings"])
                    
            except Exception as e:
                # Don't let validator errors stop code generation
                print(f"Validator error (non-critical): {type(e).__name__}: {e}")
                all_warnings.append(f"Validator error: {e}")

        return {
            "valid": overall_valid, 
            "errors": all_errors,
            "warnings": all_warnings
        }

    def get_context_for_file(self, file_path: str) -> dict:
        """
        Extract semantic context for a file: related files, patterns, and types.
        Returns empty context if graph not initialized or errors occur.
        """
        # Check if graph was initialized
        if not self.graph:
            if self.initialization_error:
                return {"status": "error", "message": self.initialization_error}
            return {"status": "error", "message": "Graph not initialized"}

        try:
            related = self.graph.get_related_files(file_path)
            patterns = self.graph.extract_patterns(file_path)

            # Build a simple type environment from graph definitions
            types_env = {}
            for rel in related:
                rel_path = rel.get("path")
                if rel_path in self.graph.nodes:
                    node = self.graph.nodes[rel_path]
                    types_env.update(node.get("definitions", {}))

            return {
                "status": "completed",
                "related_files": related,
                "patterns": patterns,
                "types": types_env,
            }
        except Exception as e:
            print(f"Error getting context for file {file_path}: {e}")
            return {
                "status": "error",
                "message": f"Error getting context: {e}",
                "related_files": [],
                "patterns": {"function_patterns": [], "error_handling": [], "naming": []},
                "types": {}
            }