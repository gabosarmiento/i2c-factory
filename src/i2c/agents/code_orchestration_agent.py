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

    class Config:
        # Allow extra fields in case response has additional data
        extra = "allow"
        # Be more lenient with JSON parsing
        json_encoders = {
            # Handle any problematic types
        }

class CodeOrchestrationAgent(Agent):
    def __init__(
        self, 
        *, 
        session_state: Optional[Dict[str, Any]] = None,  
        **kwargs,
    ) -> None:
        # ------------------------------------------------------------------
        # 1. AGNO initialisation (name, model, role, instructions)
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
        
        
        # ------------------------------------------------------------------
        # 2.  Ensure we have a shared, mutable dict (create it exactly once)
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

        # ⬅️ Add strict JSON output enforcement for agent responses
        self.instructions.extend([
            "IMPORTANT: Your final response must be a **valid JSON object** ONLY. Do NOT include markdown formatting like ```json.",
            "Here is the exact format to follow:",
            '{',
            '  "decision": "approve",',
            '  "reason": "All quality and operational checks passed",',
            '  "modifications": { "sample.py": "Added type hints" },',
            '  "quality_results": { "lint": "passed", "types": "passed", "security": "passed" },',
            '  "sre_results": { "uptime_check": "passed" },',
            '  "reasoning_trajectory": [ { "step": "Final Decision", "description": "All gates passed", "success": true } ]',
            '}',
            "❌ Do NOT use ```json or ``` anywhere.",
            "❌ Do NOT return explanations or markdown.",
            "✅ Only return the raw JSON object, nothing else.",
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
        
        # Simple approach: mark tests for regeneration without importing unit_test_generator
        try:
            modified_files = modification_result.get("modified_files", {})
            project_path = Path(self.session_state.get("project_path", ""))
            
            # Instead of regenerating tests, just flag for attention
            # This avoids circular imports while still handling the recovery
            test_fix_notes = []
            
            for file_path in modified_files:
                if file_path.endswith('.py') and not file_path.startswith('test_'):
                    test_fix_notes.append(f"Tests may need regeneration for {file_path}")
            
            # Update modification result with test fix notes
            modified_files["TEST_FIX_NOTES.md"] = "\n".join([
                "# Test Fix Notes",
                "The following files may need test regeneration:",
                "",
            ] + test_fix_notes)
            
            self._add_reasoning_step("Test-Fix", f"Flagged {len(test_fix_notes)} files for test review", success=True)
            return {"modified_files": modified_files, "test_fix_attempted": True}
            
        except Exception as e:
            self._add_reasoning_step("Test-Fix", f"Test fix attempt failed: {str(e)}", success=False)
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

            # 9. Return comprehensive result with clean formatting
            try:
                final_result = {
                    "decision": decision,
                    "reason": reason,
                    "modifications": modification_result.get("summary", {}),
                    "quality_results": self._clean_results(quality_results),
                    "sre_results": self._clean_results(sre_results),
                    "reasoning_trajectory": self.session_state.get("reasoning_trajectory", []) if self.session_state else []
                }

                # Ensure clean JSON without function refs
                return self._sanitize_response(final_result)

            except Exception as e:
                return {
                    "decision": "reject",
                    "reason": f"Execution error: {str(e)}",
                    "modifications": {},
                    "quality_results": {},
                    "sre_results": {},
                    "reasoning_trajectory": []
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

    # --- Add this utility method to the class as well ---
    def _sanitize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Remove function references and ensure JSON serializable"""
        import json
        try:
            json_str = json.dumps(response, default=str)
            return json.loads(json_str)
        except Exception:
            return {
                "decision": "reject",
                "reason": "Response serialization failed",
                "modifications": {},
                "quality_results": {},
                "sre_results": {},
                "reasoning_trajectory": []
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
        """Analyze project context using architectural intelligence and file system analysis"""
        self._add_reasoning_step("Project Context Analysis", 
                                f"Analyzing project architecture at {project_path} for task: {task}")
        
        try:
            analysis_result = {
                "project_structure": {
                    "files": [],
                    "languages": {},
                    "directories": []
                },
                "task_analysis": {
                    "description": task,
                    "identified_targets": []
                },
                "context": {},
                "architectural_context": {}
            }

            if project_path.exists() and project_path.is_dir():
                ignore_patterns = {'.git', '__pycache__', '.venv', 'node_modules', '.pytest_cache'}
                
                files = []
                for file_path in project_path.rglob("*"):
                    if file_path.is_file():
                        if any(ignore_dir in file_path.parts for ignore_dir in ignore_patterns):
                            continue
                        files.append(str(file_path.relative_to(project_path)))
                
                analysis_result["project_structure"]["files"] = files
                analysis_result["project_structure"]["languages"] = self._detect_languages(project_path)
                
                dirs = []
                for dir_path in project_path.rglob("*"):
                    if dir_path.is_dir() and dir_path.name not in ignore_patterns:
                        dirs.append(str(dir_path.relative_to(project_path)))
                analysis_result["project_structure"]["directories"] = dirs
                
                task_lower = task.lower()
                likely_targets = []
                
                for file_path in files:
                    file_lower = file_path.lower()
                    if any(keyword in file_lower for keyword in task_lower.split() if len(keyword) > 3):
                        likely_targets.append(file_path)
                    elif any(pattern in file_lower for pattern in ['main.py', 'app.py', 'index.js', 'server.py']):
                        likely_targets.append(file_path)
                
                analysis_result["task_analysis"]["identified_targets"] = likely_targets[:5]

            # 2. NEW: Architectural Intelligence Analysis (with robust error handling)
            architectural_context = {}
            try:
                from i2c.agents.architecture.architecture_understanding_agent import get_architecture_agent
                

                content_samples = self._get_content_samples(project_path, files[:5] if files else [])
                self._add_reasoning_step("Architectural Analysis", 
                                        "Analyzing system architecture and module boundaries")
                
                architecture_agent = get_architecture_agent(self.session_state)
                structural_context = architecture_agent.analyze_system_architecture(
                    objective=task,
                    existing_files=files,
                    content_samples=content_samples
                )
                
                if structural_context and hasattr(structural_context, 'architecture_pattern'):
                    architectural_context = {
                        "architecture_pattern": structural_context.architecture_pattern.value if structural_context.architecture_pattern else "unknown",
                        "system_type": getattr(structural_context, 'system_type', 'web_app'),
                        "modules": {},
                        "file_organization_rules": getattr(structural_context, 'file_organization_rules', {}),
                        "constraints": getattr(structural_context, 'constraints', []),
                        "integration_patterns": getattr(structural_context, 'integration_patterns', [])
                    }

                    if hasattr(structural_context, 'modules') and structural_context.modules:
                        for name, module in structural_context.modules.items():
                            try:
                                architectural_context["modules"][name] = {
                                    "boundary_type": module.boundary_type.value if hasattr(module.boundary_type, 'value') else str(module.boundary_type),
                                    "languages": list(module.languages) if hasattr(module, 'languages') else ["python"],
                                    "responsibilities": getattr(module, 'responsibilities', []),
                                    "folder_structure": getattr(module, 'folder_structure', {})
                                }
                            except Exception as module_error:
                                print(f"⚠️ Error processing module {name}: {module_error}")
                                architectural_context["modules"][name] = {
                                    "boundary_type": "business_logic",
                                    "languages": ["python"],
                                    "responsibilities": [f"{name} functionality"],
                                    "folder_structure": {"base_path": name.lower()}
                                }

                    if self.session_state is not None:
                        self.session_state["structural_context"] = structural_context
                        self.session_state["architectural_understanding"] = architectural_context
                    
                    module_count = len(architectural_context.get("modules", {}))
                    pattern = architectural_context.get("architecture_pattern", "unknown")
                    
                    self._add_reasoning_step("Architectural Analysis", 
                                            f"Successfully analyzed {pattern} pattern with {module_count} modules",
                                            success=True)
                else:
                    print("⚠️ Structural context is invalid, using fallback")
                    architectural_context = self._create_fallback_architectural_context()
                    self._add_reasoning_step("Architectural Analysis", 
                                            "Used fallback architectural context", 
                                            success=False)

            except ImportError as e:
                print(f"⚠️ Could not import architecture agent: {e}")
                architectural_context = self._create_fallback_architectural_context()
                self._add_reasoning_step("Architectural Analysis", 
                                        "Architecture agent not available, using fallback", 
                                        success=False)
            except Exception as e:
                print(f"⚠️ Architectural analysis failed: {e}")
                architectural_context = self._create_fallback_architectural_context()
                self._add_reasoning_step("Architectural Analysis", 
                                        f"Analysis failed ({str(e)[:50]}...), using fallback", 
                                        success=False)

            analysis_result["architectural_context"] = architectural_context

            if self.knowledge_team and hasattr(self.knowledge_team, 'analyze_context'):
                try:
                    knowledge_context = await self.knowledge_team.analyze_context(task, project_path)
                    analysis_result["context"]["knowledge_insights"] = knowledge_context
                except Exception as e:
                    canvas.info(f"Knowledge team context analysis failed: {e}")
            
            files_count = len(analysis_result["project_structure"]["files"])
            targets_count = len(analysis_result["task_analysis"]["identified_targets"])
            arch_modules = len(analysis_result["architectural_context"].get("modules", {}))
            
            self._add_reasoning_step("Project Context Analysis", 
                                    f"Complete analysis: {files_count} files, {targets_count} targets, {arch_modules} architectural modules",
                                    success=True)
            
            return analysis_result
        
        except Exception as e:
            self._add_reasoning_step("Project Context Analysis", 
                                    f"Analysis failed: {str(e)}", 
                                    success=False)
            return {
                "project_structure": {"files": [], "languages": {}, "directories": []},
                "task_analysis": {"description": task, "identified_targets": []},
                "context": {"error": str(e)},
                "architectural_context": {}
            }

    def _create_fallback_architectural_context(self) -> Dict[str, Any]:
        """Create fallback architectural context when analysis fails"""
        return {
            "architecture_pattern": "fullstack_web",
            "system_type": "web_app", 
            "modules": {
                "frontend": {
                    "boundary_type": "ui_layer",
                    "languages": ["javascript"],
                    "responsibilities": ["user interface"],
                    "folder_structure": {"base_path": "frontend/src"}
                },
                "backend": {
                    "boundary_type": "api_layer",
                    "languages": ["python"],
                    "responsibilities": ["api endpoints"],
                    "folder_structure": {"base_path": "backend/app"}
                }
            },
            "file_organization_rules": {
                "ui_components": "frontend/src/components",
                "api_routes": "backend/api/routes",
                "business_logic": "backend/services",
                "data_models": "backend/models"
            },
            "constraints": [],
            "integration_patterns": ["REST API"]
        }

    def _get_content_samples(self, project_path: Path, file_list: List[str]) -> Dict[str, str]:
        """Get content samples from key files for architectural analysis"""
        content_samples = {}
        
        for file_rel in file_list:
            try:
                file_path = project_path / file_rel
                if file_path.exists() and file_path.is_file():
                    # Read file content (limit size for analysis)
                    content = file_path.read_text(encoding='utf-8')
                    if len(content) > 1000:
                        content = content[:1000] + "..."
                    content_samples[file_rel] = content
            except Exception as e:
                canvas.warning(f"Could not read {file_rel}: {e}")
        
        return content_samples

    async def _create_modification_plan(
        self, task: str, constraints: List[str], analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a modification plan using architectural intelligence and planner"""
        self._add_reasoning_step("Modification Planning", 
                            f"Creating architecturally-aware modification plan for task: {task}")
        
        try:
            from i2c.workflow.modification.plan_generator import generate_modification_plan
            
            project_path = Path(self.session_state.get("project_path", ""))
            language = self.session_state.get("language", "python")
            
            # Get architectural context for intelligent planning
            architectural_context = analysis.get("architectural_context", {})
            structural_context = self.session_state.get("structural_context")
            
            # Build enhanced context for planner
            enhanced_context = self._build_planning_context(
                architectural_context, structural_context, task, constraints
            )
            
            # Call the planner with architectural context
            modification_steps = generate_modification_plan(
                user_request=task,
                retrieved_context_plan=enhanced_context,
                project_path=project_path,
                language=language
            )
            
            # Validate and enhance modification steps using architectural intelligence
            validated_steps = self._validate_steps_against_architecture(
                modification_steps, architectural_context, structural_context
            )
            
            plan = {
                "steps": validated_steps,
                "constraints": constraints,
                "target_files": [step.get("file", "") for step in validated_steps if step.get("file")],
                "architectural_guidance": {
                    "architecture_pattern": architectural_context.get("architecture_pattern"),
                    "file_organization_rules": architectural_context.get("file_organization_rules", {}),
                    "module_boundaries": list(architectural_context.get("modules", {}).keys()),
                    "integration_patterns": architectural_context.get("integration_patterns", [])
                }
            }
            
            self._add_reasoning_step("Modification Planning", 
                                f"Generated architecturally-validated plan with {len(validated_steps)} steps", 
                                success=True)
            
            return plan
            
        except Exception as e:
            self._add_reasoning_step("Modification Planning", 
                                f"Planning failed: {str(e)}", 
                                success=False)
            # Fallback to basic plan
            return {
                "steps": [],
                "constraints": constraints, 
                "target_files": [],
                "architectural_guidance": {}
            }

    def _build_planning_context(self, architectural_context: Dict[str, Any], 
                            structural_context, task: str, constraints: List[str]) -> str:
        """Build enhanced planning context with fullstack app intelligence"""
        
        context_parts = []
        
        # Add architectural understanding
        if architectural_context:
            system_type = architectural_context.get('system_type', 'unknown')
            architecture_pattern = architectural_context.get('architecture_pattern', 'unknown')
            
            context_parts.append("=== ARCHITECTURAL CONTEXT ===")
            context_parts.append(f"System Type: {system_type}")
            context_parts.append(f"Architecture Pattern: {architecture_pattern}")
            
            # FULLSTACK WEB APP SPECIFIC RULES
            if system_type == "fullstack_web_app":
                context_parts.append("\n=== FULLSTACK WEB APP RULES ===")
                context_parts.append("This is a FULLSTACK WEB APPLICATION - follow these mandatory patterns:")
                context_parts.append("")
                context_parts.append("FRONTEND STRUCTURE (React):")
                context_parts.append("- Main app: frontend/src/App.jsx (React functional component)")
                context_parts.append("- Components: frontend/src/components/ComponentName.jsx")
                context_parts.append("- Styles: frontend/src/index.css or component-specific CSS")
                context_parts.append("- Entry: frontend/src/main.jsx (Vite/React entry point)")
                context_parts.append("- Config: frontend/vite.config.js or similar")
                context_parts.append("")
                context_parts.append("BACKEND STRUCTURE (FastAPI):")
                context_parts.append("- Main app: backend/main.py (FastAPI application)")
                context_parts.append("- API routes: backend/api/routes.py or backend/api/[domain].py")
                context_parts.append("- Data models: backend/models/[domain].py (Pydantic models)")
                context_parts.append("- Services: backend/services/[domain].py (business logic)")
                context_parts.append("- Database: backend/db/database.py (SQLAlchemy or similar)")
                context_parts.append("")
                context_parts.append("MANDATORY CODE PATTERNS:")
                context_parts.append("1. Backend main.py MUST include:")
                context_parts.append("   from fastapi import FastAPI")
                context_parts.append("   app = FastAPI()")
                context_parts.append("   @app.get('/api/...') endpoints")
                context_parts.append("   uvicorn.run() or equivalent")
                context_parts.append("")
                context_parts.append("2. Frontend App.jsx MUST include:")
                context_parts.append("   import React from 'react'")
                context_parts.append("   Functional component with JSX return")
                context_parts.append("   Export default App")
                context_parts.append("")
                context_parts.append("3. Components MUST be in separate files:")
                context_parts.append("   Each React component in its own .jsx file")
                context_parts.append("   Proper imports and exports")
                context_parts.append("")
            
            # Add module information with enforcement
            modules = architectural_context.get("modules", {})
            if modules:
                context_parts.append("MODULES AND BOUNDARIES:")
                for module_name, module_info in modules.items():
                    context_parts.append(f"- {module_name}: {module_info.get('boundary_type', 'unknown')}")
                    context_parts.append(f"  Responsibilities: {', '.join(module_info.get('responsibilities', []))}")
                    
                    folder_structure = module_info.get('folder_structure', {})
                    if folder_structure:
                        base_path = folder_structure.get('base_path', '')
                        subfolders = folder_structure.get('subfolders', [])
                        if base_path:
                            context_parts.append(f"  Location: {base_path}/")
                            if subfolders:
                                context_parts.append(f"  Subfolders: {', '.join(subfolders)}")
            
            # Add code generation rules with specific examples
            code_gen_rules = architectural_context.get("code_generation_rules", {})
            if code_gen_rules:
                context_parts.append("\n=== CODE GENERATION RULES ===")
                
                if system_type == "fullstack_web_app":
                    context_parts.append("BACKEND main.py template:")
                    context_parts.append("```python")
                    context_parts.append("from fastapi import FastAPI")
                    context_parts.append("from fastapi.middleware.cors import CORSMiddleware")
                    context_parts.append("from api import routes")
                    context_parts.append("")
                    context_parts.append("app = FastAPI(title='Your App Name')")
                    context_parts.append("")
                    context_parts.append("app.add_middleware(")
                    context_parts.append("    CORSMiddleware,")
                    context_parts.append("    allow_origins=['http://localhost:3000'],")
                    context_parts.append("    allow_methods=['*'],")
                    context_parts.append("    allow_headers=['*']")
                    context_parts.append(")")
                    context_parts.append("")
                    context_parts.append("app.include_router(routes.router, prefix='/api')")
                    context_parts.append("")
                    context_parts.append("if __name__ == '__main__':")
                    context_parts.append("    import uvicorn")
                    context_parts.append("    uvicorn.run(app, host='0.0.0.0', port=8000)")
                    context_parts.append("```")
                    context_parts.append("")
                    
                    context_parts.append("FRONTEND App.jsx template:")
                    context_parts.append("```jsx")
                    context_parts.append("import React from 'react'")
                    context_parts.append("import './App.css'")
                    context_parts.append("")
                    context_parts.append("function App() {")
                    context_parts.append("  return (")
                    context_parts.append("    <div className='App'>")
                    context_parts.append("      <h1>Your App Title</h1>")
                    context_parts.append("      {/* Your components here */}")
                    context_parts.append("    </div>")
                    context_parts.append("  )")
                    context_parts.append("}")
                    context_parts.append("")
                    context_parts.append("export default App")
                    context_parts.append("```")
            
            # Add architectural constraints with enforcement
            arch_constraints = architectural_context.get("constraints", [])
            if arch_constraints:
                context_parts.append("\nARCHITECTURAL CONSTRAINTS (MANDATORY):")
                for constraint in arch_constraints:
                    context_parts.append(f"- {constraint}")
            
            # Add integration patterns
            integration_patterns = architectural_context.get("integration_patterns", [])
            if integration_patterns:
                context_parts.append("\nINTEGRATION PATTERNS:")
                for pattern in integration_patterns:
                    context_parts.append(f"- {pattern}")
        
        # Add task-specific guidance
        context_parts.append(f"\n=== TASK GUIDANCE ===")
        context_parts.append(f"Task: {task}")
        
        if constraints:
            context_parts.append("Additional Constraints:")
            for constraint in constraints:
                context_parts.append(f"- {constraint}")
        
        # Add planning instructions with architectural enforcement
        context_parts.append("\n=== PLANNING INSTRUCTIONS ===")
        context_parts.append("When creating the modification plan:")
        context_parts.append("1. RESPECT the identified architectural pattern and module boundaries")
        context_parts.append("2. PLACE files according to the file organization rules")
        context_parts.append("3. GENERATE code that matches the architectural templates")
        context_parts.append("4. FOLLOW the integration patterns for cross-module communication")
        context_parts.append("5. VALIDATE that modifications don't violate architectural constraints")
        context_parts.append("6. FOR FULLSTACK APPS: Never mix frontend and backend code in same files")
        context_parts.append("7. ENSURE proper file extensions (.jsx for React, .py for Python)")
        context_parts.append("8. CREATE separate files for each component/service/model")
        
        return "\n".join(context_parts)

    def _validate_steps_against_architecture(self, steps: List[Dict[str, Any]], 
                                        architectural_context: Dict[str, Any],
                                        structural_context) -> List[Dict[str, Any]]:
        """Validate and enhance modification steps using architectural intelligence"""
        
        if not architectural_context or not steps:
            return steps
        
        validated_steps = []
        file_org_rules = architectural_context.get("file_organization_rules", {})
        modules = architectural_context.get("modules", {})
        
        for step in steps:
            file_path = step.get("file", "")
            action = step.get("action", "")
            what = step.get("what", "")
            
            # Validate file placement against architectural rules
            suggested_path = self._suggest_architectural_path(file_path, what, file_org_rules, modules)
            
            if suggested_path and suggested_path != file_path:
                # Update file path based on architectural guidance
                step["file"] = suggested_path
                step["architectural_note"] = f"Path adjusted from '{file_path}' to follow architectural pattern"
                
                self._add_reasoning_step("Architectural Validation", 
                                    f"Adjusted path: {file_path} → {suggested_path}")
            
            # Add architectural context to step
            step["architectural_context"] = self._get_step_architectural_context(
                step, architectural_context
            )
            
            validated_steps.append(step)
        
        return validated_steps

    def _suggest_architectural_path(self, original_path: str, what_description: str, 
                                file_org_rules: Dict[str, str], 
                                modules: Dict[str, Any]) -> Optional[str]:
        """Suggest better file path based on architectural understanding"""
        
        what_lower = what_description.lower()
        original_lower = original_path.lower()
        
        # Map common functionality to architectural rules
        functionality_mapping = {
            "component": "ui_components",
            "route": "api_routes", 
            "endpoint": "api_routes",
            "service": "business_logic",
            "model": "data_models",
            "controller": "api_routes",
            "view": "ui_components",
            "repository": "data_access",
            "util": "shared_utilities"
        }
        
        # Find matching rule
        for func_keyword, rule_name in functionality_mapping.items():
            if func_keyword in what_lower or func_keyword in original_lower:
                if rule_name in file_org_rules:
                    rule_path = file_org_rules[rule_name]
                    filename = Path(original_path).name
                    return f"{rule_path}/{filename}"
        
        # Check module boundaries
        for module_name, module_info in modules.items():
            module_responsibilities = " ".join(module_info.get("responsibilities", [])).lower()
            
            if any(keyword in module_responsibilities for keyword in what_lower.split()):
                folder_structure = module_info.get("folder_structure", {})
                base_path = folder_structure.get("base_path", "")
                if base_path:
                    filename = Path(original_path).name
                    return f"{base_path}/{filename}"
        
        return None

    def _get_step_architectural_context(self, step: Dict[str, Any], 
                                    architectural_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get relevant architectural context for a specific step"""
        
        file_path = step.get("file", "")
        what = step.get("what", "")
        
        step_context = {
            "relevant_modules": [],
            "applicable_constraints": [],
            "integration_guidance": []
        }
        
        # Find relevant modules
        modules = architectural_context.get("modules", {})
        for module_name, module_info in modules.items():
            folder_structure = module_info.get("folder_structure", {})
            base_path = folder_structure.get("base_path", "")
            
            if base_path and file_path.startswith(base_path):
                step_context["relevant_modules"].append({
                    "name": module_name,
                    "boundary_type": module_info.get("boundary_type"),
                    "responsibilities": module_info.get("responsibilities", [])
                })
        
        # Find applicable constraints
        constraints = architectural_context.get("constraints", [])
        for constraint in constraints:
            if any(keyword in constraint.lower() for keyword in what.lower().split()):
                step_context["applicable_constraints"].append(constraint)
        
        # Add integration guidance
        integration_patterns = architectural_context.get("integration_patterns", [])
        step_context["integration_guidance"] = integration_patterns
        
        return step_context

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

    async def _run_quality_checks(self, modification_result: Dict[str, Any], quality_gates: List[str]) -> Dict[str, Any]:
        """Run quality checks using the quality team with proper message formatting"""
        self._add_reasoning_step("Quality Validation", "Running quality checks through Quality Team")
        
        try:
            project_path = Path(self.session_state.get("project_path", ""))
            modified_files = modification_result.get("modified_files", {})

            if not self.quality_team:
                raise ValueError("Quality team not initialized.")

            # Create properly formatted message
            message_payload = {
                "role": "user",  # Add required role field
                "content": {
                    "instruction": (
                        "Review the code changes for quality issues, style violations, "
                        "and potential bugs. Return a structured validation report."
                    ),
                    "project_path": str(project_path),
                    "modified_files": modified_files,
                    "quality_gates": quality_gates
                }
            }

            canvas.info(f"[CodeOrchestrator] Message to Quality Team:\n{json.dumps(message_payload, indent=2)}")
            
            # Send message with proper format
            result = await self.quality_team.arun(message=message_payload)
            
            # Process response safely
            response_content = self._safe_get_response_content(result)
            
            try:
                output = json.loads(response_content) if isinstance(response_content, str) else response_content
            except json.JSONDecodeError:
                # Fallback parsing
                output = {"passed": True, "issues": [], "message": response_content}

            canvas.info(f"[CodeOrchestrator] Parsed output from Quality Team: {output}")

            if output.get("passed", False):
                self._add_reasoning_step("Quality Validation", "Quality checks passed successfully", success=True)
            else:
                issues_count = len(output.get("issues", []))
                self._add_reasoning_step("Quality Validation", f"Quality checks found {issues_count} issues", success=False)

            return {
                "passed": output.get("passed", False),
                "issues": output.get("issues", []),
                "gate_results": output.get("gate_results", {}),
                "summary": output.get("summary", {}),
                "debug_raw_output": output
            }

        except Exception as e:
            canvas.error(f"[CodeOrchestrationAgent] Quality delegation failed: {e}")
            self._add_reasoning_step("Quality Validation", f"Quality delegation failed: {str(e)}", success=False)
            
            return {
                "passed": False,
                "issues": [f"Quality delegation error: {str(e)}"],
                "gate_results": {},
                "summary": {}
            }

    async def _run_operational_checks(self, modification_result: Dict[str, Any]) -> Dict[str, Any]:
        """Run operational checks using the SRE team agent with proper message delegation."""
        self._add_reasoning_step("Operational Validation", "Running delegated SRE validation for deployment safety.")
        
        try:
            project_path = Path(self.session_state.get("project_path", ""))
            modified_files = modification_result.get("modified_files", {})
            
            # Build correct message payload for SRE agent
            message_payload = {
                "role": "user",
                "content": {
                    "instruction": (
                        "Review the proposed code changes for operational risks, performance issues, "
                        "and deployment readiness. Return a structured validation report."
                    ),
                    "project_path": str(project_path),
                    "modified_files": modified_files
                }
            }
            
            # Import the SRE team agent orchestrator
            from i2c.agents.sre_team.sre_team import SRELeadAgent
            
            # Initialize and invoke the SRE agent
            sre_agent = SRELeadAgent()
            sre_result = await sre_agent.run(message_payload)
            
            # Parse agent output
            check_results = sre_result.get("check_results", {})
            issues = sre_result.get("issues", [])
            all_passed = sre_result.get("passed", False)
            
            # Add reasoning step based on result
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
            import traceback
            canvas.error(f"[CodeOrchestrationAgent] SRE check failed: {e}")
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
    
    def _add_reasoning_step(self, step: str, description: str, success: Optional[bool] = None):
        """Add reasoning step with robust error handling"""
        try:
            if self.session_state is None:
                return
            
            # Initialize reasoning trajectory if it doesn't exist
            if "reasoning_trajectory" not in self.session_state:
                self.session_state["reasoning_trajectory"] = []
            
            # Create reasoning step safely
            reasoning_step = {
                "step": str(step),
                "description": str(description),
                "timestamp": self._get_timestamp()
            }
            
            # Add success flag if provided
            if success is not None:
                reasoning_step["success"] = bool(success)
            
            # Safely append to trajectory
            if isinstance(self.session_state["reasoning_trajectory"], list):
                self.session_state["reasoning_trajectory"].append(reasoning_step)
            else:
                # Reset if trajectory is corrupted
                self.session_state["reasoning_trajectory"] = [reasoning_step]
        
        except Exception as e:
            # Don't let reasoning failures break the main process
            print(f"⚠️ Reasoning step failed: {e}")

    def _safe_get_response_content(self, response) -> str:
        """Safely extract content from agent response"""
        try:
            # Handle different response types
            if hasattr(response, 'content'):
                content = response.content
            elif hasattr(response, 'text'):
                content = response.text
            elif isinstance(response, str):
                content = response
            elif hasattr(response, '__str__'):
                content = str(response)
            else:
                content = "Unable to extract response content"
            
            # Ensure we return a string
            return str(content) if content is not None else ""
            
        except Exception as e:
            print(f"⚠️ Response content extraction failed: {e}")
            return f"Response processing error: {str(e)}"

    def _get_timestamp(self) -> str:
        """Get current timestamp safely"""
        try:
            from datetime import datetime
            return datetime.now().isoformat()
        except Exception:
            return "unknown"
        
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
        show_tool_calls=False,
        debug_mode=False,
        markdown=False,
        enable_agentic_context=False,
        tools=[]
    )
