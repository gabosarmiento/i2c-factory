# Minimal structured logger for CLI applications.

class Logger:
    @staticmethod
    def info(message: str):
        print(f"ℹ️  INFO | {message}")

    @staticmethod
    def success(message: str):
        print(f"✅ SUCCESS | {message}")

    @staticmethod
    def warning(message: str):
        print(f"⚠️  WARNING | {message}")

    @staticmethod
    def error(message: str):
        print(f"❌ ERROR | {message}")

    @staticmethod
    def step(message: str):
        print(f"🛠 STEP | {message}")

    @staticmethod
    def done(message: str):
        print(f"🎯 DONE | {message}")

