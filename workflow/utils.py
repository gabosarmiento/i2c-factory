# /workflow/utils.py
# Shared utility functions for the workflow package.

import re
from pathlib import Path
try:
    import tiktoken  # For token counting
except ImportError:
    tiktoken = None  # No tiktoken, usaremos fallback
import typing

# Import CLI controller for logging within the helper
try:
    from cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_UTIL] {msg}")
        def error(self, msg): print(f"[ERROR_UTIL] {msg}")
    canvas = FallbackCanvas()

# --- Model Pricing (Example - Fill with actual Groq prices if known) ---
# Prices per 1 MILLION tokens (Input/Output often differ, use combined/average for simplicity initially)
# Find precise pricing on Groq's website. These are illustrative placeholders.
# Using price per 1k tokens for easier calculation in estimate_cost
MODEL_PRICING_PER_1K_TOKENS = {
    "groq/meta-llama/llama-4-maverick-17b-128e-instruct": 0.00010, # Example: $0.10 / 1M tokens -> $0.00010 / 1k
    "groq/meta-llama/llama-4-scout-17b-16e-instruct": 0.00008, # Example: $0.08 / 1M tokens -> $0.00008 / 1k
    "groq/llama-guard-3-8b": 0.00005, # Example: $0.05 / 1M tokens -> $0.00005 / 1k
    "groq/llama3-8b-8192": 0.00005, # Example: $0.05 / 1M tokens -> $0.00005 / 1k
    # Add other models used as needed
}
DEFAULT_PRICE_PER_1K = 0.00007 # Default fallback price

# --- Token Counting ---
# Use tiktoken - choose appropriate encoding (cl100k_base is common for GPT-4/3.5)
# Verify if Groq models align with a specific tiktoken encoding or provide their own count method.
try:
    # Attempt to get the encoding used by many modern models
    # encoding = tiktoken.get_encoding("cl100k_base")
    # Attempt to get the encoding used by many modern models (if tiktoken is available)
    if tiktoken is not None:
        encoding = tiktoken.get_encoding("cl100k_base")
    else:
        encoding = None
except Exception:
    # Fallback to a default if the preferred one isn't available
    try:
        encoding = tiktoken.encoding_for_model("gpt-4") # Or another common model
    except Exception:
        encoding = None # Cannot count tokens if no encoding works
        print("⚠️ Warning: tiktoken encoding not found. Token counts will be estimates (0).")

def count_tokens(text: str) -> int:
    """Counts tokens using tiktoken."""
    if encoding and text:
        try:
            return len(encoding.encode(text))
        except Exception as e:
            print(f"⚠️ Warning: tiktoken encoding failed: {e}")
            return 0 # Fallback
    return 0 # Return 0 if no encoding or empty text

# --- Cost Estimation ---
def estimate_cost(text: str, model_id: str) -> tuple[int, float]:
    """Estimates token count and cost for a given text and model."""
    tokens = count_tokens(text)
    # Use model-specific pricing if available, otherwise default
    price_per_1k = MODEL_PRICING_PER_1K_TOKENS.get(model_id, DEFAULT_PRICE_PER_1K)
    cost = round((tokens / 1000) * price_per_1k, 6)
    return tokens, cost

# --- File/Path Utilities ---
def sanitize_filename(name: str) -> str:
    """Removes or replaces characters unsafe for filenames/directory names."""
    name = name.strip()
    name = re.sub(r'[\\/*?:"<>|\s]+', '_', name)
    name = re.sub(r'[^\w\-_]', '', name)
    return name[:50] or "untitled_project"

def ensure_project_path(base_dir: Path, suggested_name: str) -> Path:
    """Creates a unique project path, appending numbers if necessary."""
    count = 0
    project_path = base_dir / suggested_name
    while project_path.exists():
        count += 1
        project_path = base_dir / f"{suggested_name}_{count}"
    return project_path

# --- safe_run REMOVED ---
# Retry/fallback logic is no longer handled by this utility.
# Use standard try/except blocks in calling code. Budget checks happen via BudgetManagerAgent.

