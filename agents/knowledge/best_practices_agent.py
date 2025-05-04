# /agents/knowledge/best_practices_agent.py
"""BestPracticesAgent

Provides coding best practices using RAG context and integrates with IssueResolutionOperator.
"""

from __future__ import annotations
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from cli.controller import canvas
from builtins import llm_highest
from agno.agent import Agent
from agents.reflective.context_aware_operator import ContextAwareOperator, ValidationHook
from db_utils import query_context, TABLE_CODE_CONTEXT
from workflow.modification.rag_retrieval import retrieve_context_for_step

class BestPracticesAgent(ContextAwareOperator):
    """Generates coding best practices based on project context."""

    def __init__(
        self,
        budget_manager,
        embed_model,
        max_reasoning_steps: int = 3,
        **kwargs,
    ) -> None:
        super().__init__(
            budget_manager=budget_manager,
            operation_type="best_practices",
            max_reasoning_steps=max_reasoning_steps,
            default_model_tier="highest",
        )
        self.embed_model = embed_model
        self.reasoning_agent = Agent(
            model=llm_highest,
            reasoning=True,
            name="BestPracticesAgent",
            description="Provides coding best practices",
            instructions=[
                "You are an expert in software engineering best practices.",
                "Provide concise, actionable best practices based on the context.",
                "Focus on the specific language and project requirements.",
            ],
        )
        self._register_default_validation_hooks()

    def _register_default_validation_hooks(self) -> None:
        """Register validation hooks for best practices."""
        self.register_validation_hook(
            ValidationHook(
                hook_id="practice_relevance",
                hook_type="relevance",
                description="Ensures best practices are relevant and actionable",
                validation_function=self._validate_practice_relevance,
                priority=8,
            )
        )

    def execute(
        self,
        user_request: str,
        project_path: Path,
        language: str,
        db_connection=None,
        issue_context: Optional[Dict] = None,
    ) -> Tuple[bool, Dict]:
        """Generate best practices for a given request or issue."""
        from db_utils import get_db_connection
        db = db_connection or get_db_connection()
        phase_id = "generate_practices"
        self.cost_tracker.start_phase(
            phase_id,
            "Generate coding best practices",
            model_id=getattr(llm_highest, "id", "Unknown"),
        )

        try:
            # Retrieve RAG context - use the correct function signature
            step_stub = {"what": user_request}
            code_context = retrieve_context_for_step(step_stub, db, self.embed_model)
            if not code_context:
                canvas.warning("No relevant code context found.")
                code_context = []

            analysis_prompt = self._prepare_analysis_prompt(
                user_request, code_context, language, issue_context
            )
            analysis_result = self._execute_reasoning_step(
                phase_id=phase_id,
                step_id="analyze_practices",
                prompt=analysis_prompt,
                model_tier="highest",
                context_chunks_used=code_context,
            )

            if not analysis_result:
                self.cost_tracker.end_phase(False, feedback="Failed to analyze best practices")
                return False, {"error": "Failed to analyze best practices", "reasoning_trajectory": self.cost_tracker.trajectory}

            practices = self._extract_practices(analysis_result["response"])
            validation = self.run_validation_hooks(practices)
            valid = bool(practices) and all(v["outcome"] for v in validation.values())
            self.cost_tracker.record_validation("analyze_practices", valid, json.dumps(validation, indent=2))

            iterations = 0
            while not valid and iterations < self.max_reasoning_steps:
                fix_prompt = self._prepare_fix_prompt(user_request, practices, validation, issue_context)
                fix_result = self._execute_reasoning_step(
                    phase_id=phase_id,
                    step_id=f"fix_practices_{iterations}",
                    prompt=fix_prompt,
                    model_tier="highest",
                )
                if not fix_result:
                    break
                practices = self._extract_practices(fix_result["response"])
                validation = self.run_validation_hooks(practices)
                valid = bool(practices) and all(v["outcome"] for v in validation.values())
                self.cost_tracker.record_validation(f"fix_practices_{iterations}", valid, json.dumps(validation, indent=2))
                iterations += 1

            self.cost_tracker.end_phase(valid, result=practices)
            final = {
                "best_practices": practices,
                "valid": valid,
                "iterations": iterations,
                "reasoning_trajectory": self.cost_tracker.trajectory,
            }
            self.cost_tracker.complete_operation(success=valid, final_result=final)
            return valid, final

        except Exception as e:
            canvas.error(f"Error in best practices generation: {e}")
            self.cost_tracker.complete_operation(success=False, final_result={"error": str(e), "reasoning_trajectory": self.cost_tracker.trajectory})
            return False, {"error": str(e), "reasoning_trajectory": self.cost_tracker.trajectory}

    def _prepare_analysis_prompt(
        self, user_request: str, code_context: List[str], language: str, issue_context: Optional[Dict]
    ) -> str:
        """Craft prompt for generating best practices."""
        issue_text = json.dumps(issue_context, indent=2) if issue_context else "None"
        return f"""
# Best Practices Analysis Task
## User Request
{user_request}
## Language
{language}
## Code Context
{json.dumps(code_context, indent=2)}
## Issue Context (if applicable)
{issue_text}
## Task
Generate a list of best practices relevant to the request and context.
Return a JSON array of practices, each with 'practice' (string) and 'rationale' (string).
"""

    def _prepare_fix_prompt(
        self, user_request: str, practices: List[Dict], validation_results: Dict, issue_context: Optional[Dict]
    ) -> str:
        """Craft prompt for fixing invalid best practices."""
        feedback = "\n".join(
            f"- {hid}: {'✅' if res['outcome'] else '❌'} {res['feedback']}"
            for hid, res in validation_results.items()
            if not res["outcome"]
        )
        issue_text = json.dumps(issue_context, indent=2) if issue_context else "None"
        return f"""
# Best Practices Fix Task
## User Request
{user_request}
## Current Practices
{json.dumps(practices, indent=2)}
## Validation Issues
{feedback}
## Issue Context
{issue_text}
## Task
Return a corrected JSON array of best practices.
"""

    def _extract_practices(self, response: str) -> List[Dict]:
        """Extract best practices from LLM response."""
        import re
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
        if match:
            try:
                obj = json.loads(match.group(1))
                return obj if isinstance(obj, list) else []
            except Exception:
                pass
        canvas.warning("Failed to extract practices; returning empty list.")
        return []

    @staticmethod
    def _validate_practice_relevance(practices: List[Dict]) -> Tuple[bool, str]:
        """Validate that best practices are relevant and actionable."""
        if not practices:
            return False, "No practices provided."
        for practice in practices:
            if not all(key in practice for key in ["practice", "rationale"]):
                return False, "Practice missing required fields."
            if len(practice["practice"]) < 10:
                return False, "Practice description too short."
        return True, "Practices are relevant and actionable."