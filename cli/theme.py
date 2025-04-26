# /cli/theme.py
# Defines color themes for different CLI moods (calm, alert, critical).

from rich.theme import Theme

def get_theme(mode: str) -> Theme:
    """
    Returns a Rich Theme object based on the CLI mood.
    """
    if mode == "critical":
        return Theme({
            "info": "bold red",
            "success": "bright_red",
            "warning": "bold red",
            "error": "bold red",
            "step": "yellow",
            "agent": "bright_red",
            "code": "grey50",
        })
    elif mode == "alert":
        return Theme({
            "info": "yellow",
            "success": "bright_yellow",
            "warning": "yellow",
            "error": "bright_red",
            "step": "magenta",
            "agent": "bright_magenta",
            "code": "grey66",
        })
    else:  # calm mode
        return Theme({
            "info": "bright_blue",
            "success": "bright_green",
            "warning": "yellow",
            "error": "red",
            "step": "cyan",
            "agent": "bright_cyan",
            "code": "grey82",
        })
