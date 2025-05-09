# src/i2c/tools/neurosymbolic/type_systems/go_service.py
import subprocess
import tempfile
import re
from pathlib import Path

class GoTypeSystem:
    """Go type validation using go vet and staticcheck"""
    
    def validate_content(self, content: str) -> dict:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "go.mod").write_text("module validation\n")
            main_file = tmp_path / "main.go"
            main_file.write_text(content)
            
            vet_result = subprocess.run(
                ["go", "vet", str(main_file)],
                capture_output=True,
                text=True
            )
            
            staticcheck_result = subprocess.run(
                ["staticcheck", str(main_file)],
                capture_output=True,
                text=True
            )
            
            return self._combine_results(vet_result, staticcheck_result)

    def _combine_results(self, vet_result, staticcheck_result):
        errors = []
        errors += re.findall(r"(.*?):(\d+):(\d+): (.*)", vet_result.stderr)
        errors += staticcheck_result.stdout.splitlines()
        return {
            "valid": len(errors) == 0,
            "errors": [f"GO: {e}" for e in errors]
        }