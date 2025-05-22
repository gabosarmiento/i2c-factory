# /from i2c/cli/controller.py
# Canvas Controller: Alive Factory CLI Visual Manager

class Canvas:
    def __init__(self):
        self.prefix_info = "[INFO]:"
        self.prefix_step = "[STEP]:"
        self.prefix_success = "[SUCCESS]:"
        self.prefix_error = "[ERROR]:"
        self.prefix_warning = "[WARNING]:"

    def start_process(self, title: str):
        print(f"\n🚀 {title} Start\n")

    def end_process(self, message: str):
        print(f"\n🏁 {message}\n")

    def step(self, message: str):
        print(f"{self.prefix_step} {message}")

    def info(self, message: str):
        print(f"{self.prefix_info} {message}")

    def success(self, message: str):
        print(f"{self.prefix_success} {message}")

    def error(self, message: str):
        print(f"{self.prefix_error} {message}")

    def warning(self, message: str):
        print(f"{self.prefix_warning} {message}")

    def get_user_input(self, prompt: str) -> str:
        return input(f"🎯 {prompt} ")

# Instantiate globally for imports
canvas = Canvas()

