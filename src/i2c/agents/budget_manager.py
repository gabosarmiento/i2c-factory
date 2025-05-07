# agents/budget_manager.py
# Enhanced to integrate with Agno's built-in metrics

import os
from typing import Optional, Tuple, Dict, Any, Union
from agno.agent import Agent, RunResponse
from agno.agent.metrics import SessionMetrics

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
    Enhanced to integrate with Agno's built-in metrics.
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
        
        # Agno metrics integration
        self.agno_metrics: Optional[SessionMetrics] = None
        
        # Auto-approval threshold (requests under this cost are auto-approved)
        self.auto_approve_threshold = auto_approve_threshold
        
        # Load budget configuration if available
        self._load_config()
        
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
    
    def update_from_agno_metrics(self, agent: Agent):
        """
        Update budget tracking using Agno's built-in metrics.
        
        Args:
            agent: The Agno agent to extract metrics from
        """
        if not agent.session_metrics:
            return
            
        # Store Agno metrics for reporting
        self.agno_metrics = agent.session_metrics
        
        # Update total token counts from Agno
        new_tokens = agent.session_metrics.total_tokens - self.consumed_tokens_session
        if new_tokens <= 0:
            return
            
        # Calculate cost based on Agno tracked tokens and the agent's model
        model_id = getattr(agent.model, 'id', 'Unknown')
        if not model_id.startswith('groq/'):
            model_id = f"groq/{model_id}"
            
        _, cost = estimate_cost("", model_id)  # Just get cost per token
        new_cost = (new_tokens / 1000) * (cost * 1000)  # Convert to per-token cost
        
        # Update session totals
        self.consumed_tokens_session = agent.session_metrics.total_tokens
        self.consumed_cost_session += new_cost
        
        # Update provider-specific stats
        provider = self._determine_provider(model_id)
        self.provider_stats[provider]['tokens'] += new_tokens
        self.provider_stats[provider]['cost'] += new_cost
        self.provider_stats[provider]['calls'] += 1
        
        canvas.info(f"💰 Updated from Agno metrics: +{new_tokens} tokens, +${new_cost:.6f}")
    
    def update_from_run_response(self, response: RunResponse, model_id: str):
        """
        Update budget tracking from a RunResponse object.
        
        Args:
            response: The RunResponse to extract metrics from
            model_id: The model identifier
        """
        if not response.metrics:
            return
            
        # Extract metrics from RunResponse
        total_tokens = 0
        if isinstance(response.metrics, dict):
            # Sum up token counts from the metrics dictionary
            if 'total_tokens' in response.metrics:
                total_tokens = sum(response.metrics['total_tokens'])
            elif 'input_tokens' in response.metrics and 'output_tokens' in response.metrics:
                input_tokens = sum(response.metrics['input_tokens']) if isinstance(response.metrics['input_tokens'], list) else response.metrics['input_tokens']
                output_tokens = sum(response.metrics['output_tokens']) if isinstance(response.metrics['output_tokens'], list) else response.metrics['output_tokens']
                total_tokens = input_tokens + output_tokens
        
        if total_tokens <= 0:
            return
            
        # Calculate cost based on tracked tokens
        _, cost_per_1k = estimate_cost("", model_id)  # Just get cost per token
        new_cost = (total_tokens / 1000) * cost_per_1k  # Convert to per-token cost
        
        # Update session totals
        self.consumed_tokens_session += total_tokens
        self.consumed_cost_session += new_cost
        
        # Update provider-specific stats
        provider = self._determine_provider(model_id)
        self.provider_stats[provider]['tokens'] += total_tokens
        self.provider_stats[provider]['cost'] += new_cost
        self.provider_stats[provider]['calls'] += 1
        
        canvas.info(f"💰 Tracked from RunResponse: {total_tokens} tokens, ${new_cost:.6f}")
    
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
            from i2c.workflow.utils import count_tokens, estimate_cost
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
        from i2c.workflow.utils import estimate_cost
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
        tokens = self.consumed_tokens_session
        cost = self.consumed_cost_session
        
        # If we have Agno metrics and they report higher token usage, use those
        if self.agno_metrics is not None:
            if self.agno_metrics.total_tokens > tokens:
                tokens = self.agno_metrics.total_tokens
        
        return tokens, cost
    
    def get_provider_stats(self) -> dict:
        """Get detailed provider statistics."""
        return self.provider_stats
    
    def get_summary(self) -> str:
        """Get a formatted summary of budget usage."""
        tokens, cost = self.get_session_consumption()
        
        summary = f"""
💰 Budget Usage Summary
----------------------
Session Total: {tokens} tokens, ${cost:.6f}
Budget Limit: ${self.session_budget if self.session_budget else 'Unlimited'}
Remaining: ${f"{self.session_budget - cost:.6f}" if self.session_budget else "Unlimited"}

Provider Breakdown:
"""
        for provider, stats in self.provider_stats.items():
            if stats['calls'] > 0:
                summary += f"  {provider}: {stats['calls']} calls, {stats['tokens']} tokens, ${stats['cost']:.6f}\n"
        
        # Add Agno metrics details if available
        if self.agno_metrics:
            summary += "\nAgno Metrics Detail:\n"
            summary += f"  Input Tokens: {self.agno_metrics.input_tokens}\n"
            summary += f"  Output Tokens: {self.agno_metrics.output_tokens}\n"
            
            if self.agno_metrics.prompt_tokens > 0 or self.agno_metrics.completion_tokens > 0:
                summary += f"  Prompt Tokens: {self.agno_metrics.prompt_tokens}\n"
                summary += f"  Completion Tokens: {self.agno_metrics.completion_tokens}\n"
                
            if self.agno_metrics.reasoning_tokens > 0:
                summary += f"  Reasoning Tokens: {self.agno_metrics.reasoning_tokens}\n"
                
            if self.agno_metrics.time is not None:
                summary += f"  Response Time: {self.agno_metrics.time:.2f}s\n"
        
        return summary