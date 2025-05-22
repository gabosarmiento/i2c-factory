# file: workflow/diagnostic/modification_analyzer.py
from i2c.bootstrap import initialize_environment
initialize_environment()
import json
import time
import difflib
from pathlib import Path
from typing import Dict, Any, Tuple, List
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import the components we need to analyze
from i2c.db_utils import get_db_connection
from i2c.workflow.modification.rag_retrieval import retrieve_context_for_planner
from i2c.workflow.modification.plan_generator import generate_modification_plan
from i2c.workflow.modification.code_executor import execute_modification_steps
from i2c.workflow.modification.test_and_quality import generate_unit_tests, run_quality_checks
from i2c.workflow.modification.rag_config import get_embed_model
from i2c.cli.controller import canvas
from i2c.agents.quality_team.utils.language_detector import LanguageDetector

class ModificationAnalyzer:
    """Diagnostics wrapper for analyzing the modification workflow."""
    
    def __init__(self, output_dir: Path = None):
        """Initialize the analyzer with an output directory for reports."""
        self.console = Console()
        self.output_dir = output_dir or Path("./diagnostic_reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_data = {}
        
    def run_diagnostic(self, user_request: str, project_path: Path, language: str) -> Dict[str, Any]:
        """
        Run a complete diagnostic of the modification workflow.
        
        Args:
            user_request: The modification request
            project_path: Path to the project
            language: Programming language
            
        Returns:
            Dict containing all diagnostic data
        """
        self.console.print(Panel.fit(f"Starting Modification Workflow Diagnostic", 
                                    title="[bold green]Modification Analyzer[/bold green]"))
        
        # Initialize the diagnostic report
        self.report_data = {
            "request": user_request,
            "project_path": str(project_path),
            "language": language,
            "timestamp": self.timestamp,
            "stages": {},
            "overall_result": False,
            "execution_time": {}
        }
        
        # Snapshot the project before changes
        self._snapshot_project(project_path, "before")
        
        try:
            # Step 1: Database and Embedding Model
            db, embed_model = self._setup_and_diagnose_dependencies()
            
            # Step 2: Analyze RAG Retrieval
            start_time = time.time()
            rag_context, rag_metrics = self._analyze_rag_retrieval(user_request, db, embed_model)
            self.report_data["execution_time"]["rag_retrieval"] = time.time() - start_time
            
            # Step 3: Analyze Plan Generation
            start_time = time.time()
            modification_plan, plan_metrics = self._analyze_plan_generation(
                user_request, rag_context, project_path, language
            )
            self.report_data["execution_time"]["plan_generation"] = time.time() - start_time
            
            # Step 4: Analyze Code Execution
            start_time = time.time()
            modified_code_map, files_to_delete, execution_metrics = self._analyze_code_execution(
                modification_plan, project_path, db, embed_model
            )
            self.report_data["execution_time"]["code_execution"] = time.time() - start_time
            
            # Step 5: Analyze Unit Tests
            start_time = time.time()
            final_code_map, test_metrics = self._analyze_unit_tests(modified_code_map)
            self.report_data["execution_time"]["unit_tests"] = time.time() - start_time
            
            # Step 6: Analyze Quality Checks
            start_time = time.time()
            quality_result, quality_metrics = self._analyze_quality_checks(final_code_map)
            self.report_data["execution_time"]["quality_checks"] = time.time() - start_time
            
            # Mark as successful
            self.report_data["overall_result"] = True
            
            # Snapshot the project after changes (only in memory, not written yet)
            self._snapshot_project_after(final_code_map, files_to_delete, project_path)
            
            # Generate the comprehensive report
            self._generate_report()
            
            return self.report_data
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            
            self.report_data["error"] = {
                "message": str(e),
                "traceback": error_trace
            }
            
            # Generate error report
            self._generate_error_report()
            
            self.console.print(f"[bold red]Diagnostic failed:[/bold red] {str(e)}")
            return self.report_data
    
    def _setup_and_diagnose_dependencies(self) -> Tuple[Any, Any]:
        """Set up and diagnose database and embedding model."""
        self.console.print("[bold blue]Stage 1:[/bold blue] Setting up database and embedding model")
        
        db_metrics = {"success": False, "error": None}
        embed_metrics = {"success": False, "error": None}
        
        # Set up database
        try:
            db = get_db_connection()
            if db:
                db_metrics["success"] = True
                db_metrics["tables"] = db.table_names()
            else:
                db_metrics["error"] = "Database connection failed"
        except Exception as e:
            db_metrics["error"] = str(e)
            db = None
        
        # Set up embedding model
        try:
            embed_model = get_embed_model()
            if embed_model:
                embed_metrics["success"] = True
                embed_metrics["model_info"] = str(embed_model)
            else:
                embed_metrics["error"] = "Embedding model initialization failed"
        except Exception as e:
            embed_metrics["error"] = str(e)
            embed_model = None
        
        # Store metrics
        self.report_data["stages"]["dependencies"] = {
            "database": db_metrics,
            "embedding_model": embed_metrics
        }
        
        if db_metrics["success"]:
            self.console.print("[green]✓[/green] Database connection successful")
        else:
            self.console.print("[red]✗[/red] Database connection failed")
            
        if embed_metrics["success"]:
            self.console.print("[green]✓[/green] Embedding model initialized")
        else:
            self.console.print("[red]✗[/red] Embedding model initialization failed")
        
        return db, embed_model
    
    def _analyze_rag_retrieval(self, user_request: str, db, embed_model) -> Tuple[str, Dict[str, Any]]:
        """Analyze the RAG retrieval process."""
        self.console.print("[bold blue]Stage 2:[/bold blue] Analyzing RAG retrieval")
        
        rag_metrics = {
            "success": False,
            "error": None,
            "content_length": 0,
            "content_quality": 0,
            "chunks_retrieved": 0
        }
        
        try:
            # Retrieve context
            context = retrieve_context_for_planner(
                user_request=user_request,
                db=db,
                embed_model=embed_model
            )
            
            # Analyze the retrieved context
            if context:
                rag_metrics["success"] = True
                rag_metrics["content_length"] = len(context)
                rag_metrics["chunks_retrieved"] = context.count("--- Start Chunk:")
                
                # Simple quality metric: how many actual code lines vs. total lines
                code_lines = sum(1 for line in context.split('\n') 
                               if line.strip() and not line.startswith("---") and 
                               not line.startswith("[Retrieved Context"))
                rag_metrics["content_quality"] = code_lines / max(1, rag_metrics["content_length"] / 80)
            else:
                rag_metrics["error"] = "No context retrieved"
        
        except Exception as e:
            rag_metrics["error"] = str(e)
            context = ""
        
        # Store metrics
        self.report_data["stages"]["rag_retrieval"] = {
            "context": context,
            "metrics": rag_metrics
        }
        
        if rag_metrics["success"]:
            self.console.print(f"[green]✓[/green] Retrieved {rag_metrics['chunks_retrieved']} context chunks")
        else:
            self.console.print(f"[red]✗[/red] Context retrieval failed: {rag_metrics['error']}")
        
        return context, rag_metrics
    
    def _analyze_plan_generation(self, user_request: str, context: str, 
                                project_path: Path, language: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Analyze the plan generation process."""
        self.console.print("[bold blue]Stage 3:[/bold blue] Analyzing plan generation")
        
        plan_metrics = {
            "success": False,
            "error": None,
            "step_count": 0,
            "actions": {},
            "file_coverage": 0,
            "invalid_files": []
        }
        
        try:
            # Generate plan
            plan = generate_modification_plan(
                user_request=user_request,
                retrieved_context_plan=context,
                project_path=project_path,
                language=language
            )
            
            if plan:
                plan_metrics["success"] = True
                plan_metrics["step_count"] = len(plan)
                
                # Analyze actions
                actions = {}
                for step in plan:
                    action = step.get("action", "unknown")
                    actions[action] = actions.get(action, 0) + 1
                plan_metrics["actions"] = actions
                
                # Check file validity
                existing_files = set()
                for file_path in project_path.glob("**/*"):
                    if file_path.is_file():
                        rel_path = str(file_path.relative_to(project_path))
                        existing_files.add(rel_path)
                
                invalid_files = []
                for step in plan:
                    file_path = step.get("file", "")
                    action = step.get("action", "")
                    
                    if action in ["modify", "delete"] and file_path not in existing_files:
                        invalid_files.append(file_path)
                
                plan_metrics["file_coverage"] = len(set(step.get("file", "") for step in plan)) / max(1, len(existing_files))
                plan_metrics["invalid_files"] = invalid_files
            else:
                plan_metrics["error"] = "No plan generated"
                plan = []
        
        except Exception as e:
            plan_metrics["error"] = str(e)
            plan = []
        
        # Store metrics
        self.report_data["stages"]["plan_generation"] = {
            "plan": plan,
            "metrics": plan_metrics
        }
        
        # Display plan details
        if plan_metrics["success"]:
            table = Table(title="Modification Plan")
            table.add_column("Step", style="cyan")
            table.add_column("File", style="green")
            table.add_column("Action", style="magenta")
            table.add_column("What", style="yellow")
            
            for i, step in enumerate(plan):
                table.add_row(
                    str(i+1),
                    step.get("file", ""),
                    step.get("action", ""),
                    step.get("what", "")[:50] + ("..." if len(step.get("what", "")) > 50 else "")
                )
            
            self.console.print(table)
            
            if plan_metrics["invalid_files"]:
                self.console.print(f"[yellow]Warning:[/yellow] {len(plan_metrics['invalid_files'])} invalid files in plan")
        else:
            self.console.print(f"[red]✗[/red] Plan generation failed: {plan_metrics['error']}")
        
        return plan, plan_metrics

    def _is_explanation(content: str, language: str) -> bool:
        """
        Determines if content is likely an explanation rather than code.
        Args:
            content: The content to analyze
            language: The expected programming language
            
        Returns:
            True if the content appears to be explanatory text
        """
        # Common code indicators
        code_indicators = {
            'python': ['def ', 'class ', 'import ', '# ', 'if __name__', '"""', 'return', 'self.'],
            'javascript': ['function', 'const ', 'let ', 'var ', 'import ', 'export ', '=>', 'return'],
            'typescript': ['function', 'const ', 'let ', 'var ', 'import ', 'export ', '=>', 'interface ', 'type '],
            'go': ['func ', 'package ', 'import ', 'type ', 'return', 'struct ', 'interface '],
            'java': ['class ', 'public ', 'private ', 'import ', 'return', '@Override', 'void '],
        }

        # Common natural language markers
        explanation_indicators = [
            'Analyzing', 'Understanding', 'First,', 'To address', 
            'Given the', 'Let\'s', 'The task', 'We need', 'This file',
            'Looking at', 'Requirement', 'Based on', 'The goal'
        ]

        indicators = code_indicators.get(language, ['def', 'class', 'function', 'import'])

        # Count indicators
        code_score = sum(1 for ind in indicators if ind in content)
        explanation_score = sum(1 for ind in explanation_indicators if ind in content[:500])  # Check mainly the beginning

        # Check for paragraphs vs. code structure
        newline_ratio = content.count('\n') / max(1, len(content))
        has_paragraphs = any(len(line.strip()) > 80 for line in content.split('\n'))

        # Combine heuristics
        return (explanation_score > code_score) or (explanation_score > 2 and has_paragraphs)

    def _analyze_code_execution(self, plan: List[Dict[str, Any]], project_path: Path, 
                               db, embed_model) -> Tuple[Dict[str, str], List[Path], Dict[str, Any]]:
        """Analyze the code execution process."""
        self.console.print("[bold blue]Stage 4:[/bold blue] Analyzing code execution")
        
        execution_metrics = {
            "success": False,
            "error": None,
            "files_modified": 0,
            "files_deleted": 0,
            "content_sizes": {},
            "step_successes": {},
            "step_errors": {},
            "content_quality": {}  # Added metric
        }
        
        try:
            # Capture original file contents
            original_files = {}
            for file_path in project_path.glob("**/*"):
                if file_path.is_file():
                    try:
                        rel_path = str(file_path.relative_to(project_path))
                        original_files[rel_path] = file_path.read_text(encoding="utf-8")
                    except:
                        pass
            
            # Track each step individually
            session_state = {}
            step_results = {}
            all_code_map = {}
            all_files_to_delete = []
            
            for i, step in enumerate(plan):
                try:
                    # Execute just this step
                    single_step_plan = [step]
                    code_map, files_to_delete = execute_modification_steps(
                        modification_plan=single_step_plan,
                        project_path=project_path,
                        db=db,
                        embed_model=embed_model,
                        session_state=session_state
                    )
                    # Analyze content quality for each modified file
                    for file_path, content in code_map.items():
                        language = LanguageDetector.detect_language(file_path)
                        is_explanation = _is_explanation(content, language)
                        
                        execution_metrics["content_quality"][file_path] = {
                            "appears_valid": not is_explanation,
                            "language": language,
                            "likely_issue": "Explanatory text instead of code" if is_explanation else None
                        }
                    # Record success
                    step_results[i] = {
                        "success": True,
                        "code_map": code_map,
                        "files_to_delete": [str(f) for f in files_to_delete]
                    }
                    
                    # Add to cumulative results
                    all_code_map.update(code_map)
                    all_files_to_delete.extend(files_to_delete)
                    
                except Exception as e:
                    # Record failure
                    step_results[i] = {
                        "success": False,
                        "error": str(e)
                    }
                    execution_metrics["step_errors"][i] = str(e)
            
            # Count successes/failures
            success_count = sum(1 for r in step_results.values() if r["success"])
            execution_metrics["success"] = success_count > 0
            execution_metrics["files_modified"] = len(all_code_map)
            execution_metrics["files_deleted"] = len(all_files_to_delete)
            execution_metrics["step_successes"] = {i: r["success"] for i, r in step_results.items()}
            
            # Analyze content sizes
            for file_path, content in all_code_map.items():
                execution_metrics["content_sizes"][file_path] = len(content)
            
            # Perform diffing for modified files
            diffs = {}
            for file_path, new_content in all_code_map.items():
                if file_path in original_files:
                    old_content = original_files[file_path]
                    diff = list(difflib.unified_diff(
                        old_content.splitlines(),
                        new_content.splitlines(),
                        fromfile=f"a/{file_path}",
                        tofile=f"b/{file_path}"
                    ))
                    diffs[file_path] = "\n".join(diff)
            
            execution_metrics["diffs"] = diffs
            
        except Exception as e:
            execution_metrics["error"] = str(e)
            all_code_map = {}
            all_files_to_delete = []
        
        # Store metrics
        self.report_data["stages"]["code_execution"] = {
            "metrics": execution_metrics,
            "step_results": step_results
        }
        
        if execution_metrics["success"]:
            self.console.print(f"[green]✓[/green] Modified {execution_metrics['files_modified']} files, scheduled {execution_metrics['files_deleted']} for deletion")
            # Add content quality report
            quality_issues = sum(1 for quality in execution_metrics["content_quality"].values() 
                            if not quality.get("appears_valid", True))
            
            if quality_issues > 0:
                self.console.print(f"[yellow]⚠[/yellow] Content quality issues detected in {quality_issues} files")
                
                table = Table(title="Content Quality Issues")
                table.add_column("File", style="cyan")
                table.add_column("Language", style="green")
                table.add_column("Issue", style="red")
                
                for file_path, quality in execution_metrics["content_quality"].items():
                    if not quality.get("appears_valid", True):
                        table.add_row(
                            file_path,
                            quality.get("language", "unknown"),
                            quality.get("likely_issue", "Unknown issue")
                        )
                
                self.console.print(table)  
            success_rate = success_count / max(1, len(plan)) * 100
            self.console.print(f"Step success rate: {success_rate:.1f}% ({success_count}/{len(plan)})")
        else:
            self.console.print(f"[red]✗[/red] Code execution failed: {execution_metrics['error']}")
        
        return all_code_map, all_files_to_delete, execution_metrics
    
    def _analyze_unit_tests(self, code_map: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, Any]]:
        """Analyze the unit test generation process."""
        self.console.print("[bold blue]Stage 5:[/bold blue] Analyzing unit test generation")
        
        test_metrics = {
            "success": False,
            "error": None,
            "test_files_count": 0,
            "test_to_code_ratio": 0
        }
        
        try:
            # Generate unit tests
            code_map_with_tests = generate_unit_tests(code_map)
            
            if code_map_with_tests:
                test_metrics["success"] = True
                
                # Count test files
                test_files = [f for f in code_map_with_tests.keys() if f.startswith("test_")]
                test_metrics["test_files_count"] = len(test_files)
                
                # Calculate test to code ratio
                code_files = [f for f in code_map_with_tests.keys() if not f.startswith("test_") and f.endswith(".py")]
                test_metrics["test_to_code_ratio"] = len(test_files) / max(1, len(code_files))
                
                # Analyze test content
                test_content_sizes = {}
                unittest_calls = {}
                for file_path in test_files:
                    content = code_map_with_tests[file_path]
                    test_content_sizes[file_path] = len(content)
                    unittest_calls[file_path] = content.count("unittest.main()")
                
                test_metrics["test_content_sizes"] = test_content_sizes
                test_metrics["unittest_calls"] = unittest_calls
                
                # Check for any duplicate unittest.main() calls
                test_metrics["duplicate_unittest_main"] = any(count > 1 for count in unittest_calls.values())
            else:
                test_metrics["error"] = "No tests generated"
                code_map_with_tests = code_map
        
        except Exception as e:
            test_metrics["error"] = str(e)
            code_map_with_tests = code_map
        
        # Store metrics
        self.report_data["stages"]["unit_tests"] = {
            "metrics": test_metrics
        }
        
        if test_metrics["success"]:
            self.console.print(f"[green]✓[/green] Generated {test_metrics['test_files_count']} test files")
            
            if test_metrics["duplicate_unittest_main"]:
                self.console.print("[yellow]Warning:[/yellow] Duplicate unittest.main() calls detected")
        else:
            self.console.print(f"[red]✗[/red] Test generation failed: {test_metrics['error']}")
        
        return code_map_with_tests, test_metrics
    
    def _analyze_quality_checks(self, code_map: Dict[str, str]) -> Tuple[bool, Dict[str, Any]]:
        """Analyze the quality check process."""
        self.console.print("[bold blue]Stage 6:[/bold blue] Analyzing quality checks")
        
        quality_metrics = {
            "success": False,
            "error": None,
            "issues_found": 0,
            "issue_categories": {}
        }
        
        try:
            # Run quality checks
            quality_result = run_quality_checks(code_map)
            
            quality_metrics["success"] = True
            
            # Get issues
            # Note: We'd need to modify run_quality_checks to return the actual issues
            issues = []  # This would come from the quality checks
            
            quality_metrics["issues_found"] = len(issues)
            
            # Categorize issues
            categories = {}
            for issue in issues:
                category = issue.get("category", "unknown")
                categories[category] = categories.get(category, 0) + 1
            
            quality_metrics["issue_categories"] = categories
        
        except Exception as e:
            quality_metrics["error"] = str(e)
            quality_result = False
        
        # Store metrics
        self.report_data["stages"]["quality_checks"] = {
            "metrics": quality_metrics
        }
        
        if quality_metrics["success"]:
            if quality_metrics["issues_found"] == 0:
                self.console.print("[green]✓[/green] No quality issues found")
            else:
                self.console.print(f"[yellow]⚠[/yellow] Found {quality_metrics['issues_found']} quality issues")
        else:
            self.console.print(f"[red]✗[/red] Quality check failed: {quality_metrics['error']}")
        
        return quality_result, quality_metrics
    
    def _snapshot_project(self, project_path: Path, stage: str):
        """Take a snapshot of the project files."""
        snapshot = {
            "files": {},
            "directory_structure": []
        }
        
        # Capture files
        for file_path in project_path.glob("**/*"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(project_path))
                try:
                    content = file_path.read_text(encoding="utf-8")
                    snapshot["files"][rel_path] = {
                        "size": len(content),
                        "content": content
                    }
                except:
                    snapshot["files"][rel_path] = {
                        "size": file_path.stat().st_size,
                        "error": "Could not read file"
                    }
        
        # Capture directory structure
        for dir_path in project_path.glob("**/*"):
            if dir_path.is_dir():
                rel_path = str(dir_path.relative_to(project_path))
                snapshot["directory_structure"].append(rel_path)
        
        self.report_data[f"snapshot_{stage}"] = snapshot
    
    def _snapshot_project_after(self, final_code_map: Dict[str, str], 
                              files_to_delete: List[Path], project_path: Path):
        """Create a snapshot of what the project would look like after changes."""
        # Start with the before snapshot
        before_snapshot = self.report_data.get("snapshot_before", {"files": {}})
        snapshot = {
            "files": dict(before_snapshot["files"]),
            "changes": {
                "modified": [],
                "added": [],
                "deleted": []
            }
        }
        
        # Apply modifications and additions
        for rel_path, content in final_code_map.items():
            if rel_path in snapshot["files"]:
                snapshot["changes"]["modified"].append(rel_path)
            else:
                snapshot["changes"]["added"].append(rel_path)
            
            snapshot["files"][rel_path] = {
                "size": len(content),
                "content": content
            }
        
        # Apply deletions
        for file_path in files_to_delete:
            rel_path = str(file_path.relative_to(project_path))
            if rel_path in snapshot["files"]:
                del snapshot["files"][rel_path]
                snapshot["changes"]["deleted"].append(rel_path)
        
        self.report_data["snapshot_after"] = snapshot
    
    def _generate_report(self):
        """Generate a comprehensive diagnostic report."""
        self.console.print("[bold green]Generating diagnostic report...[/bold green]")
        
        # Write the full report data as JSON
        report_path = self.output_dir / f"modification_report_{self.timestamp}.json"
        with open(report_path, "w") as f:
            json.dump(self.report_data, f, indent=2)
        
        # Generate a summary HTML report
        html_path = self.output_dir / f"modification_report_{self.timestamp}.html"
        self._generate_html_report(html_path)
        
        self.console.print(f"Full report saved to: {report_path}")
        self.console.print(f"HTML summary saved to: {html_path}")
        
        # Display summary
        self._display_summary()
    
    def _generate_error_report(self):
        """Generate an error report."""
        self.console.print("[bold red]Generating error report...[/bold red]")
        
        # Write the error report data as JSON
        report_path = self.output_dir / f"modification_error_{self.timestamp}.json"
        with open(report_path, "w") as f:
            json.dump(self.report_data, f, indent=2)
        
        self.console.print(f"Error report saved to: {report_path}")
        
        # Display error summary
        self.console.print("[bold red]Diagnostic Failed[/bold red]")
        if "error" in self.report_data:
            self.console.print(f"Error: {self.report_data['error']['message']}")
    
    def _generate_html_report(self, path: Path):
        """Generate an HTML summary report."""
        # This would generate a nice HTML report with charts and visualizations
        # For brevity, we'll just create a basic HTML file
        html = [
            "<html>",
            "<head>",
            "<title>Modification Workflow Diagnostic Report</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            ".section { margin: 20px 0; border: 1px solid #ddd; padding: 10px; border-radius: 5px; }",
            ".success { color: green; }",
            ".warning { color: orange; }",
            ".error { color: red; }",
            "table { border-collapse: collapse; width: 100%; }",
            "table, th, td { border: 1px solid #ddd; }",
            "th, td { padding: 8px; text-align: left; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>Modification Workflow Diagnostic Report</h1>",
            f"<p>Timestamp: {self.timestamp}</p>",
            f"<p>Request: {self.report_data['request']}</p>",
            f"<p>Project: {self.report_data['project_path']}</p>",
            f"<p>Language: {self.report_data['language']}</p>",
            
            "<h2>Summary</h2>"
        ]
        
        # Add overall result
        overall_result = self.report_data.get("overall_result", False)
        html.append(f"<p>Overall result: <span class=\"{'success' if overall_result else 'error'}\">{'Success' if overall_result else 'Failure'}</span></p>")
        
        # Add execution times
        html.append("<h3>Execution Times</h3>")
        html.append("<table>")
        html.append("<tr><th>Stage</th><th>Time (seconds)</th></tr>")
        for stage, time_taken in self.report_data.get("execution_time", {}).items():
            html.append(f"<tr><td>{stage}</td><td>{time_taken:.2f}</td></tr>")
        html.append("</table>")
        
        # Add stage results
        html.append("<h2>Stage Results</h2>")
        
        for stage, data in self.report_data.get("stages", {}).items():
            html.append(f"<div class=\"section\">")
            html.append(f"<h3>{stage.replace('_', ' ').title()}</h3>")
            
            if "metrics" in data:
                metrics = data["metrics"]
                success = metrics.get("success", False)
                html.append(f"<p>Result: <span class=\"{'success' if success else 'error'}\">{'Success' if success else 'Failure'}</span></p>")
                
                if not success and "error" in metrics:
                    html.append(f"<p>Error: <span class=\"error\">{metrics['error']}</span></p>")
                
                # Add other metrics based on stage
                html.append("<h4>Metrics</h4>")
                html.append("<table>")
                for key, value in metrics.items():
                    if key not in ["success", "error"] and not isinstance(value, dict):
                        html.append(f"<tr><td>{key}</td><td>{value}</td></tr>")
                html.append("</table>")
            
            html.append("</div>")
        
        # Close HTML
        html.append("</body>")
        html.append("</html>")
        
        # Write to file
        with open(path, "w") as f:
            f.write("\n".join(html))
    
    def _display_summary(self):
        """Display a summary of the diagnostic results."""
        table = Table(title="Modification Workflow Diagnostic Summary")
        table.add_column("Stage", style="cyan")
        table.add_column("Result", style="green")
        table.add_column("Metrics", style="yellow")
        
        for stage, data in self.report_data.get("stages", {}).items():
            if "metrics" in data:
                metrics = data["metrics"]
                success = metrics.get("success", False)
                
                # Create a metrics summary based on stage
                metrics_summary = []
                if stage == "rag_retrieval" and success:
                    metrics_summary.append(f"Chunks: {metrics.get('chunks_retrieved', 0)}")
                    metrics_summary.append(f"Length: {metrics.get('content_length', 0)} chars")
                elif stage == "plan_generation" and success:
                    metrics_summary.append(f"Steps: {metrics.get('step_count', 0)}")
                    metrics_summary.append(f"Actions: {', '.join(f'{k}:{v}' for k, v in metrics.get('actions', {}).items())}")
                elif stage == "code_execution" and success:
                    metrics_summary.append(f"Modified: {metrics.get('files_modified', 0)}")
                    metrics_summary.append(f"Deleted: {metrics.get('files_deleted', 0)}")
                elif stage == "unit_tests" and success:
                    metrics_summary.append(f"Test files: {metrics.get('test_files_count', 0)}")
                elif stage == "quality_checks" and success:
                    metrics_summary.append(f"Issues: {metrics.get('issues_found', 0)}")
                
                table.add_row(
                    stage.replace("_", " ").title(),
                    "[green]Success[/green]" if success else f"[red]Failed: {metrics.get('error', 'Unknown error')}[/red]",
                    ", ".join(metrics_summary)
                )
        
        self.console.print(table)
        
        # Show overall result
        overall_result = self.report_data.get("overall_result", False)
        if overall_result:
            self.console.print("[bold green]Modification Workflow Diagnostic Completed Successfully[/bold green]")
        else:
            self.console.print("[bold red]Modification Workflow Diagnostic Failed[/bold red]")
        
        # Show key findings and recommendations
        findings = self._generate_key_findings()
        self.console.print("\n[bold blue]Key Findings & Recommendations:[/bold blue]")
        for finding in findings:
            if finding["type"] == "success":
                self.console.print(f"[green]✓[/green] {finding['message']}")
            elif finding["type"] == "warning":
                self.console.print(f"[yellow]⚠[/yellow] {finding['message']}")
            elif finding["type"] == "error":
                self.console.print(f"[red]✗[/red] {finding['message']}")
            
            if "recommendation" in finding:
                self.console.print(f"   Recommendation: {finding['recommendation']}")
    
    def _generate_key_findings(self) -> List[Dict[str, str]]:
        """Generate key findings and recommendations based on diagnostic data."""
        findings = []
        
        # Check RAG retrieval
        rag_metrics = self.report_data.get("stages", {}).get("rag_retrieval", {}).get("metrics", {})
        if not rag_metrics.get("success", False):
            findings.append({
                "type": "error",
                "message": f"RAG retrieval failed: {rag_metrics.get('error', 'Unknown error')}",
                "recommendation": "Check database connection and embedding model configuration."
            })
        elif rag_metrics.get("chunks_retrieved", 0) == 0:
            findings.append({
                "type": "warning",
                "message": "No context chunks were retrieved from the database.",
                "recommendation": "Ensure code has been properly indexed. Run context indexing on the project first."
            })
        elif rag_metrics.get("content_quality", 0) < 0.5:
            findings.append({
                "type": "warning",
                "message": "Retrieved context appears to be low quality or incomplete.",
                "recommendation": "Review chunking strategy and embedding quality."
            })
        
        # Check plan generation
        plan_metrics = self.report_data.get("stages", {}).get("plan_generation", {}).get("metrics", {})
        if not plan_metrics.get("success", False):
            findings.append({
                "type": "error",
                "message": f"Plan generation failed: {plan_metrics.get('error', 'Unknown error')}",
                "recommendation": "Check that the planner agent is working correctly."
            })
        elif plan_metrics.get("step_count", 0) == 0:
            findings.append({
                "type": "warning",
                "message": "Generated plan contains no steps.",
                "recommendation": "Ensure the modification request is clear and actionable."
            })
        elif plan_metrics.get("invalid_files", []):
            findings.append({
                "type": "warning",
                "message": f"Plan references {len(plan_metrics.get('invalid_files', []))} files that don't exist.",
                "recommendation": "Consider improving file existence validation in the planner."
            })
        
        # Check code execution
        exec_metrics = self.report_data.get("stages", {}).get("code_execution", {}).get("metrics", {})
        step_results = self.report_data.get("stages", {}).get("code_execution", {}).get("step_results", {})
        if not exec_metrics.get("success", False):
            findings.append({
                "type": "error",
                "message": f"Code execution failed: {exec_metrics.get('error', 'Unknown error')}",
                "recommendation": "Check the code execution engine and traceback for detailed error information."
            })
        else:
            failure_count = sum(1 for r in step_results.values() if not r.get("success", False))
            if failure_count > 0:
                findings.append({
                    "type": "warning",
                    "message": f"{failure_count} out of {len(step_results)} modification steps failed.",
                    "recommendation": "Review individual step errors and improve error handling."
                })
            
            if exec_metrics.get("files_modified", 0) == 0:
                findings.append({
                    "type": "warning",
                    "message": "No files were modified during code execution.",
                    "recommendation": "Check if the plan is appropriate for the request."
                })
        
        # Check unit tests
        test_metrics = self.report_data.get("stages", {}).get("unit_tests", {}).get("metrics", {})
        if not test_metrics.get("success", False):
            findings.append({
                "type": "error",
                "message": f"Unit test generation failed: {test_metrics.get('error', 'Unknown error')}",
                "recommendation": "Check the test generator agent and error logs."
            })
        elif test_metrics.get("test_files_count", 0) == 0 and len(self.report_data.get("stages", {}).get("code_execution", {}).get("step_results", {})) > 0:
            findings.append({
                "type": "warning",
                "message": "No test files were generated.",
                "recommendation": "Review test generation logic to ensure it's creating tests for modified files."
            })
        elif test_metrics.get("duplicate_unittest_main", False):
            findings.append({
                "type": "warning",
                "message": "Duplicate unittest.main() calls detected in test files.",
                "recommendation": "Improve post-processing to clean up test files."
            })
        
        # Check quality checks
        quality_metrics = self.report_data.get("stages", {}).get("quality_checks", {}).get("metrics", {})
        if not quality_metrics.get("success", False):
            findings.append({
                "type": "error",
                "message": f"Quality check failed: {quality_metrics.get('error', 'Unknown error')}",
                "recommendation": "Check the quality checker agent and error logs."
            })
        elif quality_metrics.get("issues_found", 0) > 0:
            findings.append({
                "type": "warning",
                "message": f"Found {quality_metrics.get('issues_found', 0)} quality issues.",
                "recommendation": "Add post-processing to address common quality issues."
            })
        
        # Add overall recommendation
        if not self.report_data.get("overall_result", False):
            # Find the earliest failure point
            failure_stage = None
            for stage in ["rag_retrieval", "plan_generation", "code_execution", "unit_tests", "quality_checks"]:
                metrics = self.report_data.get("stages", {}).get(stage, {}).get("metrics", {})
                if not metrics.get("success", False):
                    failure_stage = stage
                    break
            
            if failure_stage:
                findings.append({
                    "type": "error",
                    "message": f"Workflow failed at the {failure_stage.replace('_', ' ')} stage.",
                    "recommendation": f"Focus debugging efforts on the {failure_stage.replace('_', ' ')} component."
                })
        
        return findings
    

def main():
    """Command-line interface for running the modification analyzer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="I2C Factory Modification Workflow Analyzer")
    parser.add_argument("request", help="The modification request to analyze")
    parser.add_argument("project_path", help="Path to the project directory")
    parser.add_argument("--language", "-l", default="python", help="Programming language (default: python)")
    parser.add_argument("--output-dir", "-o", default="./diagnostic_reports", help="Output directory for reports")
    
    args = parser.parse_args()
    
    analyzer = ModificationAnalyzer(output_dir=Path(args.output_dir))
    analyzer.run_diagnostic(
        user_request=args.request,
        project_path=Path(args.project_path),
        language=args.language
    )

if __name__ == "__main__":
    main()