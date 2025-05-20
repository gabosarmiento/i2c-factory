
import subprocess, sys, shutil
from pathlib import Path
from typing import Tuple, List, Optional

# ------------------------------------------------------------------ #
#  Image definitions – edit in one place if you need new versions    #
# ------------------------------------------------------------------ #
IMAGE_MAP = {
    "node": ("node:20-alpine", ["npx", "jest", "--runInBand"]),
    "go":   ("golang:1.22-alpine", ["go", "test", "./..."]),
    "java": ("maven:3.9-eclipse-temurin-21", ["mvn", "-q", "test"]),
}

# ------------------------------------------------------------------ #
#  Helpers                                                           #
# ------------------------------------------------------------------ #
def _ensure_image_cached(image: str):
    """Pull quietly only if it's not on the host yet."""
    if shutil.which("docker") is None:
        return
    if subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True
    ).returncode != 0:
        subprocess.run(["docker", "pull", "--quiet", image], check=True)


def _docker_run(image: str, cmd: list[str], workdir: Path) -> Tuple[bool, str]:
    """Run <cmd> in a disposable container mounting <workdir>."""
    if shutil.which("docker") is None:
        return False, "Docker not found – skipping non‑Python tests."

    _ensure_image_cached(image)

    proc = subprocess.run(
        ["docker", "run", "--rm",
         "-v", f"{workdir.absolute()}:/app",
         "-w", "/app", image] + cmd,
        capture_output=True, text=True
    )
    return proc.returncode == 0, proc.stdout + proc.stderr


# ------------------------------------------------------------------ #
#  Validation Result dataclass (simple)                              #
# ------------------------------------------------------------------ #
class ValidationResult:
    def __init__(self, success: bool, failure_type: str = "", message: str = "", suggestions: Optional[List[str]] = None):
        self.success = success
        self.failure_type = failure_type
        self.message = message
        self.suggestions = suggestions or []

    def to_dict(self):
        return {
            "success": self.success,
            "failure_type": self.failure_type,
            "message": self.message,
            "suggestions": self.suggestions
        }


# ------------------------------------------------------------------ #
#  Reflective Validator                                              #
# ------------------------------------------------------------------ #
class ReflectiveValidator:
    def __init__(self, project_path: str | Path):
        self.project_path = Path(project_path)

    # ------------- main polyglot runner ------------- #
    def run_unit_tests(self) -> Tuple[bool, str]:
        """Run Python tests locally and other languages via Docker."""
        combined_log: List[str] = []
        overall_ok = True

        # ---- Python ----
        if any(p.suffix == ".py" and p.name.startswith("test_") for p in self.project_path.rglob("tests/**/*")):
            proc = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "*test*.py"],
                capture_output=True, text=True, cwd=self.project_path
            )
            combined_log.append(proc.stdout + proc.stderr)
            overall_ok &= proc.returncode == 0

        # ---- TypeScript / JavaScript (Jest) ----
        if any(p.suffix in {".ts", ".js"} and p.name.endswith((".test.ts", ".test.js")) for p in self.project_path.rglob("tests/**/*")):
            ok, out = _docker_run(*IMAGE_MAP["node"], workdir=self.project_path)
            combined_log.append(out)
            overall_ok &= ok

        # ---- Go ----
        if any(p.suffix == ".go" and p.name.endswith("_test.go") for p in self.project_path.rglob("tests/**/*")):
            ok, out = _docker_run(*IMAGE_MAP["go"], workdir=self.project_path)
            combined_log.append(out)
            overall_ok &= ok

        # ---- Java ----
        if any(p.suffix == ".java" and p.name.endswith("Test.java") for p in self.project_path.rglob("tests/**/*")):
            ok, out = _docker_run(*IMAGE_MAP["java"], workdir=self.project_path)
            combined_log.append(out)
            overall_ok &= ok

        return overall_ok, "\n".join(combined_log)

    # ------------- classify + wrap ------------- #
    def classify_failure(self, output: str) -> ValidationResult:
        if "SyntaxError" in output or "IndentationError" in output:
            return ValidationResult(False, "syntax_error", output, ["Fix indentation or syntax issues."])
        if "ModuleNotFoundError" in output:
            return ValidationResult(False, "import_error", output, ["Check missing or wrong imports."])
        if "AttributeError" in output:
            return ValidationResult(False, "attribute_error", output, ["Check function or class names."])
        if "FAILED (failures=" in output or "FAILED (errors=" in output:
            return ValidationResult(False, "test_failure", output, ["Review the failed test cases and outputs."])
        return ValidationResult(False, "unknown_error", output, ["Review the output log manually."])

    def validate_project(self) -> ValidationResult:
        ok, out = self.run_unit_tests()
        if ok:
            return ValidationResult(True, message="All tests passed.")
        return self.classify_failure(out)
