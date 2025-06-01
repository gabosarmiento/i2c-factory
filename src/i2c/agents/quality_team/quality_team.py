# src/i2c/agents/quality_team/quality_team.py

from typing import Dict, Any, List
from pathlib import Path
import asyncio
from builtins import llm_highest, llm_middle

from agno.team import Team
from agno.agent import Agent

# Import CLI for logging
try:
    from i2c.cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_GUARD] {msg}")
        def error(self, msg): print(f"[ERROR_GUARD] {msg}")
        def info(self, msg): print(f"[INFO_GUARD] {msg}")
        def success(self, msg): print(f"[SUCCESS_GUARD] {msg}")
    canvas = FallbackCanvas()


# Import existing Quality components
from i2c.agents.quality_team.static_analysis_agent import static_analysis_agent
from i2c.agents.quality_team.reviewer_agent import reviewer_agent
from i2c.agents.quality_team.guardrail_agent import guardrail_agent
from i2c.agents.quality_team.integration_checker_agent import integration_checker_agent

# Import new Enterprise Static Analyzer
from i2c.agents.quality_team.enterprise_static_analyzer import enterprise_static_analyzer
from i2c.agents.quality_team.utils.language_detector import LanguageDetector

class QualityLeadAgent(Agent):
    """Lead agent for the Quality Team that coordinates quality checks"""
    
    # Define known quality gates
    ENTERPRISE_QUALITY_GATES = {
        'python': ['flake8', 'black', 'mypy', 'pytest', 'bandit'],
        'javascript': ['eslint'],
        'typescript': ['eslint', 'tsc'],
        'go': ['govet'],
        'java': ['checkstyle'],
        'all': ['flake8', 'black', 'mypy', 'pytest', 'bandit', 'eslint', 'tsc', 'govet', 'checkstyle']
    }
    
    def __init__(self, knowledge_base=None, **kwargs):
        """
        Initialize the Quality Lead Agent.
        
        Args:
            knowledge_base: Optional knowledge base for context retrieval
            **kwargs: Additional arguments for Agent initialization
        """
        # RAG Integration: Store knowledge base for context retrieval
        self.knowledge_base = knowledge_base
        
        super().__init__(
            name="QualityLead",
            model=llm_middle, 
            role="Leads the quality team to ensure code quality",
            instructions=[
                "You are the lead of the Quality Team, responsible for code quality checks.",
                "Your job is to coordinate quality validation of code changes.",
                "You must ensure that the code meets quality standards and adheres to best practices.",
                
                # Message parsing instructions
                "You will receive messages in this format:",
                "{",
                "  'instruction': 'Validate the modified files using all relevant quality gates.',",
                "  'project_path': '/path/to/project',",
                "  'modified_files': {'file.py': 'content...', 'file2.js': 'content...'},",
                "  'quality_gates': ['python', 'javascript']  # Optional presets or specific tools"
                "}",
                
                # Processing instructions
                "When you receive a message, follow these steps:",
                "1. Identify the project_path, modified_files, and quality_gates from the message",
                "1.5 If 'quality_gates' is missing or empty, use your internal logic to decide which gates apply based on the file types.",
                "2. Detect the programming languages used in the modified files",
                "3. Use file types to determine appropriate language presets or resolve any explicit tools from 'quality_gates'",
                "4. You must call your validate_changes(...) function using the values from the message.",
                "5. Format the response according to the expected structure",
                
                # Language detection
                "Use the file extensions and contents to determine appropriate quality gates:",
                "- .py files: Use Python quality gates (flake8, black, mypy, pytest, bandit)",
                "- .js files: Use JavaScript quality gates (eslint)",
                "- .ts files: Use TypeScript quality gates (eslint, tsc)",
                "- .go files: Use Go quality gates (govet)",
                "- .java files: Use Java quality gates (checkstyle)",
                
                # Resource optimization
                "Be smart about resource usage:",
                "- Only run quality gates appropriate for the detected languages",
                "- Prioritize critical checks (syntax, type) before style checks",
                "- Skip tools that would fail based on missing dependencies",
                
                # Response formatting
                "Return results in this format:",
                "{",
                "  'passed': boolean,  # Overall pass/fail status",
                "  'issues': [string],  # List of identified issues",
                "  'gate_results': {  # Results per quality gate",
                "    'flake8': {'passed': boolean, 'issues': [string]},",
                "    'eslint': {'passed': boolean, 'issues': [string]},",
                "    'tsc': {'passed': boolean, 'issues': [string]}"
                "  }",
                "}",
                
                # Detailed process instructions
                "For each validation request:",
                "1. Run static analysis to identify lint errors",
                "2. Run enterprise checks based on quality gates",
                "3. Request code review from the reviewer agent",
                "4. Check integration issues across files",
                "5. Apply guardrails to decide if the changes are acceptable",
                "6. Compile all results and return a structured response",
                "Always return a dictionary as a response, even if validation fails or inputs are incomplete.",
                "If a tool fails, still include it in 'gate_results' with 'passed': False and an error message.",
                "If any quality issues are found, provide clear feedback for correction."
            ],
            **kwargs
        )
        # Initialize team session state if needed
        if self.team_session_state is None:
            self.team_session_state = {}

    # RAG Integration: Add method to retrieve relevant context
    def _retrieve_context(self, task_description, quality_gates=None):
        """
        Retrieve relevant context from knowledge base for the quality task.
        
        Args:
            task_description: Description of the validation task
            quality_gates: List of quality gates to check
            
        Returns:
            String containing relevant context or empty string if no context found
        """
        if not self.knowledge_base:
            return ""
            
        try:
            # Build a query from the task description and quality gates
            query = task_description
            if quality_gates:
                query += f" quality gates: {' '.join(quality_gates)}"
                
            # Log the query being used
            canvas.info(f"[QualityLeadAgent] Retrieving context for: {query[:100]}...")
            
            # Retrieve top-k most relevant chunks
            context_chunks = self.knowledge_base.search(
                query=query, 
                limit=3,  # top-k=3
                max_tokens=800  # Limit context size
            )
            
            # Format the retrieved context
            if not context_chunks:
                canvas.info("[QualityLeadAgent] No relevant context found")
                return ""
                
            # Extract content from chunks and join with separators
            context_text = "\n\n".join([
                f"SOURCE: {chunk.get('source', 'unknown')}\n{chunk.get('content', '')}" 
                for chunk in context_chunks
            ])
            
            # Log what was retrieved for transparency
            canvas.info(f"[QualityLeadAgent] Retrieved {len(context_chunks)} context chunks ({len(context_text)} chars)")
            
            return context_text
        except Exception as e:
            canvas.warning(f"[QualityLeadAgent] Error retrieving context: {e}")
            return ""  # Graceful fallback

    async def _decide_quality_gate_presets_with_llm(
        self, project_path: Path, modified_files: Dict[str, str]
    ) -> List[str]:
        """
        Use the LLM to decide which preset quality gates to apply.
        It returns keys like 'python', 'javascript', 'minimal', etc.
        """
        message = (
            "Given the following modified files, decide which quality gate presets to apply.\n"
            "Available presets:\n"
            f"{list(self.ENTERPRISE_QUALITY_GATES.keys())}\n\n"
            "Return a Python list like: ['python', 'security']\n\n"
            "Files:\n" +
            "\n".join(modified_files.keys())
        )

        # RAG Integration: Retrieve relevant context about quality gates
        context = self._retrieve_context("selecting appropriate quality gates for files", 
                                        list(self.ENTERPRISE_QUALITY_GATES.keys()))
        
        # RAG Integration: Add context to the message if available
        if context:
            message = (
                "Context for quality gate selection:\n"
                f"{context}\n\n"
                f"{message}"
            )
            # Log the enhanced prompt for transparency
            canvas.info("[QualityLeadAgent] Enhanced quality gate selection with context")

        response = await self.model.aask(message)
        try:
            import ast
            result = ast.literal_eval(response.content.strip())
            if isinstance(result, list):
                return result
        except Exception:
            pass
        return []

    async def _run_knowledge_validation(
        self, modified_files: Dict[str, str], context: str = ""
    ) -> Dict[str, Any]:
        """Run knowledge pattern validation"""
        try:
            # Check if we have knowledge context
            if not self.team_session_state or "retrieved_context" not in self.team_session_state:
                return {"passed": True, "issues": [], "message": "No knowledge context available"}
            
            from i2c.agents.knowledge.knowledge_validator import KnowledgeValidator
            
            validator = KnowledgeValidator()
            validation_result = validator.validate_generation_output(
                generated_files=modified_files,
                retrieved_context=self.team_session_state["retrieved_context"],
                task_description="Quality validation of modified files"
            )
            
            # Convert ValidationResult to dict
            knowledge_issues = []
            if not validation_result.success:
                knowledge_issues = validation_result.violations
            
            canvas.info(f"🧪 Knowledge validation score: {validation_result.score:.2f}")
            
            return {
                "passed": validation_result.success,
                "issues": knowledge_issues,
                "score": validation_result.score,
                "applied_patterns": validation_result.applied_patterns,
                "missing_patterns": validation_result.missing_patterns
            }
            
        except Exception as e:
            canvas.error(f"[QualityLeadAgent] Error in knowledge validation: {e}")
            return {
                "passed": False,
                "issues": [f"Knowledge validation error: {str(e)}"],
                "score": 0.0,
                "applied_patterns": [],
                "missing_patterns": []
            }
    
    async def validate_changes(
            self, project_path: Path, modified_files: Dict[str, str], quality_gates: List[str] = None
        ) -> Dict[str, Any]:
        """
        Validate code changes for quality with knowledge pattern validation.
        
        Args:
            project_path: Path to the project directory
            modified_files: Dictionary of modified files (path -> content)
            quality_gates: List of quality gates to check (e.g., 'flake8', 'black', etc.)
                           or preset gate groups like 'python', 'all', etc.
            
        Returns:
            Dictionary with validation results including knowledge compliance
        """
        if quality_gates is None:
            presets = await self._decide_quality_gate_presets_with_llm(project_path, modified_files)
            quality_gates = presets
        
        # Resolve quality gates to specific tools if preset names are used
        resolved_gates = self._resolve_quality_gates(quality_gates)
        canvas.info(f"[QualityLeadAgent] Running quality gates: {resolved_gates}")

        # RAG Integration: Retrieve relevant context for validation task
        task_description = f"Validating code changes with quality gates: {', '.join(resolved_gates)}"
        context = self._retrieve_context(task_description, resolved_gates)
        
        # This function will coordinate the Quality team activities
        try:
            # 1. Static analysis check
            static_analysis_results = await self._run_static_analysis(
                project_path, modified_files, resolved_gates, context
            )
            
            # 2. Enterprise quality gates check (if any gates specified)
            if resolved_gates:
                enterprise_results = await self._run_enterprise_checks(
                    project_path, modified_files, resolved_gates, context
                )
            else:
                enterprise_results = {"passed": True, "issues": []}
            
            # 3. Code review check
            review_results = await self._run_code_review(
                project_path, modified_files, context
            )
            
            # 4. Integration check
            integration_results = await self._run_integration_checks(
                project_path, modified_files, context
            )
            
            # NEW: 5. Knowledge pattern validation
            knowledge_validation_results = await self._run_knowledge_validation(
                modified_files, context
            )
            
            # 6. Guardrail check - include all results
            guardrail_results = await self._run_guardrail_checks(
                static_analysis_results, 
                review_results, 
                integration_results,
                enterprise_results,
                knowledge_validation_results,
                context
            )
            
            # 7. Determine overall pass/fail
            all_passed = guardrail_results.get("decision") == "CONTINUE"
            
            # 8. Collect issues
            issues = []
            issues.extend(static_analysis_results.get("issues", []))
            issues.extend(review_results.get("issues", []))
            issues.extend(integration_results.get("issues", []))
            issues.extend(enterprise_results.get("issues", []))
            issues.extend(guardrail_results.get("reasons", []))
            
            # Prepare gate results for response
            gate_results = {}
            
            # Add enterprise results to gate_results
            if enterprise_results and "detailed_results" in enterprise_results:
                detailed = enterprise_results.get("detailed_results", {})
                if "issues" in detailed:
                    for file_path, file_issues in detailed.get("issues", {}).items():
                        for gate, gate_result in file_issues.items():
                            if gate not in gate_results:
                                gate_results[gate] = {
                                    "passed": True,
                                    "issues": []
                                }
                            
                            # If this gate has issues, mark it as failed
                            if gate_result.get("issues", []):
                                gate_results[gate]["passed"] = False
                                gate_results[gate]["issues"].extend(
                                    [f"{file_path}: {issue}" for issue in gate_result.get("issues", [])]
                                )
            
            # Add static analysis to gate_results
            if static_analysis_results and static_analysis_results.get("summary", {}).get("total_lint_errors", 0) > 0:
                gate_results["static_analysis"] = {
                    "passed": static_analysis_results.get("passed", True),
                    "issues": static_analysis_results.get("issues", [])
                }
            
            # Add review results to gate_results
            if review_results and review_results.get("issues", []):
                gate_results["code_review"] = {
                    "passed": review_results.get("passed", True),
                    "issues": review_results.get("issues", [])
                }
            
            # Add integration results to gate_results
            if integration_results and integration_results.get("issues", []):
                gate_results["integration"] = {
                    "passed": integration_results.get("passed", True),
                    "issues": integration_results.get("issues", [])
                }
            
            # Store results in the team session state
            if self.team_session_state is not None:
                self.team_session_state["validation_results"] = {
                    "passed": all_passed,
                    "issues": issues,
                    "gate_results": gate_results,
                    "static_analysis_results": static_analysis_results,
                    "enterprise_results": enterprise_results,
                    "review_results": review_results,
                    "integration_results": integration_results,
                    "guardrail_results": guardrail_results
                }
            
            # Return the structured response expected by the orchestrator
            return {
                "passed": all_passed,
                "issues": issues,
                "gate_results": gate_results,
                "summary": {
                    "total_issues": len(issues),
                    "static_analysis": static_analysis_results.get("passed", True),
                    "enterprise_checks": enterprise_results.get("passed", True),
                    "code_review": review_results.get("passed", True),
                    "integration": integration_results.get("passed", True),
                    "guardrails": guardrail_results.get("decision") == "CONTINUE"
                }
            }
            
        except Exception as e:
            import traceback
            error_info = {
                "passed": False,
                "error": f"Quality team error: {str(e)}",
                "error_details": traceback.format_exc(),
                "issues": [f"Quality validation error: {str(e)}"],
                "gate_results": {}
            }
            
            # Store error in the team session state
            if self.team_session_state is not None:
                self.team_session_state["validation_results"] = error_info
                
            return error_info
    
    def _resolve_quality_gates(self, quality_gates: List[str] = None) -> List[str]:
        """
        Resolve quality gate preset names to specific tools.
        
        Args:
            quality_gates: List of quality gates or presets
            
        Returns:
            Resolved list of quality gates
        """
        if not quality_gates:
            return []
            
        resolved = []
        for gate in quality_gates:
            if gate in self.ENTERPRISE_QUALITY_GATES:
                # This is a preset, expand it
                resolved.extend(self.ENTERPRISE_QUALITY_GATES[gate])
            else:
                # This is a specific tool
                resolved.append(gate)
                
        # Remove duplicates while preserving order
        seen = set()
        return [x for x in resolved if not (x in seen or seen.add(x))]
    
    # RAG Integration: Add context parameter to static analysis
    async def _run_static_analysis(
        self, project_path: Path, modified_files: Dict[str, str], 
        quality_gates: List[str], context: str = ""
    ) -> Dict[str, Any]:
        """Run static analysis checks with enhanced context"""
        try:
            # Use static_analysis_agent to analyze code quality
            analysis_summary = static_analysis_agent.get_analysis_summary(project_path)
            
            # Convert to the expected format
            return {
                "passed": analysis_summary.get("total_lint_errors", 0) == 0,
                "summary": analysis_summary,
                "issues": [f"Lint error in {file}" for file in analysis_summary.get("files_with_lint_errors", [])]
            }
        except Exception as e:
            canvas.error(f"[QualityLeadAgent] Error in static analysis: {e}")
            return {
                "passed": False,
                "summary": {"errors": [str(e)]},
                "issues": [f"Static analysis error: {str(e)}"]
            }
    
    # RAG Integration: Add context parameter to enterprise checks
    async def _run_enterprise_checks(
        self, project_path: Path, modified_files: Dict[str, str], 
        quality_gates: List[str], context: str = ""
    ) -> Dict[str, Any]:
        """Run enterprise quality gate checks with enhanced context"""

        try:
            # Use enterprise_static_analyzer to run quality gates
            enterprise_results = enterprise_static_analyzer.analyze_files(modified_files, quality_gates)
            
            # Extract issues into a flat list for easier processing
            issues = []
            if enterprise_results.get("files_with_issues"):
                for file_path in enterprise_results.get("files_with_issues", []):
                    file_issues = enterprise_results.get("issues", {}).get(file_path, {})
                    for gate, gate_result in file_issues.items():
                        for issue in gate_result.get("issues", []):
                            issues.append(f"[{gate}] {file_path}: {issue}")
            
            return {
                "passed": enterprise_results.get("passed", False),
                "summary": enterprise_results.get("summary", {}),
                "issues": issues,
                "detailed_results": enterprise_results
            }
        except Exception as e:
            canvas.error(f"[QualityLeadAgent] Error in enterprise checks: {e}")
            return {
                "passed": False,
                "summary": {"errors": [str(e)]},
                "issues": [f"Enterprise quality check error: {str(e)}"],
                "detailed_results": {}
            }
    
    # RAG Integration: Add context parameter to code review
    async def _run_code_review(
        self, project_path: Path, modified_files: Dict[str, str], context: str = ""
    ) -> Dict[str, Any]:
        """Run code review with enhanced context"""
        try:
            # Determine the dominant language in modified files
            language_counts = {}
            for file_path in modified_files:
                lang = LanguageDetector.detect_language(file_path)
                if lang != 'unknown':
                    language_counts[lang] = language_counts.get(lang, 0) + 1
            
            # Find the most common language
            dominant_language = max(language_counts.items(), key=lambda x: x[1])[0] if language_counts else "python"
            
            # RAG Integration: Enhance the review objective with context
            review_objective = "Ensure code quality"
            if context:
                # Add the retrieved context to the review objective
                review_objective = f"Ensure code quality based on the following context:\n{context}\n\nReview objective: Ensure code quality"
                canvas.info(f"[QualityLeadAgent] Enhanced code review with {len(context)} chars of context")
            
            # Use reviewer_agent to review code
            structured_goal = {
                "objective": review_objective, 
                "language": dominant_language.capitalize()  # Provide actual language
            }
            review_feedback = reviewer_agent.review_code(structured_goal, modified_files)
            
            # Simple check for potential issues in the review
            has_issues = False
            if review_feedback:
                # Look for negative keywords in the review
                negative_keywords = ["fail", "error", "incorrect", "missing", "does not align", "issues"]
                review_lower = review_feedback.lower()
                has_issues = any(keyword in review_lower for keyword in negative_keywords)
            
            return {
                "passed": not has_issues,
                "feedback": review_feedback,
                "issues": [review_feedback] if has_issues else []
            }
        except Exception as e:
            canvas.error(f"[QualityLeadAgent] Error in code review: {e}")
            return {
                "passed": False,
                "feedback": f"Error during code review: {str(e)}",
                "issues": [f"Code review error: {str(e)}"]
            }
    
    # RAG Integration: Add context parameter to integration checks
    async def _run_integration_checks(
        self, project_path: Path, modified_files: Dict[str, str], context: str = ""
    ) -> Dict[str, Any]:
        """Run integration checks with enhanced context"""
        try:
            # Use integration_checker_agent to check integration
            integration_issues = integration_checker_agent.check_integrations(project_path)
            
            return {
                "passed": len(integration_issues) == 0,
                "issues": integration_issues
            }
        except Exception as e:
            canvas.error(f"[QualityLeadAgent] Error in integration checks: {e}")
            return {
                "passed": False,
                "issues": [f"Integration check error: {str(e)}"]
            }
    
    # RAG Integration: Add context parameter to guardrail checks
    async def _run_guardrail_checks(
        self, 
        static_analysis_results: Dict[str, Any],
        review_results: Dict[str, Any],
        integration_results: Dict[str, Any],
        enterprise_results: Dict[str, Any] = None,
        context: str = ""
    ) -> Dict[str, Any]:
        """Run guardrail checks with enhanced context"""
        try:
            # Use guardrail_agent to apply guardrails
            # Additional input for dependency_summary and syntax_check_result
            dependency_summary = []  # Placeholder
            syntax_check_result = (enterprise_results.get("passed", True), "")  # Simplified
            
            # Get review feedback from review results
            review_feedback = review_results.get("feedback", "")
            
            # RAG Integration: Enhance review feedback with context if available
            if context and review_feedback:
                # Prepend the context to the review feedback
                review_feedback = f"Context for guardrail evaluation:\n{context}\n\nReview feedback:\n{review_feedback}"
                canvas.info(f"[QualityLeadAgent] Enhanced guardrail check with context")
            
            # Default values in case of failure
            decision = "BLOCK"
            reasons = []
            
            # Only call guardrail agent if we have valid inputs
            if static_analysis_results and static_analysis_results.get("summary") is not None:
                try:
                    # Call with manual unpacking
                    result = guardrail_agent.evaluate_results(
                        static_analysis_results.get("summary"),
                        dependency_summary,
                        syntax_check_result,
                        review_feedback
                    )
                    
                    
                    # Handle different return formats safely
                    if isinstance(result, tuple):
                        if len(result) >= 2:
                            decision = result[0]
                            reasons = result[1]
                        elif len(result) == 1:
                            decision = result[0]
                            reasons = ["No specific reasons provided"]
                    elif isinstance(result, str):
                        decision = result
                        reasons = ["No specific reasons provided"]
                    elif isinstance(result, dict):
                        decision = result.get("decision", "BLOCK")
                        reasons = result.get("reasons", [])
                    else:
                        canvas.warning(f"[QualityLeadAgent] Unexpected guardrail result format: {type(result)}")
                except IndexError:
                    canvas.warning("[QualityLeadAgent] Index error in guardrail evaluation")
                    reasons = ["Guardrail evaluation encountered an index error"]
                except Exception as eval_error:
                    canvas.warning(f"[QualityLeadAgent] Error in guardrail evaluation: {eval_error}")
                    reasons = [f"Guardrail evaluation error: {str(eval_error)}"]
            else:
                reasons = ["Missing static analysis results for guardrail evaluation"]
            
            # Add reasons from enterprise checks if they failed
            if enterprise_results and not enterprise_results.get("passed", True):
                summary = enterprise_results.get("summary", {})
                if summary.get("quality_gates_failed", 0) > 0:
                    failed_gates = summary.get("quality_gates_failed", 0)
                    total_issues = summary.get("total_issues", 0)
                    reasons.append(f"Enterprise quality gates: {failed_gates} gates failed with {total_issues} issues")
            
            return {
                "decision": decision,
                "reasons": reasons
            }
        except Exception as e:
            canvas.error(f"[QualityLeadAgent] Error in guardrail checks: {e}")
            return {
                "decision": "BLOCK",
                "reasons": [f"Guardrail check error: {str(e)}"]
            }

def build_quality_team(session_state=None, knowledge_base=None) -> Team:
    """
    Build the quality team with a lead agent and specialized members.
    
    Args:
        session_state: Optional shared session state dictionary.
        knowledge_base: Optional knowledge base for context retrieval.
        
    Returns:
        Team: Configured quality team
    """
    # Create the Quality lead agent with knowledge base
    quality_lead = QualityLeadAgent(knowledge_base=knowledge_base)
    
    # Use shared session if provided, else initialize defaults
    if session_state is None:
        session_state = {
            "validation_results": None,
        }
    else:
        session_state.setdefault("validation_results", None)
    
    # Create the team
    return Team(
        name="QualityTeam",
        members=[quality_lead],
        mode="collaborate",
        model=llm_middle,
        instructions=[
            "You are the Quality Team, responsible for code quality.",
            "Follow the lead of the QualityLead agent, who will coordinate your activities.",
            
            # Message parsing instructions
            "You will receive messages with validation requests like:",
            "{",
            "  'instruction': 'Validate the modified files using all relevant quality gates.',",
            "  'project_path': '/path/to/project',",
            "  'modified_files': {'file.py': 'content...', 'file2.js': 'content...'},",
            "  'quality_gates': ['flake8', 'mypy'] # Optional quality gates",
            "}",
            
            # Response formatting
            "Your response should include:",
            "{",
            "  'passed': boolean,  # Overall pass/fail status",
            "  'issues': [string],  # List of identified issues",
            "  'gate_results': {  # Results per quality gate",
            "    'flake8': {'passed': boolean, 'issues': [string]},",
            "    'mypy': {'passed': boolean, 'issues': [string]}",
            "  }",
            "}",
            
            "Ensure that code changes meet quality standards and adhere to best practices.",
            "Apply enterprise-grade quality gates like flake8, black, mypy, pytest, and bandit for Python code.",
            "Focus on issues that would affect readability, maintainability, or correctness."
        ],
        session_state=session_state
    )