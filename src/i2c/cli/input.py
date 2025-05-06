# /from i2c/cli/input.py
# Handles advanced interactive input with autocomplete for the Alive CLI.

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

# Default suggestions (could be extended later by agents)
idea_completer = WordCompleter([
    "web app",
    "cli tool",
    "api server",
    "dashboard",
    "automation script",
    "--help",
    "data pipeline",
    "chatbot",
], ignore_case=True)

session = PromptSession("🎯 Enter your project idea: ", completer=idea_completer)

def get_project_idea() -> str:
    """
    Prompts user to enter a project idea with smart autocomplete.
    Returns the user's input as a clean string.
    """
    try:
        idea = session.prompt().strip()
        return idea
    except (KeyboardInterrupt, EOFError):
        print("\n❌ Input interrupted. Exiting.")
        return ""
