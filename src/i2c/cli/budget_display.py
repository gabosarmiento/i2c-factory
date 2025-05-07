# i2c/cli/budget_display.py
"""
Simplified budget display component for the CLI interface.
Provides visual feedback on budget usage without frequent interruptions.
"""

from i2c.agents.budget_manager import BudgetManagerAgent
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import BarColumn, Progress, TextColumn

console = Console()

def show_budget_status(budget_manager: BudgetManagerAgent, show_warning: bool = True):
    """
    Display a compact budget status line.
    Shows warning only when approaching budget limit.
    """
    tokens, cost = budget_manager.get_session_consumption()
    budget_limit = budget_manager.session_budget
    
    if budget_limit:
        percentage = min(100, (cost / budget_limit) * 100)
        remaining = budget_limit - cost
        
        # Only show warning if we're above 80% of budget and warning flag is set
        if percentage > 80 and show_warning:
            console.print(f"[bold yellow]⚠️ Budget Alert: ${cost:.4f} / ${budget_limit:.2f} ([red]{percentage:.1f}%[/red] used)[/bold yellow]")
            console.print(f"[yellow]Remaining: ${remaining:.4f}[/yellow]")
            return True  # Return True to indicate warning was shown
        else:
            # Simple status without interrupting flow
            console.print(f"[cyan]Budget:[/cyan] ${cost:.4f} / ${budget_limit:.2f} ([green]{percentage:.1f}%[/green] used)")
    else:
        console.print(f"[cyan]Budget:[/cyan] ${cost:.4f} / Unlimited")
    
    return False  # No warning shown

def show_operation_cost(operation: str, tokens: int, cost: float):
    """Display a simple operation cost notification."""
    console.print(f"[cyan]Operation:[/cyan] {operation} | [cyan]Tokens:[/cyan] {tokens:,} | [cyan]Cost:[/cyan] ${cost:.6f}")

def show_budget_summary(budget_manager: BudgetManagerAgent):
    """Display a rich summary of budget usage."""
    
    # Get data from budget manager
    tokens, cost = budget_manager.get_session_consumption()
    budget_limit = budget_manager.session_budget
    
    if budget_limit:
        percentage_used = min(100, (cost / budget_limit) * 100)
        remaining = budget_limit - cost
    else:
        percentage_used = 0
        remaining = float('inf')
    
    # Directly create and render a Panel with text content
    panel_content = []
    
    # Add main stats as text
    panel_content.append(f"[cyan]Total Tokens Used:[/cyan] [green]{tokens:,}[/green]")
    panel_content.append(f"[cyan]Total Cost:[/cyan] [green]${cost:.6f}[/green]")
    
    if budget_limit:
        panel_content.append(f"[cyan]Budget Limit:[/cyan] [green]${budget_limit:.2f}[/green]")
        panel_content.append(f"[cyan]Remaining:[/cyan] [green]${remaining:.4f}[/green]")
        panel_content.append(f"[cyan]Percentage Used:[/cyan] [green]{percentage_used:.1f}%[/green]")
    else:
        panel_content.append(f"[cyan]Budget Limit:[/cyan] [green]Unlimited[/green]")
    
    # Add progress bar
    if budget_limit:
        progress_text = f"[{'■' * int(percentage_used/5)}{'□' * (20-int(percentage_used/5))}] {percentage_used:.1f}%"
        panel_content.append(f"\n[bold]Budget Usage:[/bold]\n{progress_text}")
    
    # Provider stats
    providers = budget_manager.get_provider_stats()
    
    if any(stats['calls'] > 0 for _, stats in providers.items()):
        panel_content.append("\n[bold]Provider Breakdown:[/bold]")
        for provider, stats in providers.items():
            if stats['calls'] > 0:
                panel_content.append(f"  [cyan]{provider}:[/cyan] {stats['calls']} calls, {stats['tokens']:,} tokens, ${stats['cost']:.6f}")
    
    # Add Agno metrics if available
    agno_metrics = getattr(budget_manager, 'agno_metrics', None)
    
    if agno_metrics:
        panel_content.append("\n[bold]Agno Metrics Detail:[/bold]")
        
        input_tokens = getattr(agno_metrics, 'input_tokens', 0)
        output_tokens = getattr(agno_metrics, 'output_tokens', 0)
        
        panel_content.append(f"  [cyan]Input Tokens:[/cyan] {input_tokens:,}")
        panel_content.append(f"  [cyan]Output Tokens:[/cyan] {output_tokens:,}")
        
        prompt_tokens = getattr(agno_metrics, 'prompt_tokens', 0)
        completion_tokens = getattr(agno_metrics, 'completion_tokens', 0)
        
        if prompt_tokens > 0 or completion_tokens > 0:
            panel_content.append(f"  [cyan]Prompt Tokens:[/cyan] {prompt_tokens:,}")
            panel_content.append(f"  [cyan]Completion Tokens:[/cyan] {completion_tokens:,}")
        
        reasoning_tokens = getattr(agno_metrics, 'reasoning_tokens', 0)
        if reasoning_tokens > 0:
            panel_content.append(f"  [cyan]Reasoning Tokens:[/cyan] {reasoning_tokens:,}")
        
        response_time = getattr(agno_metrics, 'time', None)
        if response_time is not None:
            panel_content.append(f"  [cyan]Response Time:[/cyan] {response_time:.2f}s")
    
    # Create and display the panel
    panel = Panel(
        "\n".join(panel_content),
        title="💰 Budget Summary",
        border_style="blue",
        expand=False,
        padding=(1, 2)
    )
    
    console.print(panel)