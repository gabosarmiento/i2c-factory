
import os
import yaml
from pathlib import Path

def load_config(config_path: Path = None):
    if config_path is None:
        config_path = Path(__file__).resolve().parents[3]  / "config.yaml"

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    return config

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
