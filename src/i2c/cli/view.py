# /from i2c/cli/view.py
# Provides all structured visual outputs for the Alive CLI: logs, spinners, code panels, ASCII art.

from rich.panel import Panel
from rich.syntax import Syntax
from rich.spinner import Spinner
from rich.live import Live
from time import sleep

from i2c.cli.ascii import show_plan_diagram

# --- Basic Text Outputs ---

def print_info(session, message: str):
    session.console.print(f"[info][INFO][/]: {message}")

def print_success(session, message: str):
    session.console.print(f"[success][SUCCESS][/]: {message}")

def print_warning(session, message: str):
    session.console.print(f"[warning][WARNING][/]: {message}")

def print_error(session, message: str):
    session.console.print(f"[error][ERROR][/]: {message}")

def print_step(session, message: str):
    session.console.print(f"[step][STEP][/]: {message}")

# --- Code Block Output ---

def show_code_block(session, code: str, filename: str = "generated.py"):
    syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
    panel = Panel(syntax, title=filename, border_style="bright_blue")
    session.console.print(panel)

# --- Nanobot Spinner ---

def show_spinner(session, message: str, duration: float = 1.5):
    spinner = Spinner("earth", text=f"[agent]{message}")
    with Live(spinner, refresh_per_second=10, console=session.console):
        sleep(duration)

# --- ASCII Diagram ---

def show_project_diagram(session):
    show_plan_diagram()
