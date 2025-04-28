# /agents/budget_manager.py
# Agent responsible for managing token budget and cost estimation.

import os
from workflow.utils import estimate_cost, count_tokens, MODEL_PRICING_PER_1K_TOKENS # Import utilities
from cli.controller import canvas # Import canvas for user interaction

class BudgetManagerAgent:
    """
    Central agent that estimates token usage & cost for any LLM prompt,
    asks the user to approve budgets, and tracks cumulative consumption
    across the session.
    """
    def __init__(self, session_budget: float | None = None):
        """
        Initializes the Budget Manager.

        Args:
            session_budget: An optional overall budget for the session in dollars.
        """
        self.canvas = canvas # Use the global canvas instance
        self.pricing = MODEL_PRICING_PER_1K_TOKENS # Use pricing from utils
        self.count_tokens = count_tokens # Use token counter from utils
        self.consumed_tokens_session = 0
        self.consumed_cost_session = 0.0
        self.session_budget = session_budget
        print(f"💰 [BudgetManagerAgent] Initialized. Session budget: ${session_budget if session_budget is not None else 'Unlimited'}")

    def estimate(self, prompt: str, model_id: str) -> tuple[int, float]:
        """Estimate tokens and cost for a specific prompt and model."""
        # Note: This estimates input cost only. Output cost is harder to predict.
        # We could apply a multiplier (e.g., assume output is 2x input) for a rougher total estimate.
        # For now, estimate based on input prompt.
        est_tokens, est_cost = estimate_cost(prompt, model_id)
        return est_tokens, est_cost

    def _check_session_budget(self, estimated_cost: float) -> bool:
        """Checks if the estimated cost exceeds the session budget."""
        if self.session_budget is None:
            return True # No budget limit
        return (self.consumed_cost_session + estimated_cost) <= self.session_budget

    def request_approval(self, description: str, prompt: str, model_id: str) -> bool:
        """
        Estimates cost, checks session budget (if set), prompts user for approval,
        and updates consumed totals if approved.

        Args:
            description: A brief description of the operation requiring budget.
            prompt: The prompt text to estimate cost for.
            model_id: The ID of the LLM model that will be used.

        Returns:
            True if the operation is approved (or no approval needed), False otherwise.
        """
        est_tokens, est_cost = self.estimate(prompt, model_id)

        # --- Simple Threshold Logic (Optional - Avoid asking for tiny costs) ---
        APPROVAL_THRESHOLD_COST = 0.001 # Example: Don't ask if cost is less than $0.001
        if est_cost < APPROVAL_THRESHOLD_COST:
             # Silently approve very small costs, but still track them
             self.consumed_tokens_session += est_tokens
             self.consumed_cost_session += est_cost
             # canvas.info(f"[Budget] Auto-approved low cost operation: {description} (~${est_cost:.6f})") # Optional log
             return True
        # --- End Threshold Logic ---

        # --- Session Budget Check ---
        if not self._check_session_budget(est_cost):
            self.canvas.error(
                f"[Budget] Estimated cost (${est_cost:.6f}) for '{description}' exceeds remaining session budget "
                f"(${self.session_budget - self.consumed_cost_session:.6f}). Operation aborted."
            )
            return False
        # --- End Session Budget Check ---

        # --- User Confirmation ---
        self.canvas.warning(
            f"[Budget] Operation '{description}' will use model '{model_id}' "
            f"and consume an estimated {est_tokens} prompt tokens (~${est_cost:.6f})."
        )
        # Display session total if budget is set
        if self.session_budget is not None:
             self.canvas.info(f"  Session total cost so far: ${self.consumed_cost_session:.6f} / ${self.session_budget:.6f}")

        ans = self.canvas.get_user_input("Approve this cost? (y/n): ").strip().lower()
        if ans in ('y','yes'):
            self.consumed_tokens_session += est_tokens
            self.consumed_cost_session += est_cost
            self.canvas.info(f"[Budget] Approved. Session cost updated: ${self.consumed_cost_session:.6f}")
            return True
        else:
            self.canvas.error("[Budget] Operation aborted by user.")
            return False
        # --- End User Confirmation ---

    def get_session_consumption(self) -> tuple[int, float]:
        """Returns the total tokens and cost consumed in the session so far."""
        return self.consumed_tokens_session, self.consumed_cost_session

# Instantiate the agent globally? Or better in session.py?
# Let's instantiate in session.py to potentially pass session budget from args later.
# budget_manager = BudgetManagerAgent() # Removed global instance

