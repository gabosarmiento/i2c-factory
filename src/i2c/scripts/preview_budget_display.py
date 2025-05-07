# src/i2c/scripts/preview_budget_display.py
"""Preview script for the simplified budget display UI"""

import os
from pathlib import Path
import time
from i2c.bootstrap import initialize_environment, PROJECT_ROOT

# Initialize environment
initialize_environment()

# Import directly from i2c.cli.budget_display (not from itself)
from i2c.cli.budget_display import (
    show_budget_status,
    show_budget_summary,
    show_operation_cost
)
from i2c.agents.budget_manager import BudgetManagerAgent
from rich.console import Console
from types import SimpleNamespace

console = Console()

def main():
    """Main preview function"""
    console.print("[bold cyan]Simplified Budget Display Preview[/bold cyan]", justify="center")
    console.print("=" * 70, justify="center")
    console.print("\nThis preview demonstrates the simplified budget display components.\n")
    
    # Create a budget manager with test data
    budget_manager = BudgetManagerAgent(session_budget=5.0)  # $5.00 budget
    
    # 1. Show budget status (low usage - no warning)
    console.print("\n[bold]1. Budget Status (Low Usage)[/bold]")
    budget_manager.track_usage(
        prompt="Test prompt 1",
        response="Test response 1",
        model_id="groq/llama-3.1-8b-instant",
        actual_tokens=150,
        actual_cost=0.01
    )
    show_budget_status(budget_manager)
    
    time.sleep(1)
    
    # 2. Show operation cost
    console.print("\n[bold]2. Operation Cost Display[/bold] (shown after operations)")
    show_operation_cost(
        operation="Small Operation",
        tokens=150,
        cost=0.01
    )
    
    time.sleep(1)
    
    # 3. Update budget to near limit and show warning
    console.print("\n[bold]3. Budget Status (Near Limit - Warning)[/bold]")
    budget_manager.track_usage(
        prompt="Large operation",
        response="Large operation response",
        model_id="groq/llama-3.1-70b-versatile",
        actual_tokens=70000,
        actual_cost=4.2  # 84% of $5 budget
    )
    show_budget_status(budget_manager)
    
    time.sleep(1)
    
    # 4. Add mock Agno metrics for richer summary
    budget_manager.agno_metrics = SimpleNamespace(
        input_tokens=30000,
        output_tokens=40150,
        total_tokens=70150,
        prompt_tokens=30000,
        completion_tokens=40150,
        time=5.3,
        time_to_first_token=0.8,
        reasoning_tokens=5000
    )
    
    # Update provider stats for a richer display
    budget_manager.provider_stats['groq']['tokens'] = 70150
    budget_manager.provider_stats['groq']['cost'] = 4.21
    budget_manager.provider_stats['groq']['calls'] = 2
    
    # 5. Show session-end budget summary
    console.print("\n[bold]4. Full Budget Summary[/bold] (shown at end of session)")
    show_budget_summary(budget_manager)
    
    console.print("\n[bold cyan]Preview Complete[/bold cyan]", justify="center")
    console.print("[green]The simplified budget display provides visibility without frequent interruptions.[/green]", justify="center")
    console.print("=" * 70, justify="center")

if __name__ == "__main__":
    main()