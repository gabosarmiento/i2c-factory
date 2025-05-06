# agents/budget_manager.py
# Update to track both OpenAI and Groq usage

import os
from typing import Optional, Tuple
from agno.agent import Agent

# Import cost estimation utilities  

# Import CLI controller for user interaction
from i2c.cli.controller import canvas

# Local fallback version to avoid circular dependency
def estimate_cost(text: str, model_id: str) -> tuple[int, float]:
    """Simple local cost estimation to avoid circular import."""
    tokens = len(text) // 4  # Estimate based on average 4 characters per token

    pricing = {
        "groq/llama-3.3-70b-versatile": 0.00059,
        "groq/llama-3.1-70b-versatile": 0.00059,
        "groq/llama-3.1-8b-instant": 0.00005,
        "groq/meta-llama/llama-4-maverick-17b-128e-instruct": 0.00030,
        "groq/meta-llama/llama-4-scout-17b-16e-instruct": 0.00025,
        "groq/llama-guard-3-8b": 0.00020,
        "groq/llama3-8b-8192": 0.00005,
        "gpt-4": 0.03000,
        "gpt-3.5-turbo": 0.00050,
    }

    price_per_1k = pricing.get(model_id, 0.00020)
    cost = round((tokens / 1000) * price_per_1k, 6)

    return tokens, cost


class BudgetManagerAgent:
    """
    Agent responsible for managing token usage and budget constraints.
    Enhanced to track both OpenAI and Groq API usage.
    """
    def __init__(self, session_budget: Optional[float] = None, auto_approve_threshold: float = 0.01):
        # Session-level tracking
        self.session_budget = session_budget  # Total budget for the session ($)
        self.consumed_tokens_session = 0      # Total tokens consumed
        self.consumed_cost_session = 0.0      # Total cost incurred ($)
        
        # Provider-specific tracking
        self.provider_stats = {
            'openai': {'tokens': 0, 'cost': 0.0, 'calls': 0},
            'groq': {'tokens': 0, 'cost': 0.0, 'calls': 0},
            'other': {'tokens': 0, 'cost': 0.0, 'calls': 0}
        }
        
        # Auto-approval threshold (requests under this cost are auto-approved)
        self.auto_approve_threshold = auto_approve_threshold
        
        # Load budget configuration if available
        self._load_config ()
        
        canvas.info(f"💰 [BudgetManagerAgent] Initialized. Session budget: ${self.session_budget if self.session_budget else 'Unlimited'}")
    
    def _load_config(self):
        """Load budget configuration from environment or config file."""
        if not self.session_budget:
            # Try to load from environment
            env_budget = os.getenv('SESSION_BUDGET')
            if env_budget:
                try:
                    self.session_budget = float(env_budget)
                except ValueError:
                    canvas.warning(f"Invalid SESSION_BUDGET value: {env_budget}")
    
    def _determine_provider(self, model_id: str) -> str:
        """Determine the provider from the model ID."""
        if model_id.startswith('groq/') or model_id.startswith('meta-llama/'):
            return 'groq'
        elif model_id.startswith('gpt'):
            return 'openai'
        else:
            return 'other'
    
    def track_usage(self, prompt: str, response: str, model_id: str, actual_tokens: int = None, actual_cost: float = None):
        """
        Track token usage for a completed API call.
        
        Args:
            prompt: The input prompt
            response: The API response
            model_id: The model identifier (e.g., 'groq/mixtral-8x7b')
            actual_tokens: Actual token count from API (optional)
            actual_cost: Actual cost from API (optional)
        """
        # Use actual values if provided, otherwise estimate
        if actual_tokens is not None and actual_cost is not None:
            tokens = actual_tokens
            cost = actual_cost
        else:
            # Fallback to estimation
            total_text = prompt + response
            tokens, cost = estimate_cost(total_text, model_id)
        
        # Update session totals
        self.consumed_tokens_session += tokens
        self.consumed_cost_session += cost
        
        # Update provider-specific stats
        provider = self._determine_provider(model_id)
        self.provider_stats[provider]['tokens'] += tokens
        self.provider_stats[provider]['cost'] += cost
        self.provider_stats[provider]['calls'] += 1
        
        # Log the usage
        canvas.info(f"💰 Tracked {provider} usage: {tokens} tokens, ${cost:.6f}")
    
    def request_approval(self, description: str, prompt: str, model_id: str) -> bool:
        """Request budget approval for an operation."""
        # Estimate cost
        token_estimate, cost_estimate = estimate_cost(prompt, model_id)
        provider = self._determine_provider(model_id)
        
        # Check if within budget
        if self.session_budget is not None:
            projected_total = self.consumed_cost_session + cost_estimate
            if projected_total > self.session_budget:
                canvas.warning(f"💸 [BudgetManagerAgent] Budget exceeded! Current: ${self.consumed_cost_session:.4f}, Requested: ${cost_estimate:.4f}, Budget: ${self.session_budget}")
                return False
        
        # Auto-approve small requests
        if cost_estimate <= self.auto_approve_threshold:
            canvas.info(f"💰 [BudgetManagerAgent] Auto-approved: {description} ({provider}, ~{token_estimate} tokens, ~${cost_estimate:.6f})")
            return True
        
        # Request user approval for larger operations
        approval_msg = (
            f"\n💰 Budget Approval Request:\n"
            f"Operation: {description}\n"
            f"Provider: {provider}\n"
            f"Model: {model_id}\n"
            f"Estimated tokens: {token_estimate}\n"
            f"Estimated cost: ${cost_estimate:.6f}\n"
            f"Current session total: ${self.consumed_cost_session:.4f}\n"
            f"Budget remaining: ${self.session_budget - self.consumed_cost_session:.4f if self.session_budget else 'Unlimited'}\n"
            f"\nApprove? [y/N]: "
        )
        
        user_response = canvas.get_user_input(approval_msg).strip().lower()
        approved = user_response == 'y'
        
        if approved:
            canvas.success(f"✅ [BudgetManagerAgent] Approved: {description}")
        else:
            canvas.warning(f"❌ [BudgetManagerAgent] Denied: {description}")
        
        return approved
    
    def get_session_consumption(self) -> Tuple[int, float]:
        """Get total session consumption."""
        return self.consumed_tokens_session, self.consumed_cost_session
    
    def get_provider_stats(self) -> dict:
        """Get detailed provider statistics."""
        return self.provider_stats
    
    def get_summary(self) -> str:
        """Get a formatted summary of budget usage."""
        summary = f"""
💰 Budget Usage Summary
----------------------
Session Total: {self.consumed_tokens_session} tokens, ${self.consumed_cost_session:.6f}
Budget Limit: ${self.session_budget if self.session_budget else 'Unlimited'}
Remaining: ${self.session_budget - self.consumed_cost_session:.6f if self.session_budget else 'Unlimited'}

Provider Breakdown:
"""
        for provider, stats in self.provider_stats.items():
            if stats['calls'] > 0:
                summary += f"  {provider}: {stats['calls']} calls, {stats['tokens']} tokens, ${stats['cost']:.6f}\n"
        
        return summary