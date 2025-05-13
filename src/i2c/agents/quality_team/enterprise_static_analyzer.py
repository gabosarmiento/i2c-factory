# src/i2c/agents/quality_team/enterprise_static_analyzer.py
# Extension of the StaticAnalysisAgent that adds enterprise-grade quality gates

from pathlib import Path
import tempfile
import os
from typing import Dict, List, Any, Optional

# Import CLI for logging
try:
    from i2c.cli.controller import canvas
except ImportError:
    class FallbackCanvas: # Basic fallback logger
        def warning(self, msg): print(f"[WARN_ESA_AGENT] {msg}")
        def error(self, msg): print(f"[ERROR_ESA_AGENT] {msg}")
        def info(self, msg): print(f"[INFO_ESA_AGENT] {msg}")
        def success(self, msg): print(f"[SUCCESS_ESA_AGENT] {msg}")
    canvas = FallbackCanvas()

# Import tools and utilities
from i2c.agents.quality_team.utils.language_detector import LanguageDetector
from i2c.agents.quality_team.hooks.validation_tool_hook import validation_tool_hook

# Import all tools
from i2c.agents.quality_team.tools.tool_utils import (
    run_flake8, run_black, run_mypy, run_pytest, run_bandit,
    run_eslint, run_tsc, run_govet, run_checkstyle
)

class EnterpriseStaticAnalyzer:
    """
    Enhanced static analyzer that runs enterprise-grade quality gates 
    for various programming languages.
    """
    
    def __init__(self):
        """Initialize the enterprise static analyzer."""
        canvas.info("🏢 [EnterpriseStaticAnalyzer] Initialized.")
        
        # Register tools with validation hook
        self._register_tools()
    
    def _register_tools(self):
        """Register all validation tools with the hook."""
        # The hook is applied at the module level for the imported tools,
        # so we don't need to do anything here.
        pass
    
    def _create_temp_file(self, content: str, suffix: str = '.py') -> Path:
        """
        Create a temporary file with the given content.
        
        Args:
            content: The file content
            suffix: The file extension
            
        Returns:
            Path to the temporary file
        """
        fd, path = tempfile.mkstemp(suffix=suffix)
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(content)
            return Path(path)
        except Exception as e:
            canvas.error(f"[EnterpriseStaticAnalyzer] Error creating temp file: {e}")
            os.close(fd)
            os.unlink(path)
            raise
    
    def analyze_files(self, modified_files: Dict[str, str], quality_gates: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run enterprise-grade quality gates on the modified files.
        
        Args:
            modified_files: Dictionary mapping file paths to content
            quality_gates: Optional list of specific quality gates to run
            
        Returns:
            Dict with analysis results per file
        """
        canvas.info(f"🤖 [EnterpriseStaticAnalyzer] Analyzing {len(modified_files)} files...")
        
        if not modified_files:
            canvas.warning("[EnterpriseStaticAnalyzer] No files to analyze. Skipping.")
            return {
                "passed": True,
                "files_analyzed": 0,
                "files_with_issues": [],
                "issues": {},
                "summary": {
                    "total_issues": 0,
                    "quality_gates_run": 0
                }
            }
        
        temp_files = {}
        results = {
            "passed": True,
            "files_analyzed": len(modified_files),
            "files_with_issues": [],
            "issues": {},
            "summary": {
                "total_issues": 0,
                "quality_gates_run": 0,
                "quality_gates_failed": 0
            }
        }
        
        try:
            # Create temporary files for analysis
            for file_path, content in modified_files.items():
                suffix = Path(file_path).suffix
                temp_files[file_path] = self._create_temp_file(content, suffix)
            
            # Analyze each file
            for file_path, temp_file in temp_files.items():
                file_results = self._analyze_file(file_path, temp_file, quality_gates)
                
                # Store the results
                results["issues"][file_path] = file_results
                
                # Update summary
                results["summary"]["quality_gates_run"] += len(file_results)
                
                # Check if any gates failed
                file_passed = True
                issue_count = 0
                
                for gate, gate_result in file_results.items():
                    if not gate_result.get("passed", False):
                        file_passed = False
                        results["summary"]["quality_gates_failed"] += 1
                    
                    # Count issues
                    issue_count += len(gate_result.get("issues", []))
                
                # Update file status
                if not file_passed:
                    results["files_with_issues"].append(file_path)
                    results["passed"] = False
                
                # Update total issues
                results["summary"]["total_issues"] += issue_count
            
            canvas.success(f"[EnterpriseStaticAnalyzer] Analysis completed for {len(modified_files)} files.")
            canvas.info(f"[EnterpriseStaticAnalyzer] Found {results['summary']['total_issues']} issues in {len(results['files_with_issues'])} files.")
            
            return results
            
        finally:
            # Clean up temporary files
            for temp_file in temp_files.values():
                try:
                    temp_file.unlink()
                except Exception as e:
                    canvas.warning(f"[EnterpriseStaticAnalyzer] Error cleaning up temp file: {e}")
    
    def _analyze_file(self, file_path: str, temp_file: Path, quality_gates: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analyze a single file with appropriate quality gates.
        
        Args:
            file_path: Original file path
            temp_file: Path to temporary file with content
            quality_gates: Optional list of specific quality gates to run
            
        Returns:
            Dict with analysis results for the file
        """
        results = {}
        language = LanguageDetector.detect_language(file_path)
        canvas.info(f"[EnterpriseStaticAnalyzer] Analyzing file: {file_path} (language: {language})")
        
        # Get appropriate quality gates based on language
        if not quality_gates:
            quality_gates = LanguageDetector.get_quality_gates(file_path)
        else:
            # Filter quality gates to only include those appropriate for this file type
            language_gates = LanguageDetector.get_quality_gates(file_path)
            if language_gates:
                # Only run gates that are both requested AND appropriate for this file type
                quality_gates = [gate for gate in quality_gates if gate in language_gates]
        
        if not quality_gates:
            canvas.warning(f"[EnterpriseStaticAnalyzer] No quality gates defined for language: {language}")
            return {}
        
        # Run each quality gate
        for gate in quality_gates:
            result = self._run_quality_gate(gate, str(temp_file))
            if result:
                results[gate] = result
        
        return results
    
    def _run_quality_gate(self, gate: str, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Run a specific quality gate on a file.
        
        Args:
            gate: Quality gate identifier
            file_path: Path to the file
            
        Returns:
            Dict with quality gate results or None if gate not supported
        """
        try:
            canvas.info(f"[EnterpriseStaticAnalyzer] Running quality gate: {gate} on {file_path}")
            
            # Run the appropriate tool based on gate
            if gate == 'flake8':
                return validation_tool_hook("run_flake8", run_flake8, {"file_path": file_path})
            elif gate == 'black':
                return validation_tool_hook("run_black", run_black, {"file_path": file_path, "check_only": True})
            elif gate == 'mypy':
                return validation_tool_hook("run_mypy", run_mypy, {"file_path": file_path})
            elif gate == 'pytest':
                return validation_tool_hook("run_pytest", run_pytest, {"file_path": file_path})
            elif gate == 'bandit':
                return validation_tool_hook("run_bandit", run_bandit, {"file_path": file_path})
            elif gate == 'eslint':
                return validation_tool_hook("run_eslint", run_eslint, {"file_path": file_path})
            elif gate == 'tsc':
                return validation_tool_hook("run_tsc", run_tsc, {"file_path": file_path})
            elif gate == 'govet':
                return validation_tool_hook("run_govet", run_govet, {"file_path": file_path})
            elif gate == 'checkstyle':
                return validation_tool_hook("run_checkstyle", run_checkstyle, {"file_path": file_path})
            # Add more gates as needed
            
            canvas.warning(f"[EnterpriseStaticAnalyzer] Quality gate not implemented: {gate}")
            return None
            
        except Exception as e:
            canvas.error(f"[EnterpriseStaticAnalyzer] Error running quality gate {gate}: {e}")
            return {
                "passed": False,
                "issues": [f"Error running quality gate {gate}: {str(e)}"],
                "command": gate,
                "exit_code": -1
            }

# Instantiate the analyzer globally for easy import
enterprise_static_analyzer = EnterpriseStaticAnalyzer()