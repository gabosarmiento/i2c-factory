import os
import json
from pathlib import Path 
import pytest

from groq import Groq

def read_all_code(directory):
    """Concatenate all Python code in a directory tree into one string."""
    directory = Path(directory)
    code_files = sorted(directory.rglob("*.py"))
    if not code_files:
        raise FileNotFoundError(f"No .py files found in {directory}")
    code = []
    for f in code_files:
        code.append(f"# === {f.name} ===\n")
        code.append(f.read_text(encoding="utf-8"))
    return "\n".join(code)

class GroqLLM:
    def __init__(self, model=None):
        self.model = model or "llama3-70b-8192"
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise RuntimeError("Set GROQ_API_KEY in your environment.")
        self.client = Groq(api_key=self.api_key)
    def ask(self, prompt):
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a senior AGNO code reviewer. Analyze the codebase for AGNO usage."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=512
        )
        return completion.choices[0].message.content.strip()

llm = GroqLLM()

# --- Test itself ---
def test_llm_verifies_agno_usage(tmp_path):
    # Simulate a scenario.json (optional, for local test coverage)
    scenario_path = tmp_path / "scenario.json"
    scenario_json = {
        "name": "AGNO Knowledge Application Test",
        "description": "Ensure initial generation uses PDF ...",
        "steps": [
            {
                "type": "knowledge",
                "name": "Ingest AGNO Cheat Sheet",
                "doc_path": "src/i2c/docs/agno_cheat_sheet.pdf",
                "doc_type": "AGNO Cheat Sheet",
                "framework": "AGNO",
                "version": "1.0",
                "project_name": "agno_cli_reflector",
                "global": True
            },
            {
                "type": "initial_generation",
                "name": "Generate CLI Reflection Tool",
                "prompt": (
                    "Based on the AGNO cheat sheet, build a CLI tool to test reflection. "
                    "Use PDFUrlKnowledgeBase and vector DB to load documents."
                ),
                "project_name": "agno_cli_reflector",
                "input": {
                    "instruction": "IGNORED"
                },
                "output_type": "code",
                "agent": "CodeBuilderAgent"
            }
        ]
    }
    scenario_path.write_text(json.dumps(scenario_json), encoding="utf-8")

    # Load scenario and extract project_name robustly
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    project_name = scenario.get("project_name")
    if not project_name:
        for step in scenario.get("steps", []):
            if "project_name" in step:
                project_name = step["project_name"]
                break
    assert project_name, "❌ Could not find project_name in scenario or steps"

    # Compose the output directory (assumes your pipeline has written here)
    output_dir = Path("output") / project_name
    assert output_dir.exists(), f"❌ Output dir not found: {output_dir}"

    # Read all code
    codebase = read_all_code(output_dir)

    # LLM analysis
    prompt = f"""
You are a senior AGNO developer. Analyze the following codebase and answer:

1. Does it use the AGNO framework?
2. Which AGNO components or patterns are implemented?
3. Does it reflect an agentic, modular, and reflective architecture?

Respond with JSON:
{{
    "uses_agno": true|false,
    "components": [...],
    "justification": "..."
}}

--- CODE START ---
{codebase}
--- CODE END ---
"""
    from i2c.utils.json_extraction import extract_json

    response = llm.ask(prompt)
    try:
        result = extract_json(response)
    except Exception:
        print("Raw LLM response (not valid JSON):", response)
        raise

    assert result["uses_agno"], f"❌ LLM judged AGNO not applied. Justification: {result['justification']}"

if __name__ == "__main__":
    test_llm_verifies_agno_usage(Path("output"))
    print("✅ LLM AGNO usage test passed")
