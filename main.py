# /main.py
# Main entry point for the Idea-to-Code Factory application.

import builtins
from llm_providers import initialize_groq_providers

# populate builtins.llm_* before any agents import them
(
    builtins.llm_highest,
    builtins.llm_middle,
    builtins.llm_small,
    builtins.llm_xs
) = initialize_groq_providers()

import os
import subprocess
import sys
from dotenv import load_dotenv

# Set tokenizer env var early
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# --- Core imports ---
from workflow import start_factory_session
from cli.ascii import show_banner
from config.config import load_groq_api_key

# --- Budget manager setup ---
from agents.budget_manager import BudgetManagerAgent
from llm_providers import initialize_groq_providers

def check_environment():
    """Check Python and dependency versions"""
    print("🔍 Running environment check...")
    result = subprocess.run([sys.executable, "scripts/check_versions.py"], capture_output=True)
    if result.returncode != 0:
        print("❌ Environment check failed!")
        print(result.stdout.decode())
        sys.exit(1)
    else:
        print("✅ Environment check passed.")

def load_environment():
    """Loads environment variables from .env file."""
    load_dotenv()
    print("🔑 Environment variables loaded (if .env file exists).")
    try:
        load_groq_api_key()
        print("   ✅ GROQ_API_KEY found.")
        return True
    except ValueError as e:
        print(f"   {e}")
        return False

def initialize_budget_manager():
    """Sets up and globally registers the budget manager."""
    global_budget_manager = BudgetManagerAgent(session_budget=10.0)  # $10 session budget
    import builtins
    builtins.global_budget_manager = global_budget_manager
    print("💰 Budget manager initialized with $10 session budget.")

# --- Main Execution ---
if __name__ == "__main__":
    print("--- Application Start ---")
    check_environment()
    show_banner()

    if load_environment():
        initialize_budget_manager()  # Optional, still safe to use if some agents track usage

        # ⬇️ Capture initialized models explicitly
        import builtins
        from llm_providers import initialize_groq_providers
        (
            builtins.llm_highest,
            builtins.llm_middle,
            builtins.llm_small,
            builtins.llm_xs
        ) = initialize_groq_providers()

        start_factory_session()
    else:
        print("❌ Workflow aborted due to missing environment configuration.")

    print("--- Application End ---")

