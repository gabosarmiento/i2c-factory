# i2c/workflow/workflow_controller.py
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from i2c.workflow.session_manager import WorkflowSessionManager
from i2c.workflow.generation_workflow import GenerationWorkflow
from i2c.workflow.modification_workflow import ModificationWorkflow
from i2c.workflow.quality_workflow import QualityWorkflow
from i2c.workflow.self_healing_controller import SelfHealingController
from i2c.workflow.sre_team_workflow import SRETeamWorkflow
from agno.embedder.sentence_transformer import SentenceTransformerEmbedder
from i2c.db_utils import get_db_connection
from i2c.cli.controller import canvas
import builtins

# Get the global budget manager
if hasattr(builtins, 'global_budget_manager'):
    budget_manager = builtins.global_budget_manager
else:
    # Create a default one if not available
    from i2c.agents.budget_manager import BudgetManagerAgent
    budget_manager = BudgetManagerAgent(session_budget=None)
    
class WorkflowController:
    """
    Controls workflow execution with recovery capabilities.
    Manages the execution of different Agno workflows and maintains shared state.
    """
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"wfc-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.session_manager = WorkflowSessionManager(self.session_id)
        self.recovery_log = []
        self.last_error = None  
    
    def get_last_error(self) -> Optional[str]:
        """Get the last error message from workflow execution"""
        return self.last_error

    def _set_error(self, error_message: str):
        """Set the last error message"""
        self.last_error = error_message
        canvas.error(f"[WorkflowController] {error_message}")
        
    def run_workflow_with_recovery(self, workflow, max_attempts: int = 1, **kwargs) -> bool:
        """
        Run a workflow with basic recovery attempts.
        
        Args:
            workflow: An Agno Workflow instance
            max_attempts: Maximum number of recovery attempts
            **kwargs: Arguments to pass to the workflow's run method
            
        Returns:
            bool: Success status
        """
        workflow_name = workflow.__class__.__name__
        canvas.info(f"🚀 [WorkflowController] Running {workflow_name}...")
        
        # Store initial parameters in session state
        for key, value in kwargs.items():
            if key != 'db' and key != 'embed_model':  # Skip DB/embedder objects
                self.session_manager.update_state(**{key: value})
        
        # First attempt
        success = False
        final_response = None
        error_message = None
        
        try:
            # Run workflow and collect responses
            for response in workflow.run(**kwargs):
                # Update session with any extra_data from response
                if hasattr(response, 'extra_data') and response.extra_data:
                    self.session_manager.update_state(**response.extra_data)
                final_response = response
            
            # Check if final response indicates success
            if final_response and hasattr(final_response, 'extra_data'):
                success = final_response.extra_data.get('success', False)
            else:
                success = False
                
        except Exception as e:
            error_message = str(e)
            canvas.error(f"❌ [WorkflowController] {workflow_name} failed: {e}")
            self.recovery_log.append({
                "workflow": workflow_name,
                "attempt": 0,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
        
        # Recovery attempts if needed
        attempt = 1
        while not success and attempt <= max_attempts and error_message:
            canvas.warning(f"🔄 [WorkflowController] Recovery attempt {attempt} for {workflow_name}...")
            
            try:
                # Create a fresh workflow instance for recovery
                recovery_workflow = workflow.__class__(
                    session_id=f"{self.session_id}-recovery{attempt}"
                )
                
                # Run the recovery workflow
                for response in recovery_workflow.run(**kwargs):
                    if hasattr(response, 'extra_data') and response.extra_data:
                        self.session_manager.update_state(**response.extra_data)
                    final_response = response
                
                # Check recovery success
                if final_response and hasattr(final_response, 'extra_data'):
                    success = final_response.extra_data.get('success', False)
                
                # Log recovery attempt
                self.recovery_log.append({
                    "workflow": workflow_name,
                    "attempt": attempt,
                    "success": success,
                    "timestamp": datetime.now().isoformat()
                })
                
                if success:
                    canvas.success(f"✅ [WorkflowController] Recovery attempt {attempt} succeeded!")
                    break
                    
            except Exception as e:
                error_message = str(e)
                canvas.error(f"❌ [WorkflowController] Recovery attempt {attempt} failed: {e}")
                self.recovery_log.append({
                    "workflow": workflow_name,
                    "attempt": attempt,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
            
            attempt += 1
            
        # Final status
        if success:
            canvas.success(f"✅ [WorkflowController] {workflow_name} completed successfully!")
        else:
            canvas.error(f"❌ [WorkflowController] {workflow_name} failed after {attempt} attempt(s).")
            
        return success
            
    def run_generation_cycle(self, structured_goal: dict, project_path: Path, session_state: dict = None) -> bool:
        """
        Run the generation cycle workflow with integration intelligence.
        
        Args:
            structured_goal: Dict with objective and language
            project_path: Path to the project directory
            session_state: Session state to pass through workflow
            
        Returns:
            bool: Success status
        """
        # Check if we should use integration intelligence
        use_integration_intelligence = structured_goal.get("use_integration_intelligence", True)
        
        if use_integration_intelligence:
            canvas.info("🧠 Attempting Integration Intelligence Workflow")
            try:
                import asyncio
                from i2c.workflow.integration_intelligence import execute_integration_intelligence_workflow
                
                # Prepare objective
                objective = {
                    "task": structured_goal.get("objective", "Generate software system"),
                    "constraints": structured_goal.get("constraints", []),
                    "language": structured_goal.get("language", "Python"),
                    "system_type": session_state.get("system_type", "fullstack_web_app") if session_state else "fullstack_web_app"
                }
                
                # Merge session state
                merged_session_state = session_state.copy() if session_state else {}
                merged_session_state.update({
                    "project_path": str(project_path),
                    "structured_goal": structured_goal
                })
                
                # Execute integration intelligence workflow
                if hasattr(asyncio, 'run'):
                    result = asyncio.run(execute_integration_intelligence_workflow(objective, merged_session_state))
                else:
                    # Fallback for older Python versions
                    loop = asyncio.get_event_loop()
                    result = loop.run_until_complete(execute_integration_intelligence_workflow(objective, merged_session_state))
                
                if result.success:
                    canvas.success("🎉 Integration Intelligence succeeded!")
                    
                    # Write files to disk
                    from i2c.workflow.modification.file_operations import write_files_to_disk
                    write_files_to_disk(result.files, project_path)
                    
                    canvas.success(f"✅ Generated {len(result.files)} files with integration intelligence")
                    return True
                else:
                    canvas.warning("⚠️ Integration Intelligence failed, falling back to standard workflow")
                    for error in result.errors:
                        canvas.error(f"❌ {error}")
                    # Fall through to standard workflow
                    
            except Exception as e:
                canvas.error(f"❌ Integration Intelligence failed: {e}")
                canvas.warning("⚠️ Falling back to standard generation workflow")
                # Fall through to standard workflow
        
        # Standard generation workflow (fallback)
        canvas.info("🔄 Using standard generation workflow")
        
        # Update session state
        self.session_manager.update_state(
            action_type="generate",
            structured_goal=structured_goal,
            project_path=str(project_path),
            language=structured_goal.get("language")
        )
        
        # Create and run workflow
        workflow = GenerationWorkflow(session_id=f"{self.session_id}-gen")
        workflow.session_state.update({
            "action_type": "generate",
            "structured_goal": structured_goal,
            "project_path": str(project_path),
            "language": structured_goal.get("language")
        })

        # Merge in the passed session_state (contains knowledge_base)
        if session_state:
            workflow.session_state.update(session_state)
            canvas.info(f"🔍 DEBUG: Merged session_state into GenerationWorkflow: {'knowledge_base' in session_state}")
            
            # Verify knowledge_base is now in workflow session_state
            if 'knowledge_base' in workflow.session_state:
                canvas.success("✅ DEBUG: Knowledge base successfully passed to GenerationWorkflow")
            else:
                canvas.error("❌ DEBUG: Knowledge base missing after merge")
        
        success = self.run_workflow_with_recovery(
            workflow, 
            max_attempts=1,
            structured_goal=structured_goal,
            project_path=project_path
        )
        
        # NEW: Extract updated session state from workflow and store it
        if success and hasattr(workflow, 'session_state'):
            # Update our session manager with the workflow's final session state
            for key, value in workflow.session_state.items():
                if key not in ['action_type', 'structured_goal', 'language']:  # Skip workflow-specific keys
                    self.session_manager.update_state(**{key: value})
            
            canvas.info(f"🔄 DEBUG: Extracted {len(workflow.session_state)} keys from GenerationWorkflow")
            
            # Log important keys that were extracted (removed team-specific keys: project_context, validation_results)
            important_keys = [
                'knowledge_base', 'architectural_context', 'system_type', 'reflection_memory', 
                'retrieved_context', 'enhanced_objective', 'db_path', 
                'project_path', 'backend_api_routes', 'api_route_summary'
            ]
            
            extracted_keys = []
            missing_keys = []
            
            for key in important_keys:
                if key in workflow.session_state:
                    extracted_keys.append(key)
                else:
                    missing_keys.append(key)
            
            if extracted_keys:
                canvas.success(f"✅ DEBUG: Extracted keys: {', '.join(extracted_keys)}")
            if missing_keys:
                canvas.warning(f"⚠️ DEBUG: Missing keys: {', '.join(missing_keys)}")

        return success

    def run_modification_cycle(self, user_request: str, project_path: Path, language: str, session_state: dict = None) -> bool:
        """
        Run the modification cycle workflow with recovery.
        
        Args:
            user_request: The modification request
            project_path: Path to the project directory
            language: The programming language
            
        Returns:
            bool: Success status
        """
        # Update session state
        self.session_manager.update_state(
            action_type="modify",
            user_request=user_request,
            project_path=str(project_path),
            language=language
        )
        
        # Initialize RAG resources
        db = get_db_connection()
        embed_model = SentenceTransformerEmbedder()
        
        # Create and run workflow
        workflow = ModificationWorkflow(session_id=f"{self.session_id}-mod")
        
        # NEW: Merge session state into workflow if provided
        if session_state:
            workflow.session_state.update(session_state)
            canvas.info(f"🔍 DEBUG: Merged session_state into ModificationWorkflow")
        
        success = self.run_workflow_with_recovery(
            workflow,
            max_attempts=1,
            user_request=user_request,
            project_path=project_path,
            language=language,
            db=db,
            embed_model=embed_model
        )
        
        # NEW: Extract updated session state from modification workflow
        if success and hasattr(workflow, 'session_state'):
            for key, value in workflow.session_state.items():
                if key not in ['user_request', 'language']:  # Skip workflow-specific keys
                    self.session_manager.update_state(**{key: value})
            
            canvas.info(f"🔄 DEBUG: Extracted session state from ModificationWorkflow")

        return success
    
    def run_sre_workflow(self, project_path: Path, language: str, session_state: dict = None) -> bool:
        """
        Run the SRE workflow with session state coordination.
        
        Args:
            project_path: Path to the project directory
            language: The programming language
            session_state: Session state to pass to SRE workflow
            
        Returns:
            bool: Success status
        """
        # Update session state
        self.session_manager.update_state(
            project_path=str(project_path),
            language=language
        )
        
        # NEW: Merge passed session state
        if session_state:
            for key, value in session_state.items():
                self.session_manager.update_state(**{key: value})
            canvas.info(f"🔄 DEBUG: Merged session state into SRE workflow")
        
        # Get current session state for SRE workflow
        current_session_state = self.session_manager.get_state()
        
        canvas.info("🔍 [WorkflowController] Running SRE Workflow via SRETeam...")
        
        try:
            # NEW: Use the enhanced SRE team with session state
            from i2c.agents.sre_team.sre_team import build_sre_team
            
            sre_team = build_sre_team(
                project_path=project_path,
                session_state=current_session_state
            )
            
            # Run SRE validation
            sre_results = sre_team.run_sync()
            
            success = sre_results.get("passed", False)
            
            # Extract SRE results for later use
            self.session_manager.update_state(
                sre_results=sre_results,
                analysis_summary=sre_results.get("summary", {}),
                deployment_ready=sre_results.get("deployment_ready", False),
                docker_ready=sre_results.get("docker_ready", False)
            )
            
            if success:
                canvas.success("✅ [WorkflowController] SRE Workflow completed successfully!")
            else:
                canvas.error("❌ [WorkflowController] SRE Workflow failed.")
                
            return success
            
        except Exception as e:
            canvas.error(f"❌ [WorkflowController] Error running SRE Workflow: {e}")
            return False
    
    def run_quality_workflow(self, project_path: Path, structured_goal: dict, session_state: dict = None) -> bool:
        """
        Run the quality workflow with session state coordination.
        
        Args:
            project_path: Path to the project directory
            structured_goal: Dict with objective and language
            session_state: Session state to pass to quality workflow
            
        Returns:
            bool: Success status
        """
        # NEW: Merge passed session state
        if session_state:
            for key, value in session_state.items():
                self.session_manager.update_state(**{key: value})
            canvas.info(f"🔄 DEBUG: Merged session state into Quality workflow")
        
        # Get current session state
        current_session_state = self.session_manager.get_state()
        
        # Get code_map and analysis_summary from session state
        code_map = current_session_state.get("code_map", {})
        analysis_summary = current_session_state.get("analysis_summary", {})
        
        if not code_map:
            canvas.warning("⚠️ [WorkflowController] No code map available for quality workflow.")
            return False
        
        canvas.info("🔍 [WorkflowController] Running Quality Workflow via QualityTeam...")
        
        try:
            # NEW: Use the enhanced Quality team with session state
            from i2c.agents.quality_team.quality_team import build_quality_team
            
            quality_team = build_quality_team(session_state=current_session_state)
            
            # Create quality validation message
            validation_message = {
                "instruction": "Validate the modified files using all relevant quality gates.",
                "project_path": str(project_path),
                "modified_files": code_map,
                "quality_gates": []  # Will be determined by the team
            }
            
            # Run quality validation using the team
            from agno.agent import Message
            message = Message(role="user", content=str(validation_message))
            
            quality_results = quality_team.run(message=message)
            
            # Extract results (assuming quality team returns structured results)
            success = getattr(quality_results, 'passed', True) if hasattr(quality_results, 'passed') else True
            
            # Store quality results in session state
            self.session_manager.update_state(
                quality_results=quality_results,
                quality_validation_passed=success
            )
            
            if success:
                canvas.success("✅ [WorkflowController] Quality Workflow completed successfully!")
            else:
                canvas.error("❌ [WorkflowController] Quality Workflow failed.")
                
            return success
            
        except Exception as e:
            canvas.error(f"❌ [WorkflowController] Error running Quality Workflow: {e}")
            # Fallback to legacy approach
            workflow = QualityWorkflow(session_id=f"{self.session_id}-quality")
            return self.run_workflow_with_recovery(
                workflow,
                max_attempts=1,
                project_path=project_path,
                structured_goal=structured_goal,
                code_map=code_map,
                analysis_summary=analysis_summary
            )

    def run_complete_workflow(self, action_type: str, action_detail: Any, 
                            project_path: Path, structured_goal: dict, 
                            session_state: dict = None) -> bool:
        """
        Run the complete workflow sequence (main cycle, SRE, quality).
        
        Args:
            action_type: "generate" or "modify"
            action_detail: Structured goal or user request
            project_path: Path to the project directory
            structured_goal: Dict with objective and language
            session_state: Session state to maintain across workflows
            
        Returns:
            bool: Overall success status
        """
        # Update session state with initial values
        self.session_manager.update_state(
            action_type=action_type,
            project_path=str(project_path),
            structured_goal=structured_goal,
            language=structured_goal.get("language") if structured_goal else "python"
        )
        
        # NEW: Merge passed session_state into session manager
        if session_state:
            for key, value in session_state.items():
                self.session_manager.update_state(**{key: value})
            canvas.info(f"🔄 DEBUG: Merged {len(session_state)} keys into WorkflowController session")
        
        # 1. Run main cycle (generation or modification)
        if action_type == "generate":
            canvas.info(f"🏭 [WorkflowController] Starting Generation Cycle...")
            
            # Get current session state from session manager
            current_session_state = self.session_manager.get_state()
            canvas.info(f"🔍 DEBUG: Passing {len(current_session_state)} session keys to generation cycle")
            
            main_cycle_success = self.run_generation_cycle(
                structured_goal=action_detail,
                project_path=project_path,
                session_state=current_session_state
            )
        elif action_type == "modify":
            canvas.info(f"🏭 [WorkflowController] Starting Modification Cycle...")
            
            # Get current session state from session manager
            current_session_state = self.session_manager.get_state()
            
            main_cycle_success = self.run_modification_cycle(
                user_request=action_detail,
                project_path=project_path,
                language=structured_goal.get("language", "python"),
                session_state=current_session_state  # NEW: Pass session state
            )
        else:
            canvas.error(f"❌ [WorkflowController] Unknown action type: {action_type}")
            return False
        
        # Check main cycle success
        if not main_cycle_success:
            canvas.error(f"❌ [WorkflowController] Main cycle failed.")
            return False

        # 1.5. Extract API routes for frontend-backend integration (NEW)
        current_session_state = self.session_manager.get_state()
        self._extract_api_routes_for_integration(project_path, current_session_state)

        # 2. Run SRE workflow with current session state
        current_session_state = self.session_manager.get_state()
        sre_success = self.run_sre_workflow(
            project_path=project_path,
            language=structured_goal.get("language", "python"),
            session_state=current_session_state
        )
        
        # Check SRE success
        if not sre_success:
            canvas.error(f"❌ [WorkflowController] SRE workflow failed.")
            return False
        
        # 3. Run quality workflow with current session state
        current_session_state = self.session_manager.get_state()
        quality_success = self.run_quality_workflow(
            project_path=project_path,
            structured_goal=structured_goal,
            session_state=current_session_state
        )       

        
        # Final status
        # Resilient success logic - don't fail entire workflow for quality/SRE issues
        overall_success = main_cycle_success  # Main generation must succeed

        # Capture specific error messages
        error_details = []
        
        if not main_cycle_success:
            error_msg = "Main generation cycle failed"
            error_details.append(error_msg)
            self._set_error(error_msg)
        
        # Log quality and SRE results without failing entire workflow
        if not quality_success:
            error_msg = "Quality validation failed"  
            error_details.append(error_msg)
            canvas.warning(f"⚠️ [WorkflowController] {error_msg} but continuing...")
            
        if not sre_success:
            error_msg = "SRE validation failed"
            error_details.append(error_msg)
            canvas.warning(f"⚠️ [WorkflowController] {error_msg} but continuing...")

        # Set combined error message if any failures
        if error_details:
            self._set_error("; ".join(error_details))
            
        # Report detailed status
        if overall_success:
            if quality_success and sre_success:
                canvas.success(f"🎉 [WorkflowController] Complete workflow succeeded with all validations!")
            else:
                canvas.success(f"✅ [WorkflowController] Generation succeeded (quality: {'✅' if quality_success else '⚠️'}, SRE: {'✅' if sre_success else '⚠️'})")
        else:
            canvas.error(f"❌ [WorkflowController] Main generation failed.")

        return overall_success
    
    def _extract_api_routes_for_integration(self, project_path: Path, session_state: dict):
        """
        Extract API routes from backend files and store in session state for frontend integration.
        This ensures frontend components can connect to real backend endpoints.
        """
        try:
            # Check if this is a system that needs API integration
            arch_context = session_state.get("architectural_context", {})
            system_type = arch_context.get("system_type")
            
            if system_type not in ["fullstack_web_app", "microservices"]:
                canvas.info(f"🔍 DEBUG: Skipping API extraction for system type: {system_type}")
                return
            
            # Check if backend files exist
            backend_files = list(project_path.rglob("backend/**/*.py")) + list(project_path.rglob("**/main.py")) + list(project_path.rglob("**/app.py"))
            if not backend_files:
                canvas.info("🔍 DEBUG: No backend files found - skipping API extraction")
                return
            
            canvas.step("Extracting API routes for frontend-backend integration...")
            
            # Import API route extraction utilities
            from i2c.utils.api_route_tracker import APIRouteExtractor, FrontendAPIInjector
            
            # Extract routes from the project
            extractor = APIRouteExtractor()
            routes = extractor.extract_from_project(project_path)
            
            # Store routes in session state
            session_state['backend_api_routes'] = routes
            
            # Create API summary for frontend injection
            injector = FrontendAPIInjector(routes)
            session_state['api_route_summary'] = injector.api_summary
            
            # Update session manager
            self.session_manager.update_state(
                backend_api_routes=routes,
                api_route_summary=injector.api_summary
            )
            
            # Log success
            total_routes = sum(len(endpoints) for endpoints in routes.values())
            if total_routes > 0:
                canvas.success(f"✅ Extracted {total_routes} API routes for frontend integration")
                
                # Debug: show extracted routes
                for method, endpoints in routes.items():
                    if endpoints:
                        canvas.info(f"   {method.upper()}: {len(endpoints)} endpoints")
                        for endpoint in endpoints[:3]:  # Show first 3
                            path = endpoint.get('full_path') or endpoint.get('path', '')
                            canvas.info(f"     - {path}")
                        if len(endpoints) > 3:
                            canvas.info(f"     ... and {len(endpoints) - 3} more")
            else:
                canvas.warning("⚠️ No API routes found in backend files")
                
        except Exception as e:
            canvas.warning(f"⚠️ API route extraction failed: {e}")
            # Don't fail the workflow, just log the error
            import traceback
            canvas.warning(f"API extraction error details: {traceback.format_exc()}")