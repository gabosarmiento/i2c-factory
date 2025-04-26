# /cli/session.py
# Controls the global CLI session state: mood, error tracking, theme switching.

from rich.console import Console
from cli.theme import get_theme

class CLISession:
    def __init__(self):
        """
        Initializes a CLI session with calm mood and base theme.
        """
        self.console = Console(theme=get_theme("calm"))
        self.error_count = 0
        self.mood = "calm"  # calm, alert, critical
        self.max_errors_before_alert = 2
        self.max_errors_before_critical = 5

    def log_error(self):
        """
        Increments error count and adjusts mood accordingly.
        """
        self.error_count += 1
        self._check_mood()

    def log_success(self):
        """
        Decreases error count slightly and adjusts mood accordingly.
        """
        if self.error_count > 0:
            self.error_count -= 1
        self._check_mood()

    def _check_mood(self):
        """
        Adjusts console theme based on current error count.
        """
        if self.error_count >= self.max_errors_before_critical:
            if self.mood != "critical":
                self.mood = "critical"
                self.console = Console(theme=get_theme("critical"))
        elif self.error_count >= self.max_errors_before_alert:
            if self.mood != "alert":
                self.mood = "alert"
                self.console = Console(theme=get_theme("alert"))
        else:
            if self.mood != "calm":
                self.mood = "calm"
                self.console = Console(theme=get_theme("calm"))

    def reset_errors(self):
        """
        Resets error count and mood to calm.
        """
        self.error_count = 0
        self.mood = "calm"
        self.console = Console(theme=get_theme("calm"))

    def get_mood(self) -> str:
        """
        Returns the current mood ("calm", "alert", or "critical").
        """
        return self.mood
