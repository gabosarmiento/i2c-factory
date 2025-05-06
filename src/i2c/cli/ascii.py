# /from i2c/cli/ascii.py
# Handles dynamic ASCII Art banners and diagrams for the Alive CLI.

from rich.console import Console
from rich.panel import Panel

console = Console()

# Example simple banner for startup
def show_banner():
    ascii_art = """                                         .-.----------.                                                                
                                    .-.                  --.                                                           
                               . .-.       ..........       --                                                         
                                ..   .  .......-.......  ..   ..                                                       
                               .   .--.........-.....-....--   ..                                                      
                               .    ........-------.......      .                                                      
                               .     .......--I2C--.......      .                                                      
                               .       ..................      .                                                       
                                ..       ..............       .                                                        
                                  --        . .....   .     -.                                                         
                                    .--.                .-.                                                            
                                          ...------...                                                                 
                  .  .  .  . ......... .. Idea 2 Code  .. .......... .  .  .  .                                        
    """
    console.print(Panel(ascii_art, style="bold cyan", title="[bright_blue]Idea-to-Code Factory[/]", border_style="bright_blue"))

# Example dynamic diagram for planning

def show_plan_diagram():
    diagram = """
    Idea
     │
     ▼
  Clarified Goal
     │
     ▼
 Planned Files
     │
     ▼
Generated Code
     │
     ▼
   Project Ready 🚀
    """
    console.print(Panel(diagram, style="bright_cyan", title="[cyan]Project Flow[/]", border_style="cyan"))
