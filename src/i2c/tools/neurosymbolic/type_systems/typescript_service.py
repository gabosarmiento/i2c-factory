# src/i2c/tools/neurosymbolic/type_systems/typescript_service.py

import subprocess
from pathlib import Path
import json

class TypeScriptValidator:
    """Leverages official TypeScript compiler for precise validation"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.ts_config = project_root / "tsconfig.json"
        
    def validate_file(self, file_path: Path, content: str) -> dict:
        """Validate TypeScript code using tsc compiler"""
        # Write the code to a temporary file
        temp_file = self.project_root / "temp_validation.ts"
        temp_file.write_text(content, encoding='utf-8')
        
        try:
            # Run tsc with JSON output, strict mode, noEmit
            result = subprocess.run(
                ["tsc", "--pretty", "false", "--strict", "--noEmit", "--json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return self._parse_tsc_output(result.stdout)
        except subprocess.CalledProcessError as e:
            # Even on errors, tsc writes JSON to stdout
            return self._parse_tsc_output(e.stdout)
        finally:
            # Clean up the temp file
            temp_file.unlink()

    def _parse_tsc_output(self, output: str) -> dict:
        try:
            # tsc --json emits an array of diagnostic objects
            diags = json.loads(output)
            return {
                "valid": len(diags) == 0,
                "errors": [self._format_ts_error(d) for d in diags]
            }
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {"valid": False, "errors": ["TypeScript validation failed"]}

    def _format_ts_error(self, diagnostic: dict) -> str:
        # Format: TS<code>: <message> at file:start
        return (
            f"TS{diagnostic['code']}: {diagnostic['message']}\n"
            f"  at {diagnostic['file']}:{diagnostic['start']}"
        )
