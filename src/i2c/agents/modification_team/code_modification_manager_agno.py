import json
from pathlib import Path
from typing import Any, Dict

from agno.agent import Agent
from agno.team import Team

from i2c.llm_providers import llm_middle, llm_highest

# Use your own dataclasses if import fails
try:
    from i2c.agents.modification_team.patch import ModificationRequest, AnalysisResult, ModificationPlan
except Exception:
    from dataclasses import dataclass

    @dataclass
    class ModificationRequest:
        project_root: str
        user_prompt: str
        rag_context: str | None = None

    @dataclass
    class AnalysisResult:
        details: str = ""

    @dataclass
    class ModificationPlan:
        diff_hints: str

def _create_agno_modification_team() -> Team:
    analyzer = Agent(
        name="AnalyzerAgent",
        model=llm_middle,
        role="Analyzer",
        instructions=[
            "Analyze the code structure and requested change.",
            "Return ONLY JSON with an 'analysis' field describing required changes.",
            "No markdown, explanations, or extra text."
        ]
    )
    modifier = Agent(
        name="ModifierAgent",
        model=llm_highest,
        role="Modifier",
        instructions=[
            "Implement change per analyzer's JSON. Return ONLY valid JSON: file_path, original, modified.",
            "The 'modified' field MUST contain full, runnable Python code.",
            "No markdown or explanations.",
            "Output only JSON. Parse with json.loads()."
        ]
    )
    return Team(
        name="ModificationTeam",
        members=[analyzer, modifier],
        mode="coordinate",
        instructions=[
            "Work together to analyze and modify code per request.",
            "Always output final result as JSON with keys: file_path, original, modified."
        ],
        share_member_interactions=True,
        enable_agentic_context=False
    )

class AgnoCodeModificationManager:
    def __init__(self):
        self.team = _create_agno_modification_team()

    def apply_modification(
        self,
        request: "ModificationRequest",    # type: ignore
        analysis: "AnalysisResult" = None # type: ignore
    ) -> "ModificationPlan":               # type: ignore
        # Parse user prompt for file and what
        try:
            req_json = json.loads(request.user_prompt)
            file_path = req_json.get("file", "unknown.py")
            what = req_json.get("what", "")
        except Exception:
            file_path, what = "unknown.py", ""

        project_root = Path(request.project_root)
        original = ""
        fp = project_root / file_path
        if fp.exists():
            try:
                original = fp.read_text(encoding="utf-8").strip()
            except Exception:
                pass

        # Prepare state for AGNO
        state: Dict[str, Any] = {
            "file": file_path,
            "what": what,
            "original_content": original,
            "rag_context": getattr(request, "rag_context", None)
        }
        system_msg = "You are a team. Output ONLY JSON with file_path, original, modified."

        try:
            resp = self.team.run(message=system_msg, state=state)
            content = getattr(resp, "content", str(resp))

            # Parse AGNO output as JSON diff
            result = {
                "file_path": file_path,
                "original": original,
                "modified": original
            }
            if isinstance(content, str):
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        result.update(parsed)
                except Exception:
                    if "def " in content:
                        result["modified"] = content
            elif isinstance(content, dict):
                result.update(content)

            return ModificationPlan(diff_hints=json.dumps(result))

        except Exception:
            fallback = {
                "file_path": file_path,
                "original": original,
                "modified": original
            }
            return ModificationPlan(diff_hints=json.dumps(fallback))

def build_code_modification_team(**_kwargs):
    return AgnoCodeModificationManager()
