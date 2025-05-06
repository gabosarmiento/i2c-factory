# from i2c/workflow/feature_pipeline.py
"""Feature Pipeline for transforming user stories into code features"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from i2c.models.user_story import UserStory, StoryStatus
from i2c.story_manager import StoryManager
from i2c.agents.budget_manager import BudgetManagerAgent
from i2c.agents.knowledge.documentation_retriever import DocumentationRetrieverAgent
from i2c.agents.knowledge.best_practices_agent import BestPracticesAgent
from i2c.agents.reflective.plan_refinement_operator import PlanRefinementOperator
from i2c.agents.reflective.issue_resolution_operator import IssueResolutionOperator
from i2c.agents.modification_team import modification_planner_agent, code_modifier_agent
from i2c.workflow.modification.execute_cycle import execute_modification_cycle
from i2c.cli.controller import canvas
from i2c.db_utils import get_db_connection
from i2c.workflow.modification.rag_retrieval import retrieve_combined_context


class FeaturePipeline:
    """Orchestrates the transformation of user stories into code features"""
    
    def __init__(
        self,
        project_path: Path,
        story_manager: StoryManager,
        budget_manager: BudgetManagerAgent,
        embed_model,
        db_connection=None
    ):
        self.project_path = project_path
        self.story_manager = story_manager
        self.budget_manager = budget_manager
        self.embed_model = embed_model
        self.db_connection = db_connection or get_db_connection()
        
        # Initialize agents
        self.doc_retriever = DocumentationRetrieverAgent(
            budget_manager=budget_manager,
            embed_model=embed_model
        )
        
        self.best_practices = BestPracticesAgent(
            budget_manager=budget_manager,
            embed_model=embed_model
        )
        
        self.plan_refiner = PlanRefinementOperator(
            budget_manager=budget_manager,
            rag_table=self.db_connection,
            embed_model=embed_model
        )
        
        self.issue_resolver = IssueResolutionOperator(
            budget_manager=budget_manager
        )
    
    def process_story(self, story_id: str) -> Tuple[bool, Dict]:
        """Process a single user story through the feature pipeline"""
        canvas.start_process(f"Feature Pipeline: Processing story {story_id}")
        
        # Get story
        story = self.story_manager.get_story(story_id)
        if not story:
            canvas.error(f"Story {story_id} not found")
            return False, {"error": "Story not found"}
        
        # Update status to in progress
        self.story_manager.update_story_status(story_id, StoryStatus.IN_PROGRESS)
        
        try:
            # Phase 1: Context Gathering
            canvas.step("Phase 1: Gathering context and documentation")
            context_result = self._gather_context(story)
            if not context_result["success"]:
                raise Exception(f"Context gathering failed: {context_result.get('error')}")
            
            # Phase 2: Plan Generation with Best Practices
            canvas.step("Phase 2: Generating implementation plan")
            plan_result = self._generate_plan(story, context_result)
            if not plan_result["success"]:
                raise Exception(f"Plan generation failed: {plan_result.get('error')}")
            
            # Phase 3: Code Implementation
            canvas.step("Phase 3: Implementing feature code")
            impl_result = self._implement_feature(story, plan_result)
            if not impl_result["success"]:
                raise Exception(f"Implementation failed: {impl_result.get('error')}")
            
            # Phase 4: Issue Resolution (if needed)
            if impl_result.get("issues"):
                canvas.step("Phase 4: Resolving implementation issues")
                resolution_result = self._resolve_issues(impl_result["issues"])
                if not resolution_result["success"]:
                    raise Exception(f"Issue resolution failed: {resolution_result.get('error')}")
            
            # Update story status
            self.story_manager.update_story_status(story_id, StoryStatus.COMPLETED)
            
            canvas.success(f"Successfully processed story {story_id}")
            return True, {
                "story_id": story_id,
                "context": context_result,
                "plan": plan_result,
                "implementation": impl_result,
                "resolution": resolution_result if impl_result.get("issues") else None
            }
            
        except Exception as e:
            canvas.error(f"Feature pipeline failed: {e}")
            self.story_manager.update_story_status(story_id, StoryStatus.BLOCKED)
            return False, {"error": str(e)}
        
        finally:
            canvas.end_process("Feature Pipeline completed")
    
    def _gather_context(self, story: UserStory) -> Dict:
        """Gather context from knowledge base and documentation"""
        try:
            # Get existing story context
            story_context = self.story_manager.get_story_context(story.story_id)
            
            # Retrieve relevant documentation
            query = story.to_prompt()
            doc_success, doc_result = self.doc_retriever.execute(
                query=query,
                project_path=self.project_path,
                language="python",  # TODO: Make configurable
                # db_connection=self.db_connection
            )
            
            if not doc_success:
                canvas.warning("Documentation retrieval failed, continuing with limited context")
            
            # Retrieve combined context (code + knowledge)
            combined_context = retrieve_combined_context(
                query,
                self.db_connection, 
                self.embed_model
            )
            
            return {
                "success": True,
                "story_context": story_context,
                "documentation": doc_result.get("documents", []) if doc_success else [],
                "code_context": combined_context.get("code_context", ""),
                "knowledge_context": combined_context.get("knowledge_context", "")
            }
            
        except Exception as e:
            canvas.error(f"Error gathering context: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_plan(self, story: UserStory, context: Dict) -> Dict:
        """Generate implementation plan with best practices"""
        try:
            # Get best practices for the feature
            practices_success, practices_result = self.best_practices.execute(
                user_request=story.to_prompt(),
                project_path=self.project_path,
                language="python",  # TODO: Make configurable
                # db_connection=self.db_connection
            )
            
            if not practices_success:
                canvas.warning("Best practices generation failed, continuing without")
            
            # Generate initial plan
            initial_plan = self._create_initial_plan(story, context, practices_result.get("best_practices", []))
            
            # Refine plan
            refine_success, refine_result = self.plan_refiner.execute(
                initial_plan=json.dumps(initial_plan),
                user_request=story.to_prompt(),
                project_path=str(self.project_path),
                language="python"  # TODO: Make configurable
            )
            
            if not refine_success:
                canvas.warning("Plan refinement failed, using initial plan")
                final_plan = initial_plan
            else:
                final_plan = refine_result["plan"]
            
            return {
                "success": True,
                "initial_plan": initial_plan,
                "refined_plan": final_plan,
                "best_practices": practices_result.get("best_practices", []) if practices_success else [],
                "refinement_iterations": refine_result.get("iterations", 0) if refine_success else 0
            }
            
        except Exception as e:
            canvas.error(f"Error generating plan: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_initial_plan(self, story: UserStory, context: Dict, best_practices: List[Dict]) -> List[Dict]:
        """Create initial modification plan from story and context"""
        # Basic plan structure - would be enhanced by an LLM in production
        plan = []
        
        # Example: Create feature file based on story
        feature_file = f"features/{story.story_id.replace('story_', '')}.py"
        plan.append({
            "file": feature_file,
            "action": "create",
            "what": f"Create feature implementation for: {story.title}",
            "how": f"Implement feature based on story requirements: {story.i_want}"
        })
        
        # Example: Create test file
        test_file = f"tests/test_{story.story_id.replace('story_', '')}.py"
        plan.append({
            "file": test_file,
            "action": "create",
            "what": f"Create tests for: {story.title}",
            "how": f"Implement tests for acceptance criteria: {', '.join([ac.description for ac in story.acceptance_criteria])}"
        })
        
        # Apply best practices
        for practice in best_practices[:3]:  # Limit to top 3 practices
            plan.append({
                "file": feature_file,
                "action": "modify",
                "what": f"Apply best practice: {practice.get('practice', '')}",
                "how": practice.get('rationale', '')
            })
        
        return plan
    
    def _implement_feature(self, story: UserStory, plan_result: Dict) -> Dict:
        """Implement the feature based on the refined plan"""
        try:
            # Use the existing modification cycle
            result = execute_modification_cycle(
                story.to_prompt(),        # user_request
                self.project_path,        # project_path
                "python",                 # language
                self.db_connection,       # db
                self.embed_model,         # embed_model
            )
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": "Modification cycle failed",
                    "details": result
                }
            
            # Check for any issues (test failures, etc.)
            issues = []
            if result.get("test_failures"):
                issues.extend([
                    {"type": "test_failure", "file": file, "details": details}
                    for file, details in result["test_failures"].items()
                ])
            
            return {
                "success": True,
                "code_map": result.get("code_map", {}),
                "issues": issues,
                "language": result.get("language", "python")
            }
            
        except Exception as e:
            canvas.error(f"Error implementing feature: {e}")
            return {"success": False, "error": str(e)}
    
    def _resolve_issues(self, issues: List[Dict]) -> Dict:
        """Resolve implementation issues using IssueResolutionOperator"""
        resolved_issues = []
        unresolved_issues = []
        
        for issue in issues:
            if issue["type"] == "test_failure":
                try:
                    file_path = issue["file"]
                    file_content = (self.project_path / file_path).read_text()
                    
                    resolve_success, resolve_result = self.issue_resolver.execute(
                        test_failure=issue["details"],
                        file_content=file_content,
                        file_path=file_path,
                        language="python",  # TODO: Make configurable
                        project_path=self.project_path
                    )
                    
                    if resolve_success:
                        resolved_issues.append({
                            "issue": issue,
                            "resolution": resolve_result
                        })
                        
                        # Apply the fix
                        fixed_content = resolve_result.get("fixed_content", "")
                        if fixed_content:
                            (self.project_path / file_path).write_text(fixed_content)
                    else:
                        unresolved_issues.append(issue)
                        
                except Exception as e:
                    canvas.error(f"Error resolving issue: {e}")
                    unresolved_issues.append(issue)
        
        return {
            "success": len(unresolved_issues) == 0,
            "resolved_issues": resolved_issues,
            "unresolved_issues": unresolved_issues
        }
    
    def process_ready_stories(self) -> Dict[str, Dict]:
        """Process all stories in READY status"""
        ready_stories = self.story_manager.get_ready_stories()
        results = {}
        
        canvas.info(f"Found {len(ready_stories)} ready stories to process")
        
        for story in ready_stories:
            canvas.info(f"Processing story: {story.story_id} - {story.title}")
            success, result = self.process_story(story.story_id)
            results[story.story_id] = {
                "success": success,
                "result": result
            }
        
        # Summary
        successful = sum(1 for r in results.values() if r["success"])
        canvas.info(f"Processed {len(results)} stories: {successful} successful, {len(results) - successful} failed")
        
        return results