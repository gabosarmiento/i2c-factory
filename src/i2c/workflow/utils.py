# Update the pricing structure to include actual Groq prices

import re
from pathlib import Path
try:
    import tiktoken  # For token counting
except ImportError:
    tiktoken = None  # No tiktoken, usaremos fallback
import typing

# Import CLI controller for logging within the helper
try:
    from i2c.cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_UTIL] {msg}")
        def error(self, msg): print(f"[ERROR_UTIL] {msg}")
    canvas = FallbackCanvas()

# --- Model Pricing (Updated with Groq pricing) ---
# Prices per 1 MILLION tokens (Input/Output often differ, use combined/average for simplicity initially)
# Groq pricing as of 2024 (check https://wow.groq.com/pricing/ for updates)
# Using price per 1k tokens for easier calculation in estimate_cost
MODEL_PRICING_PER_1K_TOKENS = {
    # Groq models
    "groq/llama-3.3-70b-versatile": 0.00059,  # $0.59/M tokens
    "groq/llama-3.1-70b-versatile": 0.00059,  # $0.59/M tokens
    "groq/llama-3.1-8b-instant": 0.00005,    # $0.05/M tokens
    "groq/mistral-saba-24b": 0.00079,     # $0.24/M tokens
    "groq/gemma2-9b-it": 0.00020,           # $0.20/M tokens
    "groq/gemma-7b-it": 0.00007,            # $0.07/M tokens
    
    # Your specific Groq models
    "groq/meta-llama/llama-4-maverick-17b-128e-instruct": 0.00030,  # Estimated
    "groq/meta-llama/llama-4-scout-17b-16e-instruct": 0.00025,      # Estimated
    "groq/llama-guard-3-8b": 0.00020,  # Estimated based on size
    "groq/llama3-8b-8192": 0.00005,    # Same as llama-3.1-8b
    
    # OpenAI models (for comparison)    "gpt-4": 0.03000,
    "gpt-3.5-turbo": 0.00050,
}
DEFAULT_PRICE_PER_1K = 0.00020  # Default fallback price

# --- Token Counting ---
def count_tokens(text: str, model: str = None) -> int:
    """
    Counts tokens using tiktoken for OpenAI models or character-based estimation for others.
        
    Args:
        text: The text to count tokens for
        model: The model name (e.g., 'groq/llama-3.1-8b' or 'gpt-4')
    
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    
    # For Groq models, use a character-based estimation
    # Groq typically uses ~4 characters per token for English text
    if model and model.startswith('groq/'):
        return len(text) // 4
    
    # For OpenAI models, use tiktoken if available
    if tiktoken and model and model.startswith('gpt'):
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception:
            pass
    
    # Fallback to character estimation
    return len(text) // 4

# --- Cost Estimation ---
def estimate_cost(text: str, model_id: str) -> tuple[int, float]:
    """Estimates token count and cost for a given text and model."""
    tokens = count_tokens(text, model_id)
    
    # Extract the base model ID without provider prefix for pricing lookup
    pricing_key = model_id
    
    # Use model-specific pricing if available, otherwise default
    price_per_1k = MODEL_PRICING_PER_1K_TOKENS.get(pricing_key, DEFAULT_PRICE_PER_1K)
    cost = round((tokens / 1000) * price_per_1k, 6)
    
    return tokens, cost

def sanitize_filename(name: str) -> str:
    """Sanitize a string to make it safe as a directory or file name."""
    import re
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

# --- Helper to parse model from API logs ---
def extract_model_from_groq_log(log_message: str) -> str:
    """Extract model name from Groq API log messages."""
    # Groq logs show: "INFO:httpx:HTTP Request: POST https://api.groq.com/openai/v1/chat/completions"
    # We need to extract the model from the actual API call or agent configuration
    
    # This is a simplified approach - in reality, you'd need to intercept the actual
    # model being used in the API call
    return "groq/llama-3.1-8b-instant"  # Default Groq model

def deduplicate_code_map(code_map: dict) -> dict:
    """
    Remove duplicate files from the code map.
    Prioritizes more detailed implementations and organized file paths.
    """
    # Create a clean copy of the code map
    clean_map = {}
    
    # Find base filenames without paths to detect duplicates
    base_names = {}
    for file_path, content in code_map.items():
        base_name = Path(file_path).name
        
        # If this is the first time seeing this base name, just record it
        if base_name not in base_names:
            base_names[base_name] = [file_path]
        else:
            base_names[base_name].append(file_path)
    
    # Process duplicates
    for base_name, paths in base_names.items():
        if len(paths) == 1:
            # No duplicate for this file, just add it
            clean_map[paths[0]] = code_map[paths[0]]
        else:
            canvas.warning(f"Found duplicate files for {base_name}: {paths}")
            
            # Prioritize files in test directories for test files
            if base_name.startswith("test_"):
                test_dir_paths = [p for p in paths if "test" in str(Path(p).parent).lower()]
                if test_dir_paths:
                    # Choose the first test directory path
                    chosen_path = test_dir_paths[0]
                    canvas.info(f"Selecting {chosen_path} as the test file")
                    clean_map[chosen_path] = code_map[chosen_path]
                    
                    # Log the dropped duplicates
                    for p in paths:
                        if p != chosen_path:
                            canvas.warning(f"Dropping duplicate test file: {p}")
                else:
                    # No test directory found, use the first path
                    chosen_path = paths[0]
                    canvas.info(f"No test directory found, using {chosen_path}")
                    clean_map[chosen_path] = code_map[chosen_path]
            else:
                # For non-test files, choose the one with more content
                longest_content = ""
                chosen_path = ""
                for p in paths:
                    if len(code_map[p]) > len(longest_content):
                        longest_content = code_map[p]
                        chosen_path = p
                
                if chosen_path:
                    canvas.info(f"Selecting {chosen_path} as it has the most content")
                    clean_map[chosen_path] = longest_content
                    
                    # Log the dropped duplicates
                    for p in paths:
                        if p != chosen_path:
                            canvas.warning(f"Dropping duplicate file: {p}")
    
    # Check if we actually reduced any duplicates
    if len(clean_map) < len(code_map):
        canvas.success(f"Removed {len(code_map) - len(clean_map)} duplicate files")
    
    return clean_map