# src/i2c/tools/neurosymbolic/type_systems/javascript_service.py
import subprocess
import tempfile
import json
from pathlib import Path

class JavaScriptValidator:
    """ESLint-powered JavaScript validation with type-aware rules"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config = {
            "parserOptions": {"ecmaVersion": "latest"},
            "rules": {
                "no-undef": "error",
                "valid-typeof": "error",
                "no-mixed-operators": "error"
            }
        }
        
    def validate_content(self, content: str) -> dict:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / ".eslintrc.json").write_text(json.dumps(self.config))
            input_file = tmp_path / "input.js"
            input_file.write_text(content)
            
            result = subprocess.run(
                ["eslint", "-f", "json", str(input_file)],
                capture_output=True,
                text=True
            )
            
            return self._parse_output(result.stdout)

    def _parse_output(self, output: str) -> dict:
        try:
            issues = json.loads(output)[0]['messages']
            return {
                "valid": len(issues) == 0,
                "errors": [f"JS{msg['ruleId']}: {msg['message']} (line {msg['line']})" 
                          for msg in issues]
            }
        except Exception:
            return {"valid": False, "errors": ["JavaScript validation failed"]}