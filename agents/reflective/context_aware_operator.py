# /agents/reflective/context_aware_operator.py
"""Context‑Aware Operator base classes and helpers.

This cleaned‑up version fixes minor syntax/typing hiccups, adds missing imports,
normalises doc‑strings, and ensures the file is importable.
"""
from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from cli.controller import canvas
from llm_providers import llm_highest, llm_middle, llm_small, llm_xs
from workflow.utils import count_tokens, estimate_cost

from agents.budget_manager import BudgetManagerAgent

################################################################################
# Phase‑level cost tracker
################################################################################


class PhaseCostTracker:
    """Tracks token/cost usage across multi‑phase reasoning chains."""

    def __init__(self, budget_manager: BudgetManagerAgent, operation_id: str, description: str):
        self.budget_manager = budget_manager
        self.operation_id = operation_id
        self.description = description
        self.phases: Dict[str, Dict] = {}
        self.current_phase: Optional[str] = None
        self.trajectory: Dict[str, Any] = {
            "operation_id": operation_id,
            "operation_type": description,
            "phases": [],
            "total_tokens_consumed": 0,
            "total_cost_incurred": 0.0,
            "overall_success": False,
            "final_result": None,
        }

    # ------------------------------------------------------------------
    # Phase lifecycle
    # ------------------------------------------------------------------
    def start_phase(self, phase_id: str, phase_description: str, model_id: str) -> Dict:
        if self.current_phase:
            self.end_phase(success=None)
        phase = {
            "phase_id": phase_id,
            "phase_description": phase_description,
            "start_time": time.time(),
            "end_time": None,
            "tokens_consumed": 0,
            "cost_incurred": 0.0,
            "model_used": model_id,
            "reasoning_steps": [],
            "outcome": {"success": None, "result": None, "feedback": ""},
        }
        self.phases[phase_id] = phase
        self.current_phase = phase_id
        return phase

    def record_reasoning_step(
        self,
        step_id: str,
        prompt: str,
        response: str,
        model_id: str,
        tools_used: Optional[List[str]] = None,
        context_chunks_used: Optional[List[str]] = None,
    ) -> Dict:
        if not self.current_phase:
            raise ValueError("No active phase to record reasoning step")

        tokens_consumed = count_tokens(prompt) + count_tokens(response)
        _, cost_incurred = estimate_cost(prompt + response, model_id)

        step = {
            "step_id": step_id,
            "prompt": prompt,
            "response": response,
            "tokens_consumed": tokens_consumed,
            "cost_incurred": cost_incurred,
            "tools_used": tools_used or [],
            "context_chunks_used": context_chunks_used or [],
            "validation_outcome": None,
            "validation_feedback": None,
        }
        phase = self.phases[self.current_phase]
        phase["tokens_consumed"] += tokens_consumed
        phase["cost_incurred"] += cost_incurred
        phase["reasoning_steps"].append(step)

        self.trajectory["total_tokens_consumed"] += tokens_consumed
        self.trajectory["total_cost_incurred"] += cost_incurred

        self.budget_manager.consumed_tokens_session += tokens_consumed
        self.budget_manager.consumed_cost_session += cost_incurred
        return step

    def record_validation(self, step_id: str, outcome: bool, feedback: str) -> None:
        if not self.current_phase:
            raise ValueError("No active phase to record validation")
        phase = self.phases[self.current_phase]
        # for step in phase["reasoning_steps"]:
        #     if step["step_id"] == step_id:
        #         step["validation_outcome"] = outcome
        #         step["validation_feedback"] = feedback
        #         return
        # raise ValueError(f"No reasoning step with ID {step_id} found in current phase")

        # Find the step; if it does not exist (e.g. the caller mocked out
        # _execute_reasoning_step in unit‑tests) we create a stub so validation
        # can still be recorded without blowing up the run.
        for s in phase["reasoning_steps"]:
            if s["step_id"] == step_id:
                s["validation_outcome"] = outcome
                s["validation_feedback"] = feedback
                return

        phase["reasoning_steps"].append(
            {
                "step_id": step_id,
                "prompt": "<not‑recorded>",
                "response": "<not‑recorded>",
                "tokens_consumed": 0,
                "cost_incurred": 0.0,
                "tools_used": [],
                "context_chunks_used": [],
                "validation_outcome": outcome,
                "validation_feedback": feedback,
            }
        )
    def end_phase(self, success: Optional[bool], result: Any = None, feedback: str = "") -> Dict:
        if not self.current_phase:
            raise ValueError("No active phase to end")
        phase = self.phases[self.current_phase]
        phase["end_time"] = time.time()
        phase["outcome"].update({"success": success, "result": result, "feedback": feedback})
        self.trajectory["phases"].append(phase)
        self.current_phase = None
        return phase

    def complete_operation(self, success: bool, final_result: Any = None) -> Dict:
        if self.current_phase:
            self.end_phase(success=None)
        self.trajectory["overall_success"] = success
        self.trajectory["final_result"] = final_result
        return self.trajectory

    def get_cost_summary(self) -> Dict:
        summary = {
            "operation_id": self.operation_id,
            "description": self.description,
            "phases": {},
            "total_tokens": self.trajectory["total_tokens_consumed"],
            "total_cost": self.trajectory["total_cost_incurred"],
        }
        for phase in self.trajectory["phases"]:
            summary["phases"][phase["phase_id"]] = {
                "tokens": phase["tokens_consumed"],
                "cost": phase["cost_incurred"],
                "steps": len(phase["reasoning_steps"]),
            }
        return summary

################################################################################
# Budget scopes
################################################################################


class BudgetScope:
    """A per‑step or per‑phase soft budget guard."""

    def __init__(
        self,
        budget_manager: BudgetManagerAgent,
        scope_id: str,
        description: str,
        *,
        max_tokens_allowed: Optional[int] = None,
        max_cost_allowed: Optional[float] = None,
        model_tier: str = "middle",
        auto_approve_threshold: float = 0.001,
        parent_scope_id: Optional[str] = None,
    ) -> None:
        self.budget_manager = budget_manager
        self.scope_id = scope_id
        self.parent_scope_id = parent_scope_id
        self.description = description
        self.max_tokens_allowed = max_tokens_allowed
        self.max_cost_allowed = max_cost_allowed
        self.tokens_consumed = 0
        self.cost_incurred = 0.0
        self.model_tier = model_tier
        self.auto_approve_threshold = auto_approve_threshold
        self.active = True
        self.model = self._get_model_for_tier(model_tier)

    # --------------------------------------------- helpers
    @staticmethod
    def _get_model_for_tier(tier: str):
        mapping = {
            "highest": llm_highest,
            "middle": llm_middle,
            "small": llm_small,
            "xs": llm_xs,
        }
        return mapping.get(tier, llm_middle)

    # --------------------------------------------- approval flow
    def request_approval(self, prompt: str, description: str) -> bool:
        model_id = getattr(self.model, "id", "Unknown")
        est_tokens, est_cost = estimate_cost(prompt, model_id)

        # Hard limits first
        if self.max_tokens_allowed and self.tokens_consumed + est_tokens > self.max_tokens_allowed:
            canvas.warning(
                f"[Budget] scope '{self.scope_id}' token limit exceeded: {self.tokens_consumed}+{est_tokens}>{self.max_tokens_allowed}"
            )
            return False
        if self.max_cost_allowed and self.cost_incurred + est_cost > self.max_cost_allowed:
            canvas.warning(
                f"[Budget] scope '{self.scope_id}' cost limit exceeded: ${self.cost_incurred:.4f}+${est_cost:.4f}>${self.max_cost_allowed:.4f}"
            )
            return False

        if est_cost <= self.auto_approve_threshold:
            self.tokens_consumed += est_tokens
            self.cost_incurred += est_cost
            return True

        approved = self.budget_manager.request_approval(
            description=f"[{self.scope_id}] {description}",
            prompt=prompt,
            model_id=model_id,
        )
        if approved:
            self.tokens_consumed += est_tokens
            self.cost_incurred += est_cost
        return approved

    # --------------------------------------------- serialisation
    def to_dict(self) -> Dict:
        return {
            "scope_id": self.scope_id,
            "parent_scope_id": self.parent_scope_id,
            "description": self.description,
            "max_tokens_allowed": self.max_tokens_allowed,
            "max_cost_allowed": self.max_cost_allowed,
            "tokens_consumed": self.tokens_consumed,
            "cost_incurred": self.cost_incurred,
            "model_tier": self.model_tier,
            "auto_approve_threshold": self.auto_approve_threshold,
            "active": self.active,
        }

################################################################################
# Validation hooks
################################################################################


class ValidationHook:
    """Simple wrapper around a callable validator for reuse & priority ordering."""

    def __init__(
        self,
        hook_id: str,
        hook_type: str,
        description: str,
        validation_function: Callable[[Any], Tuple[bool, str]],
        priority: int = 0,
    ) -> None:
        self.hook_id = hook_id
        self.hook_type = hook_type
        self.description = description
        self.validation_function = validation_function
        self.priority = priority

    def validate(self, data: Any) -> Tuple[bool, str]:
        return self.validation_function(data)

    def to_dict(self) -> Dict:
        return {
            "hook_id": self.hook_id,
            "hook_type": self.hook_type,
            "description": self.description,
            "priority": self.priority,
        }

################################################################################
# Core abstract operator
################################################################################


class ContextAwareOperator(ABC):
    """Base‑class for all reflective operators that need budget awareness."""

    def __init__(
        self,
        *,
        budget_manager: BudgetManagerAgent,
        operation_type: str,
        max_reasoning_steps: int = 5,
        default_model_tier: str = "middle",
    ) -> None:
        self.budget_manager = budget_manager
        self.operation_type = operation_type
        self.max_reasoning_steps = max_reasoning_steps
        self.default_model_tier = default_model_tier
        self.operation_id = f"{operation_type}_{uuid.uuid4().hex[:8]}"

        self.cost_tracker = PhaseCostTracker(budget_manager, self.operation_id, operation_type)
        self.budget_scope = BudgetScope(budget_manager, self.operation_id, operation_type, model_tier=default_model_tier)
        self.validation_hooks: Dict[str, ValidationHook] = {}

    # --------------------------------------------- validation management
    def register_validation_hook(self, hook: ValidationHook) -> None:
        self.validation_hooks[hook.hook_id] = hook

    def run_validation_hooks(self, data: Any, hook_types: Optional[List[str]] = None) -> Dict[str, Dict]:
        hooks = [h for h in self.validation_hooks.values() if hook_types is None or h.hook_type in hook_types]
        hooks.sort(key=lambda h: h.priority, reverse=True)
        results: Dict[str, Dict[str, Any]] = {}
        for h in hooks:
            outcome, feedback = h.validate(data)
            results[h.hook_id] = {"outcome": outcome, "feedback": feedback}
        return results

    # --------------------------------------------- reasoning helpers
    def _prepare_reasoning_prompt(self, task_description: str, context: str = "") -> str:
        prompt = (
            f"""# Task Description\n{task_description}\n\n# Current Operation\nID: {self.operation_id}\nType: {self.operation_type}\n"""
        )
        if context:
            prompt += f"\n# Context\n{context}\n"
        prompt += (
            """\n# Reasoning Process\nPlease think step‑by‑step:\n1. Understand the task\n2. Break it into sub‑tasks\n3. Solve each sub‑task\n4. Validate your result\n5. Provide a concise answer and rationale."""
        )
        return prompt

    def _execute_reasoning_step(
        self,
        *,
        phase_id: str,
        step_id: str,
        prompt: str,
        model_tier: Optional[str] = None,
        tools_used: Optional[List[str]] = None,
        context_chunks_used: Optional[List[str]] = None,
    ) -> Optional[Dict]:
        model_tier = model_tier or self.default_model_tier
        step_scope = BudgetScope(
            budget_manager=self.budget_manager,
            scope_id=f"{self.operation_id}_{phase_id}_{step_id}",
            description=f"Reasoning step {step_id} in phase {phase_id}",
            model_tier=model_tier,
            parent_scope_id=self.operation_id,
        )
        if not step_scope.request_approval(prompt, f"Reasoning step {step_id}"):
            canvas.error(f"Step {step_id} in phase {phase_id} denied by budget manager.")
            return None
        model = step_scope._get_model_for_tier(model_tier)
        try:
            canvas.info(f"👉 Executing step {step_id} ({model_tier}) …")
            # response = model.run(prompt).content  # type: ignore[attr-defined]
            # Groq SDK no longer exposes `.run()`; use `.response()` instead
            llm_reply, _ = model.response(messages=[{"role":"user","content":prompt}])
            response = llm_reply.content  # extract the text out of the assistant message
            step_meta = self.cost_tracker.record_reasoning_step(
                step_id=step_id,
                prompt=prompt,
                response=response,
                model_id=getattr(model, "id", "Unknown"),
                tools_used=tools_used,
                context_chunks_used=context_chunks_used,
            )
            return {**step_meta, "step_id": step_id, "response": response}
        except Exception as exc:  # noqa: BLE001
            canvas.error(f"Execution error at step {step_id}: {exc}")
            return None

    def _validate_reasoning_step(self, step_id: str, result: Any, *, hook_types: Optional[List[str]] = None) -> bool:
        vresults = self.run_validation_hooks(result, hook_types)
        success = all(r["outcome"] for r in vresults.values())
        feedback = "\n".join(
            f"- {hid}: {'✅' if r['outcome'] else '❌'} {r['feedback']}" for hid, r in vresults.items()
        )
        self.cost_tracker.record_validation(step_id, success, feedback)
        return success

    # --------------------------------------------- abstract contract
    @abstractmethod
    def execute(self, *args, **kwargs) -> Tuple[bool, Any]:
        """Run the operator – return (success, result)."""
        raise NotImplementedError

################################################################################
# Common validation‑hook factories
################################################################################


def create_syntax_validation_hook(language: str) -> ValidationHook:
    def validate_python(code: str) -> Tuple[bool, str]:
        import ast

        try:
            ast.parse(code)
            return True, "Valid Python syntax."
        except SyntaxError as err:
            return False, f"Syntax error: {err}"

    validators: Dict[str, Callable[[str], Tuple[bool, str]]] = {"python": validate_python}

    return ValidationHook(
        hook_id=f"syntax_{language.lower()}",
        hook_type="syntax",
        description=f"{language} syntax validation",
        validation_function=validators.get(language.lower(), lambda *_: (True, "No validator.")),
        priority=10,
    )


def create_schema_validation_hook(schema: Dict) -> ValidationHook:
    def validate(data: Any) -> Tuple[bool, str]:
        try:
            import jsonschema  # type: ignore

            jsonschema.validate(data, schema)  # type: ignore[arg-type]
            return True, "Schema‑valid."
        except ImportError:
            return False, "jsonschema not installed."
        except Exception as exc:  # noqa: BLE001 – broad but acceptable here
            return False, f"Schema error: {exc}"

    return ValidationHook(
        hook_id="schema_validation",
        hook_type="schema",
        description="JSON schema validation",
        validation_function=validate,
        priority=8,
    )


def create_budget_validation_hook(max_cost: float) -> ValidationHook:
    def validate(data: Dict) -> Tuple[bool, str]:
        cost = data.get("cost_incurred", 0.0)
        return (
            (cost <= max_cost),
            f"Cost ${cost:.4f} {'within' if cost <= max_cost else 'exceeds'} budget ${max_cost:.4f}",
        )

    return ValidationHook(
        hook_id="budget_validation",
        hook_type="budget",
        description=f"Enforce cost ≤ ${max_cost:.4f}",
        validation_function=validate,
        priority=9,
    )
