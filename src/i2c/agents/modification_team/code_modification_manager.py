# -*- coding: utf-8 -*-
"""code_modification_manager.py – Clean‑Architecture, SOLID‑compliant skeleton

This replaces the first draft with a version that follows **Clean Architecture**
(entities → use‑cases → interface adapters → framework) and applies the five
**SOLID** principles.  It is still a *stub* (no real LLM calls yet) but now it
slots cleanly into your existing `src/i2c/workflow/modification` stack.

Layers
------
• **domain/** – immutable *entities* & value objects: `ModificationRequest`,
  `AnalysisResult`, `Patch`, etc.
• **use_case/** – orchestrates the entity flow. `ModifyCodeInteractor`
  coordinates Analyzer → Modifier → Validator → Diffing → Docs via *ports*.
• **adapters/** – concrete Agents (powered by Agno or legacy code) that satisfy
  the ports.
• **framework/** – Agno‑specific plumbing and the public factory
  `build_code_modification_team()`.

Dependency rule: lower layers know nothing about Agno, LLMs, or network I/O.

Usage in existing pipeline
--------------------------
`code_modifier_adapter.apply_modification()` will import the *framework layer*
factory and obtain a team; the rest of the `execute_cycle.py` loop stays the
same.
"""

from __future__ import annotations

###########################################################################
# DOMAIN LAYER – immutable value objects (no Agno imports here!)
###########################################################################
from dataclasses import dataclass
from pathlib import Path
from typing import List, Protocol
import logging




@dataclass(frozen=True)
class ModificationRequest:
    project_root: Path
    user_prompt: str


@dataclass(frozen=True)
class AnalysisResult:
    details: str  # ← free‑form text or JSON produced by Analyzer


@dataclass(frozen=True)
class ModificationPlan:
    diff_hints: str  # ← e.g. "Change users.get_users to add logging"


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    messages: List[str]


@dataclass(frozen=True)
class Patch:
    unified_diff: str


@dataclass(frozen=True)
class DocumentationUpdate:
    summary: str
###########################################################################


###########################################################################
# USE‑CASE LAYER – business logic; depends *only* on domain & ports
###########################################################################
# 1. Define ports (interfaces) – Interface Segregation + Dependency Inversion
###########################################################################

class IAnalyzer(Protocol):
    def analyze(self, request: ModificationRequest) -> AnalysisResult: ...


class IModifier(Protocol):
    def modify(self, request: ModificationRequest, analysis: AnalysisResult) -> ModificationPlan: ...


class IValidator(Protocol):
    def validate(self, request: ModificationRequest, plan: ModificationPlan, analysis: AnalysisResult,) -> ValidationReport: ...


class IDiffing(Protocol):
    def diff(self, request: ModificationRequest, plan: ModificationPlan) -> Patch: ...


class IDocumentation(Protocol):
    def document(self, request: ModificationRequest, patch: Patch) -> DocumentationUpdate: ...
###########################################################################


class ModifyCodeInteractor:
    """Pure‑python orchestrator that enforces the use‑case flow.

    – Single Responsibility: one* job – produce a validated Patch.
    – Open/Closed: accepts any objects that implement the ports.
    – Liskov: callers rely only on interface contracts.
    – Dependency Inversion: high‑level policy (#Interactor) knows *nothing*
      about Agno or concrete agents.
    """

    def __init__(
        self,
        analyzer: IAnalyzer,
        modifier: IModifier,
        validator: IValidator,
        diffing: IDiffing,
        documentation: IDocumentation | None = None,
    ) -> None:
        self.analyzer = analyzer
        self.modifier = modifier
        self.validator = validator
        self.diffing = diffing
        self.documentation = documentation

    # -------------------------------------------------------
    # The orchestration method itself
    # -------------------------------------------------------
    def execute(self, request: ModificationRequest) -> tuple[ModificationPlan, Patch, ValidationReport, DocumentationUpdate | None]:
        analysis = self.analyzer.analyze(request)
        plan = self.modifier.modify(request, analysis)
        validation = self.validator.validate(request, plan, analysis)
        if not validation.ok:
            return plan, Patch(unified_diff=""), validation, None
        patch = self.diffing.diff(request, plan)
        docs = self.documentation.document(request, patch) if self.documentation else None
        return plan, patch, validation, docs
###########################################################################


###########################################################################
# ADAPTERS LAYER – wrap Agno Agents so they satisfy the ports
###########################################################################
import os
from agno.agent import Agent, Message  # imported *only* here
from agno.tools import tool
from agno.models.groq import Groq
from i2c.tools.neurosymbolic.semantic_tool import SemanticGraphTool
import json
from builtins import llm_xs, llm_middle
from dataclasses import asdict
from i2c.agents.modification_team.domain.modification_payload import ModPayload 
import difflib, json, pathlib
import pydantic
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2')
MIN_THRESHOLD = os.getenv('MIN_THRESHOLD', 0)
class _AgentPortAdapter:
    """Base helper that turns an Agno Agent into a port implementation."""

    def __init__(self, agent: Agent):
        self._agent = agent

    # Utility – run agent synchronously and return plain text
    def _ask(self, prompt: str) -> str:
        messages = [Message(role="user", content=prompt)]
        return self._agent.predict(messages)


# Concrete port adapters (Single Responsibility: one method each)
class AnalyzerAdapter(_AgentPortAdapter, IAnalyzer):
    def analyze(self, request: ModificationRequest) -> AnalysisResult:
        # 1) Ask the LLM for plain-language analysis of the change
        analysis_txt = self._ask(
            f"Analyze the following modification request:\n{request.user_prompt}"
        )

        # 2) Use SemanticGraphTool to fetch dependency map for the target symbol
        dep_json = self._ask(
            "Use analyze_code_with_semantic_graph to return ONLY JSON:\n"
            '{ "ripple_risk": [ "module.func", "module.Class.method", ... ] }'
        )

        combined = json.dumps(
            {"analysis": analysis_txt, "dependencies": json.loads(dep_json)},
            ensure_ascii=False,
            indent=2,
        )
        # cache ripple list for Validator to read directly
        ripple = json.loads(dep_json).get("ripple_risk", [])
        self._agent.team_session_state["risk_map"] = ripple
        return AnalysisResult(details=combined)


class ModifierAdapter(_AgentPortAdapter, IModifier):
    
    """Wrap ModifierAgent and emit a JSON payload for DiffingAdapter.

    Strategy:
      1. Ask the underlying ModifierAgent for **new file content only**.
         Our prompt instructs it to reply with the *full modified source*
         preceded by a header line `FILE: relative/path.py`.

      2. We read the *current* on‑disk content of that file.

      3. Build `diff_hints` JSON payload expected by DiffingAdapter.
         This keeps us LLM‑agnostic downstream.
    """

    _FILE_HEADER = "FILE:"  # magic keyword the LLM must echo

    def modify(self, request: ModificationRequest, analysis: AnalysisResult) -> ModificationPlan:
        # Prompt the modifier to output: first line 'FILE: relative/path.py',
        # then a blank line, then the *full new source code*.
        prompt = (
            "You are the Code Modifier.\n"
            "First line: 'FILE: <relative path>'.\n"
            "Blank line. Then paste the full *modified* file content.\n\n"
            f"Here is the user request:\n{request.user_prompt}\n\n"
            f"Here is analysis context:\n{analysis.details}"
        )
        

        # --- Parse reply --------------------------------------------------
        raw_reply = self._ask(prompt)
        import json, pathlib
        try:
            data = json.loads(raw_reply)
            rel_path = data["file_path"]
            modified_src = data["modified"]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            return ModificationPlan(
                diff_hints=json.dumps({"error": "UNPARSEABLE_MODIFIER_REPLY", "raw": raw_reply})
            )

        abs_path = pathlib.Path(request.project_root, rel_path)
        try:
            original_src = abs_path.read_text()
        except FileNotFoundError:
            original_src = ""  # new file – diff against empty

        # payload = json.dumps(
        #     {
        #         "file_path": rel_path,
        #         "original": original_src,
        #         "modified": modified_src,
        #     },
        #     ensure_ascii=False,
        # )
        # build a strongly-typed payload
        payload_obj = ModPayload(
            file_path=rel_path,
            original=original_src,
            modified=modified_src,
        )
        
        payload = json.dumps(asdict(payload_obj), ensure_ascii=False)
        return ModificationPlan(diff_hints=payload)

class ValidatorAdapter(_AgentPortAdapter, IValidator):
    def validate(
        self,
        request: ModificationRequest,
        plan: ModificationPlan,
        analysis: AnalysisResult,
    ) -> ValidationReport:
        # Base validation via tool
        base = self._ask("Validate the proposed changes:\n" + plan.diff_hints)
        msgs = [base]
        ok = "PASSED" in base.upper()

        # ---- Ripple-effect check (cached) -------------------------------------------
        deps = self._agent.team_session_state.get("risk_map", [])

        if deps:
            ok = False
            msgs.append(
                "RIPPLE WARNING • these symbols may break: " + ", ".join(deps[:10])
            )

        return ValidationReport(ok=ok, messages=msgs)



class DiffingAdapter(_AgentPortAdapter, IDiffing):
    """Adapter that asks DiffingAgent to compute a minimal unified diff.

    Expects the *ModifierAgent* to have written a JSON payload into
    `ModificationPlan.diff_hints` with the following structure::

        {
          "file_path": "relative/to/project/foo.py",
          "original": "
...original source...
",
          "modified": "
...new source...
"
        }

    If that contract is not met we return an *empty* Patch so the
    validator can still run and raise a helpful error.
    """

    def diff(self, request: ModificationRequest, plan: ModificationPlan) -> Patch:
        import difflib, json, pathlib
        # Validate that diff_hints is a proper ModPayload JSON
        if not isinstance(plan.diff_hints, str):
            return Patch(unified_diff="# DiffingAdapter error: diff_hints is not a string")
        
        try:
            payload = json.loads(plan.diff_hints)
            # Use the relative path for headers, not the absolute path
            rel = payload["file_path"]
            original = payload["original"].splitlines(keepends=True)
            modified = payload["modified"].splitlines(keepends=True)
        except Exception as exc:
            # Reject invalid payloads → empty diff so upstream can handle gracefully
            return Patch(unified_diff=f"# DiffingAdapter error: {exc}")

        diff_lines = difflib.unified_diff(
            original,
            modified,
            fromfile=rel + " (original)",
            tofile=rel + " (modified)",
            lineterm="\n",
        )
        return Patch(unified_diff="".join(diff_lines))

import re
import textwrap
from typing import List
class DocumentationAdapter(_AgentPortAdapter, IDocumentation):
    """Generate a human-readable *changelog snippet* from the unified diff,
    without using an LLM."""
    
    _HUNK_RE = re.compile(r"^@@ .* @@")

    def document(self, request: ModificationRequest, patch: Patch) -> DocumentationUpdate:
        # If there's no diff at all, bail out early
        if not patch.unified_diff.strip():
            return DocumentationUpdate(
                summary="*(No changes detected – no documentation update required)*"
            )

        # Split into lines correctly
        lines: List[str] = patch.unified_diff.splitlines()
        file_path: str | None = None
        entries: List[str] = []

        for line in lines:
            # e.g. "--- path/to/file (original)"
            if line.startswith("--- ") and " (original)" in line:
                file_path = line.split(" (original)")[0][4:].strip()
            elif self._HUNK_RE.match(line):
                hunk_desc = line.replace("@@", "").strip()
                if file_path:
                    entries.append(f"* **{file_path}** – {hunk_desc}")

        if not entries:
            entries.append("* Minor internal refactor; no user-visible impact.")

        # Join with real newlines
        md = "\n".join(entries)
        md_wrapped = textwrap.dedent(f"""
        ### Changelog
        {md}
        """).strip()

        return DocumentationUpdate(summary=md_wrapped)

###########################################################################


###########################################################################
# FRAMEWORK LAYER – Agno Team wrapper (depends on everything above)
###########################################################################
from agno.team import Team


# ––– Import legacy concrete agents (existing implementation) –––
from i2c.agents.modification_team.function_modification_team import (
    extract_function,
    analyze_code_with_semantic_graph,
    modify_function_content,
    apply_function_to_file,
    delete_function,
    add_function,
    validate_modification,
)

# Local wrappers so we don’t depend on non‑existent classes
class AnalyzerAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Code Analyzer",
            model=llm_xs,
            description="Inspects existing code and pinpoints exactly where a change should occur, producing a structured analysis.",
            tools=[extract_function, analyze_code_with_semantic_graph],
            instructions=[
                "You are an expert Static Analyzer tasked with pinpointing the exact location for code changes with precision and clarity.",
                "",
                "## INPUT",
                "- User request (natural language) describing the desired change.",
                "- Optional context snippets providing insights into the project’s coding style, structure, and conventions.",
                "",
                "## TASK",
                "1. **Parse the Request**: Analyze the user’s request to understand *what* must change in the code (e.g., functionality, logic, structure).",
                "2. **Locate the Change Area**: Use the provided tools (e.g., `extract_function`, `analyze_code_with_semantic_graph`) to identify the precise file(s) and line range(s) where the change should occur.",
                "3. **Analyze Dependencies**: Use the SemanticGraphTool to detect any dependencies, ripple effects, or related code that might be impacted by the change.",
                "4. **Consider Context**: If context snippets are provided, use them to ensure the analysis aligns with the project’s coding style, naming conventions, and design patterns.",
                "",
                "## OUTPUT",
                "- Return a compact JSON object for each affected file in the following format:",
                "  {",
                "    \"file_path\": \"relative/path.py\",",
                "    \"start_line\": <int>,",
                "    \"end_line\": <int>,",
                "    \"rationale\": \"<concise explanation of why this area was chosen>\"",
                "  }",
                "- If multiple files are affected, provide an array of such JSON objects.",
                "- If no specific location can be pinpointed, return an empty array and include a rationale explaining why (e.g., the change may require creating a new file or a broader refactoring).",
                "- Do NOT include markdown, additional commentary, or explanations beyond the specified JSON format.",
                "",
                "## QUALITY STANDARDS",
                "- **Precision**: Ensure the identified line range is as narrow as possible, targeting only the necessary code for the change.",
                "- **Accuracy**: Verify that the selected area directly corresponds to the user’s request and is correctly located within the file.",
                "- **Completeness**: Include all relevant files and line ranges if the change spans multiple areas or files.",
                "- **Context Awareness**: Use context snippets to ensure the analysis respects the project’s conventions and avoids conflicts with existing code.",
                "- **Dependency Awareness**: Highlight any dependencies or potential side effects to prevent unintended consequences in the modification step.",
                "",
                "## ADDITIONAL NOTES",
                "- If the change involves creating a new file or significant refactoring, indicate this in the rationale and suggest a potential file path or approach.",
                "- Ensure the JSON output is machine-readable and strictly adheres to the specified structure for seamless integration with the Code Modification Agent."
            ],
        )


class ModifierAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Code Modifier",
            model=llm_xs,
            description="Generates modified or new code based on Analyzer output and user intent, adhering to project conventions.",
            tools=[
                modify_function_content,
                apply_function_to_file,
                delete_function,
                add_function,
            ],
            instructions=[
                "You are an expert Code Modification Agent tasked with generating or modifying code to match or exceed the highest quality standards, such as those set by DeepSeek or OpenAI.",
                "",
                "## Input",
                "- **Analyzer JSON**: Specifies the area(s) in the code that require changes (may involve multiple files).",
                "- **User Instruction**: A natural-language description of the required changes.",
                "- **Context Snippets**: Optional; provides insights into the project's coding style, patterns, and conventions.",
                "",
                "## Task",
                "- Generate or modify code to precisely fulfill the user’s instruction while adhering to the project’s conventions and industry best practices.",
                "- If multiple files are involved, provide separate outputs for each file.",
                "",
                "## Quality Standards",
                "- **Functionality**: Ensure the code fully satisfies all specified requirements and delivers correct, reliable outputs.",
                "- **Readability**: Use descriptive, meaningful variable names and maintain consistent formatting (e.g., indentation, spacing).",
                "- **Maintainability**: Structure the code modularly with clear interfaces, minimizing dependencies and enabling easy updates.",
                "- **Performance**: Optimize algorithms and data structures for efficiency; eliminate unnecessary computations or memory usage.",
                "- **Security**: Include robust input validation, proper error handling, and safeguards against vulnerabilities (e.g., injection attacks).",
                "- **Testing**: Ensure the code is testable, considering edge cases and providing guidance for unit/integration tests if relevant.",
                "- **Documentation**: Add or update comments and docstrings to clearly explain the code’s purpose, usage, and modifications.",
                "",
                "## Rules",
                "- Preserve existing functionality unless explicitly instructed to alter it.",
                "- Match the project’s coding style (e.g., PEP8 for Python) based on context or default to widely accepted standards.",
                "- Use consistent, self-explanatory naming conventions that align with the codebase.",
                "- Include or update type hints where applicable, following the project’s conventions.",
                "- Modify or remove only the necessary code, leaving unrelated sections intact and operational.",
                "- For new files, ensure seamless integration with the existing project structure.",
                "- After generating the new file, construct a JSON object exactly matching {\"file_path\": ..., \"original\": ..., \"modified\": ...} and output *only* that JSON (no code) as the message content.",
                "- Leverage context snippets to maintain consistency in style, error handling, and design patterns.",
                "- Avoid adding new dependencies unless explicitly required and justified.",
                "",
                "## Output Format (STRICT)",
                "- Output *only* a single JSON object matching exactly {\"file_path\": <relative path>, \"original\": <full original source>, \"modified\": <full modified source>}. No other text.",
                "",
                "## Additional Considerations",
                "- Ensure compatibility with the target environment, including platforms, libraries, and frameworks.",
                "- Design for scalability to handle future growth, such as increased data sizes or user loads.",
                "- Enhance user experience with efficient, responsive code and clear, helpful error messages.",
                "- Align with version control best practices (e.g., atomic changes) if relevant to the project."
            ],
        )


class ValidatorAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Code Validator",
            model=llm_xs,
            description="Checks syntax, style, and semantic safety of the proposed code change, returning a pass/fail verdict and reasons.",
            tools=[validate_modification],
            instructions=[
                "You are a meticulous Code Reviewer enforcing the highest standards of quality and safety.",
                "",
                "## TASK",
                "- Execute all validation tools (e.g., `validate_modification`) on the proposed code change.",
                "- Scrutinize for:",
                "  - Syntax errors (e.g., unparseable code, missing delimiters)",
                "  - Style violations (e.g., PEP8 deviations, inconsistent formatting)",
                "  - Semantic risks (e.g., logic flaws, runtime errors, security weaknesses)",
                "",
                "## OUTPUT",
                "- If the code is flawless, return exactly one line:",
                "  PASSED",
                "- If any issue is detected, return one line:",
                "  FAILED • <reason 1> • <reason 2> • …",
                "- Each reason must be concise (≤15 words) and pinpoint the exact problem.",
                "- No additional text, explanations, or suggestions beyond this format.",
                "",
                "## RULES",
                "- Be unrelenting: even minor deviations (e.g., a single style issue) trigger a `FAILED` verdict.",
                "- Ensure every check is exhaustive, leaving no room for oversight.",
                "- Your judgment is final—only perfect code passes."
            ],
        )
logger = logging.getLogger(__name__)

# --------------------------------------------------
# Real DiffingAgent  (pure‑python, no LLM call)
# --------------------------------------------------
class DiffingAgent(Agent):
    def predict(self, messages: List[Message]) -> str:
        import json, difflib
        payload = json.loads(messages[-1].content)   # {file_path, original, modified}
        f = payload["file_path"]
        diff = difflib.unified_diff(
            payload["original"].splitlines(keepends=True),
            payload["modified"].splitlines(keepends=True),
            fromfile=f"{f} (original)",
            tofile=f"{f} (modified)",
            lineterm=""
        )
        return "".join(diff)

# --------------------------------------------------
# Real DocsAgent  (deterministic changelog maker)
# --------------------------------------------------
class DocsAgent(Agent):
    _HUNK_RE = re.compile(r"^@@ .* @@")

    def predict(self, messages: List[Message]) -> str:
        diff_text = messages[-1].content
        if not diff_text.strip():
            return "*(No changes detected – no documentation update required)*"
        entries, current = [], None
        for ln in diff_text.splitlines():
            if ln.startswith("--- ") and " (original)" in ln:
                current = ln[4:].split(" (original)")[0].strip()
            elif self._HUNK_RE.match(ln) and current:
                entries.append(f"* **{current}** – {ln.replace('@@','').strip()}")
        if not entries:
            entries.append("* Minor internal refactor; no user‑visible impact.")
        return "### Changelog\n" + "\n".join(entries)

class ManagerAgent(Agent):
    """Thin Agno agent that simply drives the *Interactor* and streams back
    the final patch.  All business rules live in `ModifyCodeInteractor`.
    """

    def __init__(self, project_path: Path):
        super().__init__(
            name="ManagerAgent",
            model=llm_middle,
            description="You are the team orchestrator that understands the user’s request, plans the optimal agent sequence with agents, provides each agent with precise context, and compiles the final Patch +Validation + Changelog response.",
            tools=[],  # Manager doesn’t need to expose tools; members have them
            instructions=[
                "You are the team leader.",
                "— Receive a *single* natural‑language modification request.",
                "— Decompose it into sub‑tasks (analysis, code generation, validation, "
                "  diff creation, documentation).",
                "— Delegate each sub‑task to the most suitable specialist agent.",
                "— Ensure each agent receives ONLY the context it needs (privacy & "
                "  token efficiency).",
                "— If validation fails, decide whether to retry with new instructions "
                "  or abort gracefully.",
                "— Assemble the final answer with these sections only:",
                "    ## Patch",
                "    ## Validation",
                "    ## Changelog",
                "— Do not expose internal reasoning chains.",
            ],
            add_name_to_instructions=True,
        )
        logger.info(">>> 🔥  ManagerAgent HAS BEEN INSTANTIATED  🔥 <<<")
        self._project_path = project_path
        # Wire concrete agents into port adapters
        self._interactor = ModifyCodeInteractor(
            analyzer=AnalyzerAdapter(AnalyzerAgent()),
            modifier=ModifierAdapter(ModifierAgent()),
            validator=ValidatorAdapter(ValidatorAgent()),
            diffing=DiffingAdapter(DiffingAgent()),
            documentation=DocumentationAdapter(DocsAgent()),
        )

    # --- Wire SemanticGraphTool into the Agno team as a “knowledge” resource
    @tool()
    def get_callers(agent: Agent, function_name: str) -> str:
        """
        Return the list of callers of `function_name` from the pre-built semantic graph.
        """
        sem: SemanticGraphTool = agent.team_session_state["semantic_graph_tool"]
        callers = sem.get_callers(function_name)
        return json.dumps({"callers": callers})

    # Agno entry point ----------------------------------------------------
    def predict(self, messages: List[Message]) -> str:  # noqa: D401 – imperative form
        # 0) Build the request
        user_msg = messages[-1].content
        request = ModificationRequest(Path(self._project_path), user_msg)

        # 1) Run the full interactor, grabbing the raw plan up front
        plan, patch, validation, docs = self._interactor.execute(request)

        # 2) Immediately sanity-check that diff_hints is valid ModPayload JSON
        try:
            ModPayload(**json.loads(plan.diff_hints))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            return (
                "## Validation\n"
                "FAILED • Modifier produced invalid payload • "
                f"{e}"
            )

        # 3) Build the standard reply
        reply = (
            "## Patch\n"
            + patch.unified_diff
            + "\n\n"
            "## Validation\n"
            + "\n".join(validation.messages)
        )
        if docs:
            reply += "\n\n## Documentation Update\n" + docs.summary

        return reply    

    def before_cycle(self, cycle_idx: int):
        remaining = self.team_session_state.get("remaining_budget", 0.0)
        logger.info(f"🪙 Budget check before step {cycle_idx}: ${remaining:.2f} left")
        if remaining < MIN_THRESHOLD:
            raise RuntimeError(f"Budget exhausted before modification step {cycle_idx}")
###########################################################################


# Public factory used by adapter ------------------------------------------

def build_code_modification_team(project_path: Path | str, **kwargs ) -> Team:
    
    
    manager = ManagerAgent(Path(project_path))
    # build one shared SemanticGraphTool (it handles graph + validators internally)
    sem_tool = SemanticGraphTool(project_path=Path(project_path))
    return Team(
        name="Code‑Modification Team (Manager‑Clean) ",
        mode="coordinate",
        model=llm_xs, 
        members=[manager],
        instructions=[
            "Your goal is to safely modify code per user request, flag ripple-risks, and produce a unified diff."
        ],
        session_state={ "risk_map": {}, "semantic_graph_tool": sem_tool },
        enable_agentic_context=False,
        share_member_interactions=False, # Prevent sharing intermediate outputs between agents
        show_members_responses=False,    # Prevent raw responses from leaking
        success_criteria="Patch is valid, ripple-risks are addressed, and docs are updated if needed."
    )
