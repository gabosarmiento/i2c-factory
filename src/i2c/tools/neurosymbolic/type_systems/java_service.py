# src/i2c/tools/neurosymbolic/type_systems/java_service.py
import subprocess
import tempfile
import re
from pathlib import Path

class JavaTypeSystem:
    """Java type validation using javac compiler"""
    
    JAVA_VERSION = "17"
    
    def validate_content(self, content: str) -> dict:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_file = tmp_path / "Main.java"
            src_file.write_text(content)
            
            try:
                result = subprocess.run(
                    ["javac", "-source", self.JAVA_VERSION, "-Xlint:all", str(src_file)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                return {"valid": True, "warnings": self._parse_warnings(result.stderr)}
            except subprocess.CalledProcessError as e:
                return {"valid": False, "errors": self._parse_errors(e.stderr)}

    def _parse_errors(self, output: str) -> list:
        return [f"JAVA: {m[0]}" for m in re.findall(r"error: (.+?)\n", output)]

    def _parse_warnings(self, output: str) -> list:
        return [f"JAVA-WARN: {m[0]}" for m in re.findall(r"warning: (.+?)\n", output)]