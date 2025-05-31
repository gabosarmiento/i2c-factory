# /llm_providers.py

import os

import atexit
import httpx
from httpx import Client
from dotenv import load_dotenv

from agno.models.groq import Groq
from i2c.agents.budget_manager import BudgetManagerAgent  # Optional

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file.")

# /llm_providers.py
# Updated section - add this method to the file after initialize_groq_providers()
                
def initialize_groq_providers():
    print("[INFO]: Initializing Groq LLM providers…")

    llm_highest = Groq(
        # id="meta-llama/llama-4-maverick-17b-128e-instruct",
        id="llama-3.1-8b-instant",
        api_key=GROQ_API_KEY,
        temperature=0.5
    )
    
    llm_middle_alt = Groq(
        # id="meta-llama/llama-guard-4-12b",
        id="llama-3.3-70b-versatile",
        api_key=GROQ_API_KEY,
        temperature=0.5
    )

    llm_middle = Groq(
        # id="meta-llama/llama-4-scout-17b-16e-instruct",
        id="llama-3.1-8b-instant",
        api_key=GROQ_API_KEY,
        temperature=0.2
    )

    llm_small = Groq(
        id="llama-3.1-8b-instant",
        api_key=GROQ_API_KEY,
        temperature=0.2
    )
    
    llm_deepseek = Groq(
        id="deepseek-r1-distill-llama-70b",
        #id="llama-3.1-8b-instant",
        api_key=GROQ_API_KEY,
        temperature=0.4,
    )
    
    llm_lightweight = Groq(
        id="gemma2-9b-it",
        api_key=GROQ_API_KEY,
        temperature=0.2
    )


    print("[INFO]: Groq LLM providers initialized successfully.")
    return llm_highest, llm_middle, llm_middle_alt, llm_small, llm_deepseek, llm_lightweight

llm_highest, llm_middle, llm_middle_alt, llm_small, llm_deepseek, llm_ligthweight = initialize_groq_providers()

# --- Destructor fix ---
import groq._base_client
groq._base_client.SyncHttpxClientWrapper.__del__ = lambda self: None

# Enhanced make_tracked_request function for llm_providers.py

def make_tracked_request(model, messages, budget_manager=None, agent=None):
    """
    Make a request to the LLM and track token usage with enhanced Agno integration.
    
    Args:
        model: The Agno model instance
        messages: List of message dicts for the chat
        budget_manager: Optional BudgetManagerAgent for tracking
        agent: Optional Agno Agent instance for extracting metrics
        
    Returns:
        tuple: (response_text, tokens_used, cost)
    """
    try:
        # Make the actual API call using Agno's correct method
        response = model.create_completion(
            messages=messages,
            max_tokens=None,  # Let model decide based on context
        )
        
        # Extract response text
        response_text = response.choices[0].message.content
        
        # Get actual token counts from response
        prompt_tokens = getattr(response.usage, 'prompt_tokens', 0)
        completion_tokens = getattr(response.usage, 'completion_tokens', 0)
        total_tokens = getattr(response.usage, 'total_tokens', prompt_tokens + completion_tokens)
        
        # Calculate cost
        model_id = getattr(model, 'id', 'Unknown')
        full_model_id = f"groq/{model_id}" if not model_id.startswith('groq/') else model_id
        
        # Import here to avoid circular dependency
        from i2c.workflow.utils import MODEL_PRICING_PER_1K_TOKENS, DEFAULT_PRICE_PER_1K
        
        price_per_1k = MODEL_PRICING_PER_1K_TOKENS.get(full_model_id, DEFAULT_PRICE_PER_1K)
        cost = (total_tokens / 1000) * price_per_1k
        
        # If we have an Agno Agent, update from its metrics
        if agent is not None and hasattr(agent, 'run_response') and agent.run_response is not None:
            # If budget manager provided, update from Agno agent metrics
            if budget_manager and hasattr(budget_manager, 'update_from_run_response'):
                budget_manager.update_from_run_response(agent.run_response, full_model_id)
                
            # If agent has session metrics, update from those too
            if hasattr(agent, 'session_metrics') and agent.session_metrics is not None:
                if budget_manager and hasattr(budget_manager, 'update_from_agno_metrics'):
                    budget_manager.update_from_agno_metrics(agent)
        
        # Track usage if budget manager provided (for backward compatibility)
        elif budget_manager and hasattr(budget_manager, 'track_usage'):
            # Join the messages for tracking
            prompt = "\n".join([msg.get('content', '') for msg in messages])
            budget_manager.track_usage(
                prompt=prompt,
                response=response_text,
                model_id=full_model_id,
                actual_tokens=total_tokens,
                actual_cost=cost
            )
        
        return response_text, total_tokens, cost
        
    except Exception as e:
        print(f"Error in tracked request: {e}")
        # Return a safe fallback
        return "", 0, 0.0
    
def _cleanup_groq_clients():
    for model in (llm_highest, llm_middle, llm_middle_alt, llm_small, llm_deepseek, llm_ligthweight):
        wrapper = getattr(model, "_client", None)
        if wrapper:
            try:
                if hasattr(wrapper, "close"):
                    wrapper.close()
            except Exception:
                pass
            inner = getattr(wrapper, "_client", None)
            if isinstance(inner, Client):
                try:
                    inner.close()
                except Exception:
                    pass

atexit.register(_cleanup_groq_clients)
