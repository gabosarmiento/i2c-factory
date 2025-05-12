from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json
import asyncio
import datetime
from builtins import llm_middle
from agno.agent import Agent
from agno.team import Team

# Import necessary team builders
from i2c.agents.modification_team.code_modification_manager import build_code_modification_team
from i2c.agents.quality_team.quality_team import build_quality_team
from i2c.agents.sre_team.sre_team import build_sre_team
from i2c.agents.knowledge.knowledge_team import build_knowledge_team
from i2c.agents.reflective.plan_refinement_operator import PlanRefinementOperator


class CodeOrchestrationAgent(Agent):
    def __init__(self, **kwargs):
        super().__init__(
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

        if self.team_session_state is None:
            self.team_session_state = {}

        self._initialize_teams()
        self._initialize_reflective_operators()

    def _initialize_teams(self):
        self.knowledge_team = None
        self.modification_team = None
        self.quality_team = None
        self.sre_team = None

    def _initialize_reflective_operators(self):
        self.plan_refinement_operator = None
       
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
            if self.team_session_state is not None:
                self.team_session_state["objective"] = objective
                self.team_session_state["project_path"] = str(project_path)
                self.team_session_state["task"] = task
                self.team_session_state["constraints"] = constraints
                self.team_session_state["quality_gates"] = quality_gates
                
                # Initialize reasoning trajectory if not exists
                if "reasoning_trajectory" not in self.team_session_state:
                    self.team_session_state["reasoning_trajectory"] = []
            
            # 2. Initialize teams with fresh state for this execution
            await self._setup_teams(project_path)
            
            # 3. Project context analysis phase
            analysis_result = await self._analyze_project_context(project_path, task)
            if self.team_session_state is not None:
                self.team_session_state["analysis"] = analysis_result
            
            # 4. Modification planning phase
            modification_plan = await self._create_modification_plan(
                task, constraints, analysis_result
            )
            if self.team_session_state is not None:
                self.team_session_state["modification_plan"] = modification_plan
            
            # 5. Modification execution phase
            modification_result = await self._execute_modifications(modification_plan)
            if self.team_session_state is not None:
                self.team_session_state["modification_result"] = modification_result
            
            # 6. Validation phase (quality and operational checks)
            quality_results = await self._run_quality_checks(
                modification_result, quality_gates
            )
            if self.team_session_state is not None:
                self.team_session_state["quality_results"] = quality_results
            
            sre_results = await self._run_operational_checks(modification_result)
            if self.team_session_state is not None:
                self.team_session_state["sre_results"] = sre_results
            
            # 7. Reflection and refinement if needed
            if not quality_results.get('passed', False) or not sre_results.get('passed', False):
                # Refinement needed - reflect and adapt
                refinement_result = await self._refine_based_on_feedback(
                    modification_plan, quality_results, sre_results
                )
                if self.team_session_state is not None:
                    self.team_session_state["refinement_result"] = refinement_result
                
                # Re-execute with refined plan
                refined_modification_result = await self._execute_modifications(
                    refinement_result.get('refined_plan', {})
                )
                if self.team_session_state is not None:
                    self.team_session_state["refined_modification_result"] = refined_modification_result
                
                # Re-validate
                refined_quality_results = await self._run_quality_checks(
                    refined_modification_result, quality_gates
                )
                if self.team_session_state is not None:
                    self.team_session_state["refined_quality_results"] = refined_quality_results
                
                refined_sre_results = await self._run_operational_checks(
                    refined_modification_result
                )
                if self.team_session_state is not None:
                    self.team_session_state["refined_sre_results"] = refined_sre_results
                
                # Use refined results for final decision
                quality_results = refined_quality_results
                sre_results = refined_sre_results
                modification_result = refined_modification_result
            
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
                "reasoning_trajectory": self.team_session_state.get("reasoning_trajectory", []) if self.team_session_state else []
            }
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            if self.team_session_state is not None:
                self.team_session_state["error"] = str(e)
                self.team_session_state["error_details"] = error_details
            
            return {
                "decision": "reject",
                "reason": f"Orchestration error: {str(e)}",
                "error_details": error_details
            }
    
    async def _setup_teams(self, project_path: Path):
        """Initialize all specialized teams for this execution"""
        shared_session = self.team_session_state  # Ensure shared dict ref

        # Initialize teams with shared session state
        self.knowledge_team = build_knowledge_team(session_state=shared_session)
        self.modification_team = build_code_modification_team(project_path=project_path, session_state=shared_session)
        self.quality_team = build_quality_team(session_state=shared_session)
        self.sre_team = build_sre_team(session_state=shared_session)

        # Initialize reflective operators from session
        budget_manager = shared_session.get("budget_manager")
        rag_table = shared_session.get("rag_table")
        embed_model = shared_session.get("embed_model")

        self.plan_refinement_operator = PlanRefinementOperator(
            budget_manager=budget_manager,
            rag_table=rag_table,
            embed_model=embed_model
        )

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
        """Execute the modification plan using the modification team"""
        # Track this step in the reasoning trajectory
        self._add_reasoning_step("Code Modification", 
                            f"Executing {len(plan.get('steps', []))} modification steps")
        
        results = {
            "success": True,
            "modified_files": [],
            "patches": {},
            "summary": {}
        }
        
        try:
            # Execute each modification step using the modification team
            for step in plan.get('steps', []):
                # Get context for this modification
                context = ""
                if self.team_session_state is not None:
                    analysis = self.team_session_state.get("analysis", {})
                    context = analysis.get("context", {}).get(step.get("file", ""), "")
                
                # Prepare the request in the format expected by the modification team
                request = {
                    "modification_step": step,
                    "project_path": self.team_session_state.get("project_path", ""),
                    "retrieved_context": context
                }
                
                # Execute the modification
                response = await self.modification_team.apredict(json.dumps(request))
                
                # Parse the response
                try:
                    result = json.loads(response)
                    
                    # Track the modified file
                    file_path = result.get("file_path", step.get("file", "unknown"))
                    results["modified_files"].append(file_path)
                    
                    # Store the patch
                    results["patches"][file_path] = result.get("unified_diff", "")
                    
                    # Store the documentation
                    results["summary"][file_path] = result.get("documentation", "")
                    
                    # Log success
                    self._add_reasoning_step("Code Modification", 
                                        f"Successfully modified {file_path}",
                                        success=True)
                except json.JSONDecodeError:
                    # Handle case where response is not valid JSON
                    self._add_reasoning_step("Code Modification", 
                                        f"Failed to parse modification result for step: {step}",
                                        success=False)
                    results["success"] = False
        except Exception as e:
            # Handle exceptions
            self._add_reasoning_step("Code Modification", 
                                f"Error during modification: {str(e)}",
                                success=False)
            results["success"] = False
            results["error"] = str(e)
        
        return results
    
    async def _run_quality_checks(
        self, modification_result: Dict[str, Any], quality_gates: List[str]
    ) -> Dict[str, Any]:
        """Run quality checks on the modifications"""
        # Track this step in the reasoning trajectory
        self._add_reasoning_step("Quality Validation", 
                               f"Running quality checks: {', '.join(quality_gates)}")
        
        # This is a placeholder - implement actual Quality Team integration
        quality_results = {
            "passed": True,
            "gate_results": {},
            "issues": []
        }
        
        return quality_results
    
    async def _run_operational_checks(self, modification_result: Dict[str, Any]) -> Dict[str, Any]:
        """Run operational checks on the modifications"""
        # Track this step in the reasoning trajectory
        self._add_reasoning_step("Operational Validation", 
                               "Running SRE checks for operational stability")
        
        # This is a placeholder - implement actual SRE Team integration
        sre_results = {
            "passed": True,
            "check_results": {},
            "issues": []
        }
        
        return sre_results
    
    async def _refine_based_on_feedback(
        self, plan: Dict[str, Any], quality_results: Dict[str, Any], sre_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Refine the modification plan based on validation feedback"""
        # Track this step in the reasoning trajectory
        self._add_reasoning_step("Plan Refinement", 
                               "Refining plan based on validation feedback")
        
        # This is a placeholder - implement actual Reflective Operator integration
        refinement_result = {
            "reflection": "Identified issues that need to be addressed",
            "refined_plan": plan  # In a real implementation, this would be an updated plan
        }
        
        return refinement_result
    
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
        if self.team_session_state is None:
            return
        
        trajectory = self.team_session_state.get("reasoning_trajectory", [])
        
        step = {
            "step": step_name,
            "description": description,
            "timestamp": str(datetime.datetime.now()),
        }
        
        if success is not None:
            step["success"] = success
            
        trajectory.append(step)
        self.team_session_state["reasoning_trajectory"] = trajectory

def build_orchestration_team(session_state=None) -> Team:
    """
    Build the orchestration team with a code orchestration agent.
    
    Args:
        session_state: Optional shared session state dictionary.
        
    Returns:
        Team: Configured orchestration team
    """
    # Create the code orchestration agent
    orchestrator = CodeOrchestrationAgent()
    
    # Use provided session_state or initialize defaults
    session_state = session_state or {
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
        "reasoning_trajectory": []
    }
    
    # Create the team
    return Team(
        name="CodeEvolutionTeam",
        members=[orchestrator],
        mode="coordinate",
        model=llm_middle,
        instructions=[
            "You are the lead orchestrator of a code evolution factory.",
            "Your job is to coordinate specialized teams (Knowledge, Modification, Quality, SRE) to safely evolve code.",
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
        session_state=session_state
    )
