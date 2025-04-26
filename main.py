# /main.py
# Main entry point for the i2c Alive Factory CLI

import os
import sys
from dotenv import load_dotenv

from config.config import load_groq_api_key
from cli.ascii import show_banner
from workflow import start_factory_session

def main():
    """
    Bootstraps the environment and launches the Alive Factory workflow.
    """
    # 1. Load environment variables
    load_dotenv()
    try:
        load_groq_api_key()  # Validate GROQ_API_KEY presence
    except ValueError as e:
        print(f"[ERROR]: {e}")
        sys.exit(1)

    # 2. Show banner and start workflow
    show_banner()
    start_factory_session()


if __name__ == "__main__":
    main()
