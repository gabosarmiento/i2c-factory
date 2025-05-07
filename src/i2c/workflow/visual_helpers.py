# i2c/workflow/visual_helpers.py
from pathlib import Path
from i2c.cli.controller import canvas

def show_progress(title: str, steps: list, current_step: int = 0):
    """Displays a visual progress indicator."""
    if len(steps) == 0:
        return
        
    # Calculate progress percentage
    progress = int((current_step / len(steps)) * 20)  # 20 blocks for progress bar
    
    # Create progress bar
    bar = "█" * progress + "░" * (20 - progress)
    percentage = int((current_step / len(steps)) * 100)
    
    canvas.info(f"\nProgress: [{bar}] {percentage}%")
    
    # Display step status
    for i, step in enumerate(steps):
        if i < current_step:
            status = "✅"  # Complete
        elif i == current_step:
            status = "🔄"  # In progress
        else:
            status = "⬜"  # Not started
            
        canvas.info(f"{status} {step}")

def show_file_list(title: str, files: list, project_path: Path):
    """Displays a list of files with visual formatting."""
    if not files:
        return
        
    canvas.info(f"\n📁 {title}:")
    for file in files:
        # Convert to relative path if needed
        if isinstance(file, Path):
            file_path = str(file.relative_to(project_path))
        else:
            file_path = file
            
        # Determine icon based on file extension
        ext = Path(file_path).suffix.lower()
        if ext == '.py':
            icon = "🐍"  # Python
        elif ext in ['.js', '.jsx']:
            icon = "📜"  # JavaScript
        elif ext in ['.html', '.htm']:
            icon = "🌐"  # HTML
        elif ext in ['.css', '.scss']:
            icon = "🎨"  # CSS
        elif ext in ['.md', '.txt']:
            icon = "📄"  # Text
        elif ext in ['.json', '.yaml', '.yml']:
            icon = "⚙️"  # Config
        else:
            icon = "📄"  # Default
            
        canvas.info(f"  {icon} {file_path}")

def show_help_message(current_project_path: Path | None):
    """Displays help message with available commands."""
    canvas.info("\n📋 Available Commands:")
    canvas.info("----------------------------------")
    
    if not current_project_path:
        canvas.info("<idea>           - Start a new project from an idea")
        canvas.info("p <path>         - Switch to project at specified path")
        canvas.info("?, help          - Display this help message")
        canvas.info("q                - Quit")
    else:
        canvas.info("f <idea>         - Add a new feature to current project")
        canvas.info("r                - Refine the current project")
        canvas.info("s <story>        - Add a structured user story")
        canvas.info("k                - Knowledge base management")
        canvas.info("plan             - Show current project plan")
        canvas.info("p <path>         - Switch to project at specified path")
        canvas.info("?, help          - Display this help message")
        canvas.info("q                - Quit")

def show_project_plan(project_path: Path):
    """Displays current project plan and progress."""
    try:
        # This is a placeholder - in a real implementation, 
        # we'd get this from project state tracking
        project_name = project_path.name
        
        canvas.info(f"\n📊 Project Plan: {project_name}")
        canvas.info("----------------------------------")
        
        # Count files by type for a simple visualization
        file_counts = {'py': 0, 'js': 0, 'jsx': 0, 'html': 0, 'css': 0, 'other': 0}
        total_files = 0
        
        # Count files in project
        for file_path in project_path.rglob('*'):
            if file_path.is_file():
                ext = file_path.suffix[1:] if file_path.suffix else 'other'
                if ext in file_counts:
                    file_counts[ext] += 1
                else:
                    file_counts['other'] += 1
                total_files += 1
        
        canvas.info(f"Total files: {total_files}")
        
        # Display file counts by type
        for ext, count in file_counts.items():
            if count > 0:
                canvas.info(f"- {ext.upper()} files: {count}")
        
        # Show recently modified files (if any)
        try:
            import os
            recent_files = []
            for file_path in project_path.rglob('*'):
                if file_path.is_file():
                    mtime = os.path.getmtime(file_path)
                    recent_files.append((file_path, mtime))
            
            # Sort by modification time (most recent first)
            recent_files.sort(key=lambda x: x[1], reverse=True)
            
            if recent_files:
                canvas.info("\nRecently modified files:")
                for file_path, _ in recent_files[:5]:  # Show top 5 most recent
                    canvas.info(f"- {file_path.relative_to(project_path)}")
        except Exception:
            pass  # Skip this part if it fails
        
    except Exception as e:
        canvas.error(f"Error showing project plan: {e}")