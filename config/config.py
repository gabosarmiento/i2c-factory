# /config.py
# Central configuration manager for API keys and settings.

import os

def load_groq_api_key() -> str:
    """
    Loads the GROQ_API_KEY from environment variables.

    Raises:
        ValueError if the key is not found.

    Returns:
        The Groq API Key as a string.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("❌ Missing GROQ_API_KEY. Please set it in your .env file.")
    return api_key

# (Optional: Later you can add loaders for OpenAI, Anthropic, etc.)
