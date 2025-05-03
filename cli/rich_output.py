# cli/rich_output.py
"""Enhanced CLI output with rich formatting and visual feedback"""

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.syntax import Syntax
from rich.tree import Tree
from rich.markdown import Markdown
from typing import List, Dict, Optional
import time


class RichOutput:
    """Enhanced CLI output with rich formatting"""
    
    def __init__(self):
        self.console = Console()
        self.current_process = None
    
    def start_feature_pipeline(self, story_id: str, title: str):
        """Start feature pipeline display"""
        self.console.print(Panel(
            f"[bold blue]Feature Pipeline[/bold blue]\n\n"
            f"Story ID: [yellow]{story_id}[/yellow]\n"
            f"Title: {title}",
            title="🚀 Starting Feature Implementation",
            border_style="blue"
        ))
    
    def show_story_details(self, story_dict: Dict):
        """Display story details in a formatted panel"""
        panel_content = f"""
[bold]Story ID:[/bold] {story_dict['story_id']}
[bold]Title:[/bold] {story_dict['title']}
[bold]Status:[/bold] {story_dict['status']}
[bold]Priority:[/bold] {story_dict['priority']}

[bold]User Story:[/bold]
As a {story_dict['as_a']},
I want {story_dict['i_want']},
So that {story_dict['so_that']}.

[bold]Acceptance Criteria:[/bold]
"""
        for i, ac in enumerate(story_dict['acceptance_criteria'], 1):
            status = "✅" if ac['is_met'] else "⬜"
            panel_content += f"{status} {i}. {ac['description']}\n"
        
        self.console.print(Panel(panel_content, title="📋 User Story Details", border_style="cyan"))
    
    def show_context_gathering(self, context: Dict):
        """Display context gathering results"""
        table = Table(title="📚 Gathered Context")
        table.add_column("Type", style="cyan", no_wrap=True)
        table.add_column("Count", justify="right", style="green")
        table.add_column("Status", justify="center")
        
        table.add_row(
            "Story Context",
            str(len(context.get("story_context", []))),
            "✅" if context.get("story_context") else "❌"
        )
        table.add_row(
            "Documentation",
            str(len(context.get("documentation", []))),
            "✅" if context.get("documentation") else "❌"
        )
        table.add_row(
            "Code Context",
            "Present" if context.get("code_context") else "Empty",
            "✅" if context.get("code_context") else "⚠️"
        )
        table.add_row(
            "Knowledge Context",
            "Present" if context.get("knowledge_context") else "Empty",
            "✅" if context.get("knowledge_context") else "⚠️"
        )
        
        self.console.print(table)
    
    def show_plan(self, plan: List[Dict], title: str = "Implementation Plan"):
        """Display implementation plan as a tree"""
        tree = Tree(f"[bold]{title}[/bold]")
        
        for i, step in enumerate(plan, 1):
            file_node = tree.add(f"[yellow]{step['file']}[/yellow]")
            file_node.add(f"[blue]Action:[/blue] {step['action']}")
            file_node.add(f"[green]What:[/green] {step['what']}")
            file_node.add(f"[magenta]How:[/magenta] {step['how']}")
        
        self.console.print(Panel(tree, title=f"🗺️ {title}", border_style="green"))
    
    def show_best_practices(self, practices: List[Dict]):
        """Display best practices"""
        if not practices:
            self.console.print("[yellow]No best practices generated[/yellow]")
            return
        
        table = Table(title="💡 Best Practices")
        table.add_column("Practice", style="cyan")
        table.add_column("Rationale", style="green")
        
        for practice in practices:
            table.add_row(
                practice.get("practice", ""),
                practice.get("rationale", "")
            )
        
        self.console.print(table)
    
    def show_code_implementation(self, code_map: Dict[str, str]):
        """Display implemented code files"""
        for file_path, content in code_map.items():
            self.console.print(Panel(
                Syntax(content, "python", theme="monokai", line_numbers=True),
                title=f"📄 {file_path}",
                border_style="blue"
            ))
    
    def show_issue_resolution(self, resolution: Dict):
        """Display issue resolution results"""
        if not resolution:
            return
        
        resolved = resolution.get("resolved_issues", [])
        unresolved = resolution.get("unresolved_issues", [])
        
        # Resolved issues
        if resolved:
            table = Table(title="✅ Resolved Issues")
            table.add_column("Issue", style="red")
            table.add_column("Resolution", style="green")
        
        for item in resolved:
            issue = item["issue"]
            resolution_details = item["resolution"]
            table.add_row(
                f"{issue['type']}: {issue['file']}",
                f"Fixed with {resolution_details.get('iterations', 0)} iterations"
            )
           
        self.console.print(table)

       
        # Unresolved issues
        if unresolved:
            table = Table(title="❌ Unresolved Issues")
            table.add_column("Issue", style="red")
            table.add_column("Type", style="yellow")
            
            for issue in unresolved:
                table.add_row(
                    f"{issue['file']}",
                    issue['type']
                )
            
            self.console.print(table)
   
    def show_pipeline_summary(self, results: Dict[str, Dict]):
        """Display pipeline execution summary"""
        table = Table(title="📊 Pipeline Execution Summary")
        table.add_column("Story ID", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Issues", justify="right")
        table.add_column("Resolution", justify="center")
        
        for story_id, result in results.items():
            status = "✅" if result["success"] else "❌"
            issues_count = len(result.get("result", {}).get("implementation", {}).get("issues", []))
            
            # Safely pull out the resolution dict (or use an empty one)
            resolution = result.get("result", {}).get("resolution") or {}
            # Now resolution.get("success") won't blow up
            if resolution.get("success", False):
                resolution_status = "✅"
            elif issues_count > 0:
                resolution_status = "❌"
            else:
                resolution_status = "-"
            
            table.add_row(
                story_id,
                status,
                str(issues_count),
                resolution_status
            )
        
        self.console.print(table)
    
    def progress_bar(self, description: str, total: int = 100):
        """Create a progress bar context manager"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        )
    
    def print_success(self, message: str):
        """Print success message"""
        self.console.print(f"[bold green]✅ {message}[/bold green]")
    
    def print_error(self, message: str):
        """Print error message"""
        self.console.print(f"[bold red]❌ {message}[/bold red]")
    
    def print_warning(self, message: str):
        """Print warning message"""
        self.console.print(f"[bold yellow]⚠️ {message}[/bold yellow]")
    
    def print_info(self, message: str):
        """Print info message"""
        self.console.print(f"[blue]ℹ️ {message}[/blue]")


# Singleton instance
rich_output = RichOutput()    