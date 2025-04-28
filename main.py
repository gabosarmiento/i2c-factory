# /main.py
# Main entry point for the Idea-to-Code Factory application.

import os
# --- <<< Set Tokenizer Parallelism Env Var >>> ---
# Set before other imports that might use tokenizers (like sentence-transformers via agents)
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# --- <<< End Setting Env Var >>> ---

import sys # Keep sys import if needed elsewhere, though not used directly here now
from dotenv import load_dotenv

# Import the main session execution function FROM THE WORKFLOW PACKAGE
from workflow import start_factory_session # Should work due to __init__.py
from cli.ascii import show_banner # Keep the banner if desired
from config.config import load_groq_api_key # Keep API key loading

def load_environment():
    """Loads environment variables from a .env file."""
    load_dotenv()
    print("🔑 Environment variables loaded (if .env file exists).")
    try:
        load_groq_api_key() # Validate GROQ_API_KEY presence
        print("   ✅ GROQ_API_KEY found.")
        return True
    except ValueError as e:
        print(f"   {e}") # Print the error message from config
        return False # Stop if key is missing

# --- Main Execution Block ---
if __name__ == "__main__":
    print("--- Application Start ---")
    show_banner() # Show banner at the start
    if load_environment():
        # Call the primary session function from the workflow package
        start_factory_session()
    else:
        print("❌ Workflow aborted due to missing environment configuration.")
    print("--- Application End ---")

