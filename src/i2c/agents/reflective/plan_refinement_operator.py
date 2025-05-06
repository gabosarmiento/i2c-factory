# /agents/reflective/plan_refinement_operator.py
"""PlanRefinementOperator

Reflective agent that takes an initial JSON modification plan, reasons over it
(with optional RAG context), improves the plan, validates against a JSON schema
+ logical‑consistency rules, and iterates until the plan is sound — all while
respecting i2c‑factory's budget‑tracking pipeline.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from agno.agent import Agent
from i2c.cli.controller import canvas
from builtins import llm_highest
from i2c.workflow.modification.rag_retrieval import retrieve_context_for_planner

from i2c.agents.reflective.context_aware_operator import (
    ContextAwareOperator,
    ValidationHook,
    create_schema_validation_hook,
)

################################################################################
# Main operator
################################################################################


class PlanRefinementOperator(ContextAwareOperator):
    """Iteratively improve a modification plan until it passes validation."""

    def __init__(
        self,
        *,
        budget_manager,
        rag_table=None,
        embed_model=None,
        max_reasoning_steps: int = 3,
        **kwargs,
    ) -> None:
        super().__init__(
            budget_manager=budget_manager,
            operation_type="plan_refinement",
            max_reasoning_steps=max_reasoning_steps,
            default_model_tier="highest",
        )
        self.rag_table = rag_table
        self.embed_model = embed_model

        self.reasoning_agent = Agent(
            model=llm_highest,
            reasoning=True,
            name="PlanRefinementAgent",
            description="Improves and validates project modification plans",
            instructions=[
                "You are an expert software architect specialising in plan refinement.",
                "Analyse the initial plan for gaps, dependencies and structure; then output a strictly‑valid JSON plan.",
            ],
        )
        self._register_default_validation_hooks()

    # ------------------------------------------------------------------
    # Validation hooks
    # ------------------------------------------------------------------
    def _register_default_validation_hooks(self) -> None:
        plan_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["file", "action", "what", "how"],
                "properties": {
                    "file": {"type": "string"},
                    "action": {"type": "string", "enum": ["create", "modify", "delete"]},
                    "what": {"type": "string"},
                    "how": {"type": "string"},
                },
            },
        }
        self.register_validation_hook(create_schema_validation_hook(plan_schema))
        self.register_validation_hook(
            ValidationHook(
                hook_id="plan_logical_consistency",
                hook_type="consistency",
                description="Ensure plan steps are logically ordered and non‑contradictory",
                validation_function=self._validate_logical_consistency,
                priority=7,
            )
        )

    ############################################################################
    # Public entry‑point
    ############################################################################

    def execute(
        self,
        *,
        initial_plan: str,
        user_request: str,
        project_path: str,
        language: str,
    ) -> Tuple[bool, Dict]:
        """Analyse, improve and validate an initial modification plan."""

        # ------------------------------------------------------------------
        # Phase 1 – analysis & context gathering
        # ------------------------------------------------------------------
        phase_id = "analyze_initial_plan"
        self.cost_tracker.start_phase(
            phase_id,
            "Analyse initial plan and retrieve context",
            model_id=getattr(llm_highest, "id", "Unknown"),
        )

        parsed_plan: List[Dict]
        try:
            parsed_plan = json.loads(initial_plan)
            if not isinstance(parsed_plan, list):
                raise ValueError
        except Exception:  # noqa: BLE001 – catch JSON + type errors together
            canvas.warning("Initial plan is not valid JSON; starting with empty plan.")
            parsed_plan = []

        retrieved_context = retrieve_context_for_planner(
            user_request, self.rag_table, self.embed_model
        )

        analysis_prompt = self._prepare_analysis_prompt(
            parsed_plan, user_request, project_path, language, retrieved_context
        )
        analysis = self._execute_reasoning_step(
            phase_id=phase_id,
            step_id="analyze_plan",
            prompt=analysis_prompt,
            model_tier="highest",
            context_chunks_used=[retrieved_context] if retrieved_context else None,
        )
        if not analysis:
            self.cost_tracker.end_phase(False, feedback="Failed to analyse initial plan")
            return False, {"error": "Failed to analyse initial plan"}

        plan_analysis = self._extract_analysis(analysis["response"])
        self.cost_tracker.end_phase(True, result=plan_analysis)

        # ------------------------------------------------------------------
        # Phase 2 – improvement loop
        # ------------------------------------------------------------------
        phase_id = "generate_improved_plan"
        self.cost_tracker.start_phase(
            phase_id,
            "Generate improved plan",
            model_id=getattr(llm_highest, "id", "Unknown"),
        )

        improve_prompt = self._prepare_improvement_prompt(
            parsed_plan, plan_analysis, user_request, retrieved_context
        )
        improve = self._execute_reasoning_step(
            phase_id=phase_id,
            step_id="generate_plan",
            prompt=improve_prompt,
            model_tier="highest",
            context_chunks_used=[retrieved_context] if retrieved_context else None,
        )
        if not improve:
            self.cost_tracker.end_phase(False, feedback="Failed to generate improved plan")
            return False, {"error": "Failed to generate improved plan"}

        plan = self._extract_plan(improve["response"])
        validation = self.run_validation_hooks(plan)
        # valid = all(v["outcome"] for v in validation.values())
        valid = bool(plan) and all(v["outcome"] for v in validation.values())

        
        
        
        self.cost_tracker.record_validation("generate_plan", valid, json.dumps(validation, indent=2))

        iterations = 0
        while not valid and iterations < self.max_reasoning_steps:
            fix_prompt = self._prepare_fix_prompt(plan, validation, user_request)
            fix_step = self._execute_reasoning_step(
                phase_id=phase_id,
                step_id=f"fix_plan_{iterations}",
                prompt=fix_prompt,
                model_tier="highest",
            )
            if not fix_step:
                break
            plan = self._extract_plan(fix_step["response"])
            validation = self.run_validation_hooks(plan)
            valid = bool(plan) and all(v["outcome"] for v in validation.values())
            self.cost_tracker.record_validation(
                f"fix_plan_{iterations}", valid, json.dumps(validation, indent=2)
            )
            iterations += 1

        self.cost_tracker.end_phase(valid, result=plan)

        # ------------------------------------------------------------------
        # Wrap‑up
        # ------------------------------------------------------------------
        final = {
            "plan": plan,
            "valid": valid,
            "iterations": iterations,
            "reasoning_trajectory": self.cost_tracker.trajectory,
        }
        self.cost_tracker.complete_operation(success=valid, final_result=final)
        return valid, final

    ############################################################################
    # Prompt helpers
    ############################################################################

    def _prepare_analysis_prompt(
        self,
        plan: List[Dict],
        user_request: str,
        project_path: str,
        language: str,
        retrieved_context: str,
    ) -> str:
        return (
            f"""# Plan Analysis Task\n\n## User Request\n{user_request}\n\n## Project Details\nPath: {project_path}\nLanguage: {language}\n\n## Initial Plan\n```json\n{json.dumps(plan, indent=2)}\n```\n\n## Retrieved Context\n{retrieved_context}\n\n## Analysis Task\nIdentify missing steps, dependency issues, sequencing errors and any mismatches with the user request. Return a structured analysis."""
        )

    def _prepare_improvement_prompt(
        self,
        plan: List[Dict],
        analysis: Dict,
        user_request: str,
        retrieved_context: str,
    ) -> str:
        return (
            f"""# Plan Improvement Task\n\n## User Request\n{user_request}\n\n## Initial Plan\n```json\n{json.dumps(plan, indent=2)}\n```\n\n## Analysis\n{json.dumps(analysis, indent=2)}\n\n## Retrieved Context\n{retrieved_context}\n\n## Improvement Task\nProduce an improved plan (JSON array with file/action/what/how) that resolves all issues."""
        )

    def _prepare_fix_prompt(
        self,
        plan: List[Dict],
        validation_results: Dict,
        user_request: str,
    ) -> str:
        feedback = "\n".join(
            f"- {hid}: {'✅' if res['outcome'] else '❌'} {res['feedback']}" for hid, res in validation_results.items() if not res["outcome"]
        )
        return (
            f"""# Plan Fix Task\n\n## User Request\n{user_request}\n\n## Current Plan\n```json\n{json.dumps(plan, indent=2)}\n```\n\n## Validation Issues\n{feedback}\n\n## Fix Task\nReturn a corrected JSON plan (array of steps with file/action/what/how)."""
        )

    ############################################################################
    # Extraction helpers
    ############################################################################

    @staticmethod
    def _extract_analysis(response: str) -> Dict:
        # Attempt to parse first JSON block
        import re

        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:  # noqa: BLE001 – fallback below
                pass
        return {"analysis": response, "structured": False}

    @staticmethod
    def _extract_plan(response: str) -> List[Dict]:
        import re

        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
        if match:
            try:
                obj = json.loads(match.group(1))
                return obj if isinstance(obj, list) else []
            except Exception:  # noqa: BLE001 – continue
                pass
        # fallback: strip and load if array‑looking
        trimmed = response.strip()
        if trimmed.startswith("[") and trimmed.endswith("]"):
            try:
                obj = json.loads(trimmed)
                return obj if isinstance(obj, list) else []
            except Exception:
                pass
        canvas.warning("Failed to extract plan; returning empty list.")
        return []

    ############################################################################
    # Logical‑consistency validator
    ############################################################################

    @staticmethod
    def _validate_logical_consistency(plan: List[Dict]) -> Tuple[bool, str]:
        created, modified = set(), set()
        errors: List[str] = []
        for idx, step in enumerate(plan):
            file = step.get("file", "")
            action = step.get("action", "")
            if action == "create":
                if file in created:
                    errors.append(f"Step {idx}: '{file}' created multiple times.")
                created.add(file)
            elif action == "modify":
                if file not in created and file not in modified:
                    errors.append(f"Step {idx}: '{file}' modified before creation.")
                modified.add(file)
            elif action == "delete":
                if file not in created and file not in modified:
                    errors.append(f"Step {idx}: '{file}' deleted but was never created.")
        return (not errors), "\n".join(errors) if errors else "Plan is logically consistent."
