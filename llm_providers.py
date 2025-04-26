# /llm_providers.py
# Defines and initializes the Groq LLM clients used across the i2c Alive Factory agents

import os
from dotenv import load_dotenv
from agno.models.groq import Groq

# Load environment variables from .env
load_dotenv()

# Retrieve the API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file. Please add it.")

# --- Instantiate Groq LLM models with appropriate temperatures ---
llm_highest = Groq(
    id="meta-llama/llama-4-maverick-17b-128e-instruct",
    api_key=GROQ_API_KEY,
    temperature=0.5  # Higher creativity for code generation
)

llm_middle = Groq(
    id="meta-llama/llama-4-scout-17b-16e-instruct",
    api_key=GROQ_API_KEY,
    temperature=0.2  # More deterministic for planning and clarification
)

llm_small = Groq(
    id="llama-guard-3-8b",
    api_key=GROQ_API_KEY,
    temperature=0.2  # Lightweight evaluation
)

llm_xs = Groq(
    id="llama3-8b-8192",
    api_key=GROQ_API_KEY,
    temperature=0.2  # Extra small model
)

print("[INFO]: Groq LLM providers initialized successfully.")

# --- Disable problematic destructor globally ---
# Monkey-patch SyncHttpxClientWrapper to avoid AttributeError in __del__
import groq._base_client

groq._base_client.SyncHttpxClientWrapper.__del__ = lambda self: None

# --- Cleanup handler to properly close underlying HTTP clients ---
import atexit
import httpx
from httpx import Client

def _cleanup_groq_clients():
    """
    Properly closes the underlying HTTP client wrappers to avoid destructor errors.
    """
    for model in (llm_highest, llm_middle, llm_small, llm_xs):
        wrapper = getattr(model, "_client", None)
        if wrapper:
            # Attempt to close wrapper if possible
            try:
                if hasattr(wrapper, "close"):
                    wrapper.close()
            except Exception:
                pass
            # Fallback: close internal httpx client
            inner = getattr(wrapper, "_client", None)
            if isinstance(inner, Client):
                try:
                    inner.close()
                except Exception:
                    pass

# Register cleanup at program exit
atexit.register(_cleanup_groq_clients)
