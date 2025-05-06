# /from i2c/cli/recovery.py
# Provides error recovery options when an agent fails during workflow.

from rich.prompt import Prompt
from i2c.cli.view import print_warning, print_info, print_error

def offer_recovery(session, agent_name: str) -> str:
    """
    Offers recovery options when an agent fails.

    Args:
        session: The current CLI session.
        agent_name: Name of the agent that failed.

    Returns:
        User decision: "retry", "skip", or "abort"
    """
    print_error(session, f"Agent '{agent_name}' encountered an error.")
    print_warning(session, "You have the following options:")
    session.console.print(" [1] Retry the agent task")
    session.console.print(" [2] Skip and continue workflow")
    session.console.print(" [3] Abort workflow")

    while True:
        choice = Prompt.ask("Choose an option", choices=["1", "2", "3"], default="1")
        if choice == "1":
            print_info(session, f"Retrying {agent_name}...")
            return "retry"
        elif choice == "2":
            print_warning(session, f"Skipping {agent_name}...")
            return "skip"
        elif choice == "3":
            print_error(session, "Aborting workflow.")
            return "abort"
