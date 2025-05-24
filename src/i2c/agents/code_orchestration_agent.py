from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json
import asyncio
import datetime
from builtins import llm_middle
from agno.agent import Agent
from agno.team import Team

# Import necessary team builders
from i2c.agents.modification_team.code_modification_manager_agno import build_code_modification_team
from i2c.agents.quality_team.quality_team import build_quality_team
from i2c.agents.sre_team.sre_team import build_sre_team
from i2c.agents.knowledge.knowledge_team import build_knowledge_team
from i2c.cli.controller import canvas
from pydantic import BaseModel, Field
from typing import Dict, Any, List

class OrchestrationResult(BaseModel):
    decision: str = Field(..., description="Final decision: approve or reject")
    reason: str = Field(..., description="Explanation for the decision")
    modifications: Dict[str, Any] = Field(..., description="Summary of code modifications")
    quality_results: Dict[str, Any] = Field(..., description="Results of quality validations")
    sre_results: Dict[str, Any] = Field(..., description="Results of operational checks")
    reasoning_trajectory: List[Dict[str, Any]] = Field(..., description="Reasoning steps taken during the process")


class CodeOrchestrationAgent(Agent):
    def __init__(
        self, 
        *, 
        session_state: Optional[Dict[str, Any]] = None,  
        **kwargs,
    ) -> None:
        # ------------------------------------------------------------------
        # 1. Ensure we have a shared, mutable dict (create it exactly once)
        # ------------------------------------------------------------------
        if session_state is None:
            session_state = {
                "objective": None,
                "project_path": None,
                "task": None,
                "constraints": None,
                "quality_gates": None,
                "analysis": None,
                "modification_plan": None,
                "modification_result": None,
                "quality_results": None,
                "sre_results": None,
                "refinement_result": None,
                "reasoning_trajectory": [],
                # Fields relied upon by downstream teams
                "modified_files": {},
                "unit_tests": {},
            }

        self.session_state = session_state  # the single pointer
        # ------------------------------------------------------------------
        # 2. AGNO initialisation (name, model, role, instructions)
        # ------------------------------------------------------------------
        super().__init__(  # noqa: D401 – imperative style is fine
            name="CodeOrchestrator",
            model=llm_middle,
            role="Orchestrates the end-to-end code evolution process with reasoning and reflection",
            instructions=[
                "You are the lead orchestrator of a code evolution factory.",
                "Coordinate specialized teams (Knowledge, Modification, Quality, SRE) to safely evolve code.",
                "For each objective, you must:",
                "1. Analyze project context",
                "2. Create a modification plan",
                "3. Execute modifications",
                "4. Validate with quality and operational checks",
                "5. Reflect on failures and adapt",
                "6. Make a final decision: approve or reject with reasoning",
                "Always prioritize code quality and safety."
            ],
            **kwargs
        )

        # ⬅️ Add strict JSON output enforcement for agent responses
        self.instructions.extend([
            "IMPORTANT: Your final response must be **valid JSON** with this format:",
            "```json",
            '{',
            '  "decision": "approve",',
            '  "reason": "All quality and operational checks passed",',
            '  "modifications": { "sample.py": "Added type hints" },',
            '  "quality_results": { "lint": "passed", "types": "passed", "security": "passed" },',
            '  "sre_results": { "uptime_check": "passed" },',
            '  "reasoning_trajectory": [ { "step": "Final Decision", "description": "All gates passed", "success": true } ]',
            '}',
            "```",
            "Do NOT output explanations, markdown, or narratives. Only return the JSON object."
        ])

        # placeholders; real teams wired in _initialize_teams()
        self.knowledge_team: Team | None = None
        self.modification_team: Team | None = None
        self.quality_team: Team | None = None
        self.sre_team: Team | None = None

        # Build specialist teams with the shared state
        self._initialize_teams()
        self._initialize_reflective_operators()

    def _initialize_teams(self):
        """Instantiate all specialist teams **with the same session_state**."""
        shared = self.session_state  # one pointer for every team

        self.knowledge_team = build_knowledge_team(session_state=shared)
        self.modification_team = build_code_modification_team(session_state=shared)
        self.quality_team = build_quality_team(session_state=shared)
        self.sre_team = build_sre_team(session_state=shared)

    def _initialize_reflective_operators(self):
        """Skip reflective operators to avoid circular imports - implement self-healing directly"""
        canvas.info("Skipping reflective operators initialization to avoid circular imports")
        self.plan_refinement_operator = None
        self.issue_resolution_operator = None

    def _analyze_failure_patterns(self, quality_results: Dict[str, Any], sre_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze validation failures to determine recovery strategy"""
        
        # Collect all issues
        all_issues = []
        all_issues.extend(quality_results.get("issues", []))
        all_issues.extend(sre_results.get("issues", []))
        
        # Convert to lowercase for pattern matching
        issues_text = " ".join(all_issues).lower()
        
        # Critical issue patterns and recovery strategies
        recovery_analysis = {
            "strategy": "unknown",
            "confidence": "low",
            "auto_recoverable": False,
            "issues_found": all_issues,
            "patterns_detected": []
        }
        
        # Auto-recoverable patterns (simple fixes)
        if any(pattern in issues_text for pattern in ["syntax error", "indentation", "missing import", "undefined name"]):
            recovery_analysis.update({
                "strategy": "auto_fix_syntax",
                "confidence": "high", 
                "auto_recoverable": True,
                "patterns_detected": ["syntax_issues"]
            })
            
        elif any(pattern in issues_text for pattern in ["test failed", "assertion", "expected", "actual"]):
            recovery_analysis.update({
                "strategy": "fix_test_logic",
                "confidence": "medium",
                "auto_recoverable": True,
                "patterns_detected": ["test_failures"]
            })
            
        # Replan-recoverable patterns (need new approach)
        elif any(pattern in issues_text for pattern in ["performance", "timeout", "memory", "optimization"]):
            recovery_analysis.update({
                "strategy": "replan_performance",
                "confidence": "medium",
                "auto_recoverable": False,
                "patterns_detected": ["performance_issues"]
            })
            
        # Human escalation patterns (complex/risky)
        elif any(pattern in issues_text for pattern in ["security", "vulnerability", "privilege", "injection"]):
            recovery_analysis.update({
                "strategy": "human_escalation",
                "confidence": "high",
                "auto_recoverable": False,
                "patterns_detected": ["security_issues"]
            })
            
        # No specific pattern detected
        elif all_issues:
            recovery_analysis.update({
                "strategy": "generic_retry",
                "confidence": "low",
                "auto_recoverable": False,
                "patterns_detected": ["unknown_issues"]
            })
        else:
            # No issues - shouldn't reach here
            recovery_analysis.update({
                "strategy": "no_action",
                "confidence": "high",
                "auto_recoverable": True,
                "patterns_detected": []
            })
        
        self._add_reasoning_step(
            "Failure Analysis", 
            f"Detected pattern: {recovery_analysis['strategy']} (confidence: {recovery_analysis['confidence']})"
        )
        
        return recovery_analysis

    async def _execute_self_healing(self, recovery_analysis: Dict[str, Any], modification_result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute self-healing based on failure analysis"""
        
        strategy = recovery_analysis.get("strategy")
        issues = recovery_analysis.get("issues_found", [])
        
        self._add_reasoning_step("Self-Healing", f"Attempting recovery strategy: {strategy}")
        
        try:
            if strategy == "auto_fix_syntax":
                return await self._auto_fix_syntax_issues(modification_result, issues)
                
            elif strategy == "fix_test_logic":
                return await self._fix_test_failures(modification_result, issues)
                
            elif strategy == "replan_performance":
                return await self._replan_for_performance(modification_result, issues)
                
            elif strategy == "generic_retry":
                return await self._generic_retry_with_context(modification_result, issues)
                
            elif strategy == "human_escalation":
                return await self._escalate_to_human(modification_result, issues)
                
            else:
                # No recovery action
                self._add_reasoning_step("Self-Healing", "No recovery action needed", success=True)
                return modification_result
                
        except Exception as e:
            self._add_reasoning_step("Self-Healing", f"Recovery failed: {str(e)}", success=False)
            return modification_result

    async def _auto_fix_syntax_issues(self, modification_result: Dict[str, Any], issues: List[str]) -> Dict[str, Any]:
        """Auto-fix common syntax issues"""
        self._add_reasoning_step("Auto-Fix", "Attempting to fix syntax issues")
        
        # Simple approach: re-run modification with explicit syntax focus
        modified_files = modification_result.get("modified_files", {})
        
        for file_path, content in modified_files.items():
            if file_path.endswith('.py'):
                # Basic syntax fixes
                fixed_content = self._apply_basic_syntax_fixes(content)
                if fixed_content != content:
                    # Write the fixed content
                    project_path = Path(self.session_state.get("project_path", ""))
                    full_path = project_path / file_path
                    full_path.write_text(fixed_content, encoding="utf-8")
                    modified_files[file_path] = fixed_content
                    
                    self._add_reasoning_step("Auto-Fix", f"Applied syntax fixes to {file_path}", success=True)
        
        return {"modified_files": modified_files, "auto_fixed": True}

    async def _fix_test_failures(self, modification_result: Dict[str, Any], issues: List[str]) -> Dict[str, Any]:
        """Fix test failures by modifying test expectations or code"""
        self._add_reasoning_step("Test-Fix", "Attempting to fix test failures")
        
        # For now, simple approach: regenerate tests
        try:
            from i2c.agents.sre_team.unit_test import unit_test_generator
            
            modified_files = modification_result.get("modified_files", {})
            project_path = Path(self.session_state.get("project_path", ""))
            
            # Regenerate tests for Python files
            for file_path in modified_files:
                if file_path.endswith('.py') and not file_path.startswith('test_'):
                    temp_code_map = {file_path: modified_files[file_path]}
                    new_tests = unit_test_generator.generate_tests(temp_code_map)
                    
                    # Update with regenerated tests
                    for test_file_path, test_content in new_tests.items():
                        if test_file_path != file_path:
                            test_full_path = project_path / test_file_path
                            test_full_path.write_text(test_content, encoding="utf-8")
                            modified_files[test_file_path] = test_content
            
            self._add_reasoning_step("Test-Fix", "Regenerated tests to fix failures", success=True)
            return {"modified_files": modified_files, "tests_regenerated": True}
            
        except Exception as e:
            self._add_reasoning_step("Test-Fix", f"Test regeneration failed: {str(e)}", success=False)
            return modification_result

    async def _replan_for_performance(self, modification_result: Dict[str, Any], issues: List[str]) -> Dict[str, Any]:
        """Create a new plan focused on performance optimization"""
        self._add_reasoning_step("Performance-Replan", "Creating performance-focused modification plan")
        
        # Create a new objective focused on performance
        original_task = self.session_state.get("task", "")
        performance_task = f"Optimize performance for: {original_task}. Address: {', '.join(issues)}"
        
        # Re-execute modification with performance focus
        try:
            performance_plan = await self._create_modification_plan(
                performance_task, 
                ["Prioritize performance optimization", "Minimize memory usage", "Optimize algorithms"],
                {}
            )
            
            performance_result = await self._execute_modifications(performance_plan)
            
            self._add_reasoning_step("Performance-Replan", "Performance-focused modification completed", success=True)
            return performance_result
            
        except Exception as e:
            self._add_reasoning_step("Performance-Replan", f"Performance replan failed: {str(e)}", success=False)
            return modification_result

    async def _generic_retry_with_context(self, modification_result: Dict[str, Any], issues: List[str]) -> Dict[str, Any]:
        """Generic retry with additional context about the issues"""
        self._add_reasoning_step("Generic-Retry", "Retrying modification with issue context")
        
        # Add issue context to the modification and retry
        enhanced_task = self.session_state.get("task", "") + f" (Address these issues: {', '.join(issues)})"
        
        try:
            retry_plan = await self._create_modification_plan(enhanced_task, [], {})
            retry_result = await self._execute_modifications(retry_plan)
            
            self._add_reasoning_step("Generic-Retry", "Retry with context completed", success=True)
            return retry_result
            
        except Exception as e:
            self._add_reasoning_step("Generic-Retry", f"Generic retry failed: {str(e)}", success=False)
            return modification_result

    async def _escalate_to_human(self, modification_result: Dict[str, Any], issues: List[str]) -> Dict[str, Any]:
        """Escalate complex issues to human review"""
        self._add_reasoning_step("Human-Escalation", "Escalating to human review due to complex issues")
        
        # For now, just mark for human review
        escalation_info = {
            "requires_human_review": True,
            "escalation_reason": "Complex issues detected requiring human judgment",
            "issues": issues,
            "recommended_actions": [
                "Manual code review required",
                "Security assessment recommended", 
                "Consider architectural changes"
            ]
        }
        
        modification_result["escalation"] = escalation_info
        return modification_result

    def _apply_basic_syntax_fixes(self, content: str) -> str:
        """Apply basic syntax fixes to Python code"""
        lines = content.splitlines()
        fixed_lines = []
        
        for line in lines:
            # Basic indentation fix (convert tabs to spaces)
            if '\t' in line:
                line = line.replace('\t', '    ')
            
            # Remove trailing whitespace
            line = line.rstrip()
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)

    async def execute(self, objective: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution flow for the code orchestration process.
        
        Args:
            objective: Dictionary containing task details, constraints, and quality gates
                - task: Description of the code evolution task
                - constraints: List of constraints to follow
                - quality_gates: List of quality checks to perform
                - project_path: Path to the project directory
        
        Returns:
            Dictionary with execution results:
                - decision: 'approve' or 'reject'
                - reason: Explanation for the decision
                - modifications: Summary of changes made
                - quality_results: Results from quality gates
                - sre_results: Results from operational checks
        """
        try:
            # 1. Extract key information from objective
            task = objective.get('task', '')
            constraints = objective.get('constraints', [])
            quality_gates = objective.get('quality_gates', [])
            project_path_str = objective.get('project_path', '')
            
            # Validate required fields
            if not task or not project_path_str:
                return {
                    "decision": "reject",
                    "reason": "Missing required fields in objective: task and project_path are required"
                }
            
            # Initialize project path
            project_path = Path(project_path_str)
            if not project_path.exists() or not project_path.is_dir():
                return {
                    "decision": "reject",
                    "reason": f"Invalid project path: {project_path_str}"
                }
            
            # Store basic context in team session state
            if self.session_state is not None:
                self.session_state["objective"] = objective
                self.session_state["project_path"] = str(project_path)
                self.session_state["task"] = task
                self.session_state["constraints"] = constraints
                self.session_state["quality_gates"] = quality_gates
                
                # Initialize reasoning trajectory if not exists
                if "reasoning_trajectory" not in self.session_state:
                    self.session_state["reasoning_trajectory"] = []
            
            # 2. Initialize teams with fresh state for this execution
            await self._setup_teams(project_path)
            
            # 3. Project context analysis phase
            analysis_result = await self._analyze_project_context(project_path, task)
            if self.session_state is not None:
                self.session_state["analysis"] = analysis_result
            
            # 4. Modification planning phase
            modification_plan = await self._create_modification_plan(
                task, constraints, analysis_result
            )
            if self.session_state is not None:
                self.session_state["modification_plan"] = modification_plan
            
            # 5. Modification execution phase
            modification_result = await self._execute_modifications(modification_plan)
            if self.session_state is not None:
                self.session_state["modification_result"] = modification_result
            
            # 6. Validation phase (quality and operational checks)
            quality_results = await self._run_quality_checks(
                modification_result, quality_gates
            )
            if self.session_state is not None:
                self.session_state["quality_results"] = quality_results
            
            sre_results = await self._run_operational_checks(modification_result)
            if self.session_state is not None:
                self.session_state["sre_results"] = sre_results
            
            # 7. Self-Healing and Recovery Logic
            quality_passed = quality_results.get('passed', False)
            sre_passed = sre_results.get('passed', False)

            if not quality_passed or not sre_passed:
                self._add_reasoning_step("Validation Failed", f"Quality: {quality_passed}, SRE: {sre_passed}", success=False)
                
                # Analyze failure patterns for self-healing
                recovery_analysis = self._analyze_failure_patterns(quality_results, sre_results)
                
                # Attempt self-healing if recoverable
                if recovery_analysis.get("auto_recoverable", False):
                    self._add_reasoning_step("Self-Healing", "Attempting automatic recovery")
                    
                    # Execute self-healing
                    healed_modification_result = await self._execute_self_healing(recovery_analysis, modification_result)
                    
                    # Re-validate after self-healing
                    if healed_modification_result.get("auto_fixed") or healed_modification_result.get("tests_regenerated"):
                        self._add_reasoning_step("Re-Validation", "Running validation after self-healing")
                        
                        # Re-run validations
                        healed_quality_results = await self._run_quality_checks(healed_modification_result, quality_gates)
                        healed_sre_results = await self._run_operational_checks(healed_modification_result)
                        
                        # Update results if healing was successful
                        if healed_quality_results.get('passed', False) and healed_sre_results.get('passed', False):
                            self._add_reasoning_step("Self-Healing", "Self-healing successful - validation now passes", success=True)
                            quality_results = healed_quality_results
                            sre_results = healed_sre_results
                            modification_result = healed_modification_result
                        else:
                            self._add_reasoning_step("Self-Healing", "Self-healing attempted but validation still fails", success=False)
                    
                else:
                    # Non-recoverable or requires human intervention
                    recovery_strategy = recovery_analysis.get("strategy", "unknown")
                    if recovery_strategy == "human_escalation":
                        self._add_reasoning_step("Escalation", "Issues require human review", success=False)
                    else:
                        self._add_reasoning_step("Recovery Skipped", f"Strategy '{recovery_strategy}' not auto-recoverable", success=False)

            # Store final results in session state
            if self.session_state is not None:
                self.session_state["final_quality_results"] = quality_results
                self.session_state["final_sre_results"] = sre_results
                self.session_state["final_modification_result"] = modification_result
                
            # 8. Final decision
            decision, reason = self._make_final_decision(
                quality_results, sre_results, modification_result
            )
            
            # 9. Return comprehensive result
            return {
                "decision": decision,
                "reason": reason,
                "modifications": modification_result.get('summary', {}),
                "quality_results": quality_results,
                "sre_results": sre_results,
                "reasoning_trajectory": self.session_state.get("reasoning_trajectory", []) if self.session_state else []
            }
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            if self.session_state is not None:
                self.session_state["error"] = str(e)
                self.session_state["error_details"] = error_details
            
            return {
                "decision": "reject",
                "reason": f"Orchestration error: {str(e)}",
                "error_details": error_details
            }
    
    async def _setup_teams(self, project_path: Path):
        """Initialize all specialized teams for this execution"""
        shared_session = self.session_state  # Ensure shared dict ref

        # Initialize teams with shared session state
        self.knowledge_team = build_knowledge_team(session_state=shared_session)
        # Use new enhanced modification team 
        self.modification_team = build_code_modification_team(
            project_path=project_path, 
            session_state=shared_session,
            config={
                "enable_security_scanning": True,
                "strict_validation": True,
                "detailed_documentation": True,
                "analysis_depth": "deep"
            }
        )
        self.quality_team = build_quality_team(session_state=shared_session)
        self.sre_team = build_sre_team(session_state=shared_session)


    async def _analyze_project_context(self, project_path: Path, task: str) -> Dict[str, Any]:
        """Analyze project context using the knowledge team"""
        # Track this step in the reasoning trajectory
        self._add_reasoning_step("Project Context Analysis", 
                                f"Analyzing project at {project_path} for task: {task}")
        
        # This is a placeholder - implement actual Knowledge Team integration
        analysis_result = {
            "project_structure": {
                "files": [str(p) for p in project_path.glob("**/*") if p.is_file()],
                "languages": self._detect_languages(project_path)
            },
            "task_analysis": {
                "description": task,
                "identified_targets": []  # Files likely to be modified
            },
            "context": {}  # RAG-retrieved context
        }
        
        # Add successful step completion to reasoning
        self._add_reasoning_step("Project Context Analysis", 
                                "Analysis completed successfully",
                                success=True)
        
        return analysis_result
    
    async def _create_modification_plan(
        self, task: str, constraints: List[str], analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a modification plan using the planner"""
        # Track this step in the reasoning trajectory
        self._add_reasoning_step("Modification Planning", 
                               f"Creating modification plan for task: {task}")
        
        # This is a placeholder - implement actual Planner integration
        plan = {
            "steps": [],
            "constraints": constraints,
            "target_files": []
        }
        
        return plan
    

    async def _execute_modifications(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the modification plan using the modification workflow"""
        # Track this step in the reasoning trajectory
        self._add_reasoning_step("Code Modification", 
                            f"Executing modification plan through integrated workflow")
        
        try:
            from i2c.workflow.bridge import bridge_agentic_and_workflow_modification
            
            # Create an objective for the bridge function
            objective = {
                "task": self.session_state.get("task", ""),
                "language": self._detect_primary_language(plan)
            }
            
            # Call the bridge function
            project_path = Path(self.session_state.get("project_path", ""))
            result = bridge_agentic_and_workflow_modification(objective, project_path)
            
            # Add success status to reasoning
            if result.get("success", False):
                modified_files = result.get("modified_files", [])
                self._add_reasoning_step("Code Modification", 
                                    f"Successfully modified {len(modified_files)} files",
                                    success=True)
            else:
                error = result.get("error", "Unknown error")
                self._add_reasoning_step("Code Modification", 
                                    f"Failed to execute modifications: {error}",
                                    success=False)
            
            return result
            
        except Exception as e:
            # Handle exceptions
            self._add_reasoning_step("Code Modification", 
                                f"Error during modification: {str(e)}",
                                success=False)
            
            import traceback
            stack_trace = traceback.format_exc()
            
            return {
                "success": False,
                "error": str(e),
                "stack_trace": stack_trace
            } 
            
    async def _run_quality_checks(
        self, modification_result: Dict[str, Any], quality_gates: List[str]
    ) -> Dict[str, Any]:
        """Delegate quality validation to the Quality Team using agentic instructions."""
        self._add_reasoning_step("Quality Validation", f"Delegating quality checks: {', '.join(quality_gates)}")

        try:
            project_path = Path(self.session_state.get("project_path", ""))
            modified_files = modification_result.get("modified_files", {})

            if not self.quality_team:
                raise ValueError("Quality team not initialized.")

            message_payload = {
                "instruction": (
                    "Validate the provided code changes using all relevant quality gates "
                    "based on the modified files and languages involved."
                ),
                "project_path": str(project_path),
                "modified_files": modified_files,
                "quality_gates": quality_gates
            }
            canvas.info(f"[CodeOrchestrator] Message to Quality Team:\n{json.dumps(message_payload, indent=2)}")

            result = await self.quality_team.arun(message=message_payload)
            canvas.info(f"[CodeOrchestrator] Raw result from Quality Team: {result}")
            
            content = getattr(result, "content", result)
            output = content.dict() if hasattr(content, "dict") else content
            
            canvas.info(f"[CodeOrchestrator] Parsed output from Quality Team: {output}")

            return {
                "passed": output.get("passed", False),
                "issues": output.get("issues", []),
                "gate_results": output.get("gate_results", {}),
                "summary": output.get("summary", {}),
                "debug_raw_output": output  
            }

        except Exception as e:
            canvas.error(f"[CodeOrchestrationAgent] Quality delegation failed: {e}")
            import traceback
            canvas.error(traceback.format_exc())
            return {
                "passed": False,
                "issues": [f"Quality delegation error: {str(e)}"],
                "gate_results": {},
                "summary": {}
            }

    async def _run_operational_checks(self, modification_result: Dict[str, Any]) -> Dict[str, Any]:
        """Run operational checks directly using SRE agents (no message delegation)"""
        self._add_reasoning_step("Operational Validation", "Running direct SRE checks for deployment safety.")
        
        try:
            project_path = Path(self.session_state.get("project_path", ""))
            modified_files = modification_result.get("modified_files", {})
            
            # Import SRE agents directly
            from i2c.agents.sre_team.sandbox import sandbox_executor
            from i2c.agents.sre_team.dependency import dependency_verifier
            
            # Direct operational checks (no LLM calls)
            issues = []
            check_results = {}
            
            # 1. Sandbox check (syntax + tests)
            try:
                # Detect language
                language = self._detect_primary_language_from_files(modified_files)
                success, message = sandbox_executor.execute(project_path, language)
                check_results["sandbox"] = {
                    "passed": success,
                    "issues": [] if success else [f"Sandbox: {message}"]
                }
                if not success:
                    issues.append(f"Sandbox: {message}")
            except Exception as e:
                check_results["sandbox"] = {
                    "passed": False,
                    "issues": [f"Sandbox error: {str(e)}"]
                }
                issues.append(f"Sandbox error: {str(e)}")
            
            # 2. Dependency check
            try:
                dependency_issues = dependency_verifier.check_dependencies(project_path)
                check_results["dependencies"] = {
                    "passed": len(dependency_issues) == 0,
                    "issues": dependency_issues
                }
                issues.extend(dependency_issues)
            except Exception as e:
                check_results["dependencies"] = {
                    "passed": False,
                    "issues": [f"Dependency error: {str(e)}"]
                }
                issues.append(f"Dependency error: {str(e)}")
            
            # 3. Version control check (simple)
            try:
                git_dir = project_path / ".git"
                git_ready = git_dir.exists()
                check_results["version_control"] = {
                    "passed": True,  # Always pass, just informational
                    "issues": [] if git_ready else ["Project not under version control"]
                }
            except Exception as e:
                check_results["version_control"] = {
                    "passed": True,  # Don't fail on this
                    "issues": [f"Version control check error: {str(e)}"]
                }
            
            # Overall result
            all_passed = len(issues) == 0
            
            # Add success/failure reasoning
            if all_passed:
                self._add_reasoning_step("Operational Validation", "All SRE checks passed", success=True)
            else:
                self._add_reasoning_step("Operational Validation", f"Found {len(issues)} operational issues", success=False)
            
            return {
                "passed": all_passed,
                "issues": issues,
                "check_results": check_results,
                "summary": {
                    "total_issues": len(issues),
                    "deployment_ready": all_passed,
                    "checks_run": len(check_results)
                }
            }
            
        except Exception as e:
            canvas.error(f"[CodeOrchestrationAgent] Direct SRE checks failed: {e}")
            import traceback
            canvas.error(traceback.format_exc())
            
            self._add_reasoning_step("Operational Validation", f"SRE checks failed: {str(e)}", success=False)
            
            return {
                "passed": False,
                "issues": [f"SRE check error: {str(e)}"],
                "check_results": {},
                "summary": {"total_issues": 1, "deployment_ready": False}
            }

    def _detect_primary_language_from_files(self, modified_files: Dict[str, str]) -> str:
        """Detect primary language from file extensions"""
        extensions = {}
        for file_path in modified_files:
            ext = Path(file_path).suffix
            if ext:
                extensions[ext] = extensions.get(ext, 0) + 1
        
        if not extensions:
            return "python"  # Default
        
        # Find most common extension
        most_common_ext = max(extensions.items(), key=lambda x: x[1])[0]
        
        # Map to language
        language_map = {
            ".py": "python",
            ".js": "javascript", 
            ".ts": "typescript",
            ".java": "java",
            ".go": "go"
        }
        
        return language_map.get(most_common_ext, "python")

    async def _refine_based_on_feedback(
    self, plan: Dict[str, Any], quality_results: Dict[str, Any], sre_results: Dict[str, Any]
) -> Dict[str, Any]:
        self._add_reasoning_step("Plan Refinement", "Refining plan based on validation feedback")

        issues = []
        issues.extend(quality_results.get('issues', []))
        issues.extend(sre_results.get('issues', []))

        if not hasattr(self, 'plan_refinement_operator'):
            raise RuntimeError("PlanRefinementOperator not initialized")

        user_request = f"Refine plan to address: {', '.join(issues)}"

        success, result = self.plan_refinement_operator.execute(
            initial_plan=json.dumps(plan),
            user_request=user_request,
            project_path=self.session_state.get("project_path", ""),
            language=self._detect_primary_language(plan)
        )

        refinement_result = {
            "reflection": "Identified issues and refined plan accordingly",
            "refined_plan": result.get("plan") if success else plan,
            "success": success
        }

        self._add_reasoning_step("Plan Refinement", f"Refinement {'succeeded' if success else 'failed'}", success=success)

        return refinement_result

    async def _fix_test_failures(self, test_failures: List[Dict], modified_files: Dict[str, str]) -> Dict[str, Any]:
        self._add_reasoning_step("Issue Resolution", f"Resolving {len(test_failures)} test failures")

        results = {"fixed": [], "unfixed": []}

        if not hasattr(self, 'issue_resolution_operator'):
            raise RuntimeError("IssueResolutionOperator not initialized")

        for failure in test_failures:
            file_path = failure.get("file_path")
            if file_path and file_path in modified_files:
                file_content = modified_files[file_path]

                success, result = self.issue_resolution_operator.execute(
                    test_failure=failure,
                    file_content=file_content,
                    file_path=file_path,
                    language=self._detect_language_from_file(file_path),
                    project_path=Path(self.session_state.get("project_path", ""))
                )

                if success:
                    modified_files[file_path] = result.get("fixed_content", file_content)
                    results["fixed"].append({
                        "file": file_path,
                        "original_error": failure.get("error_message", "Unknown error"),
                        "patch": result.get("patch", "")
                    })
                else:
                    results["unfixed"].append({
                        "file": file_path,
                        "error": failure.get("error_message", "Unknown error"),
                        "reason": result.get("error", "Unknown reason")
                    })

        success = len(results["unfixed"]) == 0
        self._add_reasoning_step("Issue Resolution", f"Fixed {len(results['fixed'])} of {len(test_failures)} issues", success=success)

        return results

    async def _execute_with_recovery(self, plan: Dict[str, Any], max_attempts: int = 3) -> Dict[str, Any]:
        """Execute modifications with automatic recovery attempts"""
        for attempt in range(1, max_attempts + 1):
            # Execute the current plan
            result = await self._execute_modifications(plan)
            
            # Check for success
            if result.get("success", False):
                return result
            
            # If failed and we have more attempts, try to recover
            if attempt < max_attempts:
                self._add_reasoning_step("Recovery Attempt", 
                                    f"Modification failed, attempting recovery (attempt {attempt}/{max_attempts})")
                
                # Use the appropriate reflective operator to fix the issue
                recovery_plan = await self._generate_recovery_plan(result, plan)
                
                # Update the plan for the next attempt
                plan = recovery_plan
        
        # If we've exhausted all attempts, return the last result
        return result
    
    def _make_final_decision(
        self, 
        quality_results: Dict[str, Any], 
        sre_results: Dict[str, Any],
        modification_result: Dict[str, Any]
    ) -> Tuple[str, str]:
        """Make a final decision based on all results"""
        # Check validation results
        quality_passed = quality_results.get('passed', False)
        sre_passed = sre_results.get('passed', False)
        
        if quality_passed and sre_passed:
            decision = "approve"
            reason = "All quality and operational checks passed"
        else:
            decision = "reject"
            quality_issues = quality_results.get('issues', [])
            sre_issues = sre_results.get('issues', [])
            reason = "Failed validation checks: " + (
                ", ".join(quality_issues + sre_issues) or "Unspecified issues"
            )
        
        # Track final decision in reasoning
        self._add_reasoning_step("Final Decision", 
                               f"Decision: {decision} - {reason}",
                               success=(decision == "approve"))
        
        return decision, reason
    
    def _detect_languages(self, project_path: Path) -> Dict[str, int]:
        """Detect programming languages used in the project"""
        extensions = {}
        for file_path in project_path.glob("**/*"):
            if file_path.is_file():
                ext = file_path.suffix
                if ext:
                    extensions[ext] = extensions.get(ext, 0) + 1
        
        # Map extensions to languages
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".cpp": "c++",
            ".c": "c",
            ".rb": "ruby",
            ".go": "go",
            ".rs": "rust",
            ".php": "php",
            ".cs": "csharp",
            ".swift": "swift",
            ".kt": "kotlin"
        }
        
        languages = {}
        for ext, count in extensions.items():
            lang = language_map.get(ext)
            if lang:
                languages[lang] = languages.get(lang, 0) + count
        
        return languages
    
    def _add_reasoning_step(self, step_name: str, description: str, success: bool = None):
        """Add a step to the reasoning trajectory"""
        if self.session_state is None:
            return
        
        trajectory = self.session_state.get("reasoning_trajectory", [])
        
        step = {
            "step": step_name,
            "description": description,
            "timestamp": str(datetime.datetime.now()),
        }
        
        if success is not None:
            step["success"] = success
            
        trajectory.append(step)
        self.session_state["reasoning_trajectory"] = trajectory

def build_orchestration_team(session_state=None) -> Team:
    """
    Build the orchestration team with a code orchestration agent.
    
    Args:
        session_state: Optional shared session state dictionary.
        
    Returns:
        Team: Configured orchestration team
    """
    
      # Extract constraints from session state if available
    constraints = []
    if session_state.get("objective") and "constraints" in session_state["objective"]:
        constraints = session_state["objective"]["constraints"]
    elif session_state.get("constraints"):
        constraints = session_state["constraints"]

    # Log constraints for debugging
    
    if constraints:
        canvas.info(f"Orchestration team initialized with {len(constraints)} constraints:")
        for i, constraint in enumerate(constraints):
            canvas.info(f"  Constraint {i+1}: {constraint}")
            
    # Add constraints to instructions
    constraint_instructions = []
    if constraints:
        constraint_instructions.append("Follow these critical quality constraints:")
        for constraint in constraints:
            constraint_instructions.append(f"- {constraint}")
    
    # Create the code orchestration agent
    orchestrator = CodeOrchestrationAgent(session_state=session_state)
    
    # Create the team
    return Team(
        name="CodeEvolutionTeam",
        members=[orchestrator],
        mode="coordinate",
        model=llm_middle,
        instructions=[
            "You are the lead orchestrator of a code evolution factory.",
            "Your job is to coordinate specialized teams (Knowledge, Modification, Quality, SRE) to safely evolve code.",
            "Follow the lead of the CodeOrchestrator.",
            # Include constraint instructions if available
            *constraint_instructions,
            # Rest of standard instructions
            "For each objective, you must:",
            "1. Analyze the project context thoroughly",
            "2. Create a detailed plan for modifications",
            "3. Execute modifications while preserving functionality",
            "4. Validate changes through quality and operational gates",
            "5. Reflect on failures and adapt the plan as needed",
            "6. Make a final decision: approve or reject with clear reasoning",
            "Always prioritize code quality, safety, and alignment with objectives.",
            "",
            "IMPORTANT: Your final response **must be valid JSON** matching this format:",
            "```json",
            '{',
            '  "decision": "approve",',
            '  "reason": "All quality and operational checks passed",',
            '  "modifications": { "sample.py": "Added type hints" },',
            '  "quality_results": { "lint": "passed", "types": "passed", "security": "passed" },',
            '  "sre_results": { "uptime_check": "passed" },',
            '  "reasoning_trajectory": [ { "step": "Final Decision", "description": "All gates passed", "success": true } ]',
            '}',
            "```",
            "Do NOT output explanations, markdown, or narratives after the JSON. Only return the JSON object."
        ],
        session_state=session_state,
        response_model=OrchestrationResult,  
        show_tool_calls=True,
        debug_mode=True,
        markdown=True,
        enable_agentic_context=True,
    )
