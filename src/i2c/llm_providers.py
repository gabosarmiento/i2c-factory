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
        id="meta-llama/llama-4-maverick-17b-128e-instruct",
        api_key=GROQ_API_KEY,
        temperature=0.5
    )

    llm_middle = Groq(
        id="meta-llama/llama-4-scout-17b-16e-instruct",
        api_key=GROQ_API_KEY,
        temperature=0.2
    )

    llm_small = Groq(
        id="llama-guard-3-8b",
        api_key=GROQ_API_KEY,
        temperature=0.2
    )

    llm_xs = Groq(
        id="llama3-8b-8192",
        api_key=GROQ_API_KEY,
        temperature=0.2
    )

    print("[INFO]: Groq LLM providers initialized successfully.")
    return llm_highest, llm_middle, llm_small, llm_xs

llm_highest, llm_middle, llm_small, llm_xs = initialize_groq_providers()

# --- Destructor fix ---
import groq._base_client
groq._base_client.SyncHttpxClientWrapper.__del__ = lambda self: None

def make_tracked_request(model, messages, budget_manager=None):
    """
    Make a request to the LLM and track token usage.
    
    Args:
        model: The Agno model instance
        messages: List of message dicts for the chat
        budget_manager: Optional BudgetManagerAgent for tracking
        
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
        
        # Track usage if budget manager provided
        if budget_manager and hasattr(budget_manager, 'track_usage'):
            # Join the messages for tracking
            prompt = "\n".join([msg.get('content', '') for msg in messages])
            budget_manager.track_usage(
                prompt=prompt,
                response=response_text,
                model_id=full_model_id
            )
        
        return response_text, total_tokens, cost
        
    except Exception as e:
        print(f"Error in tracked request: {e}")
        # Return a safe fallback
        return "", 0, 0.0
    
def _cleanup_groq_clients():
    for model in (llm_highest, llm_middle, llm_small, llm_xs):
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
