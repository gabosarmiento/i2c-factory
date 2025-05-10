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
    def validate(self, request: ModificationRequest, plan: ModificationPlan) -> ValidationReport: ...


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
    def execute(self, request: ModificationRequest) -> tuple[Patch, ValidationReport, DocumentationUpdate | None]:
        analysis = self.analyzer.analyze(request)
        plan = self.modifier.modify(request, analysis)
        validation = self.validator.validate(request, plan)
        if not validation.ok:
            # In a future version we could raise a domain‑specific exception or
            # return an alternative Patch; here we bail early.
            return Patch(unified_diff=""), validation, None
        patch = self.diffing.diff(request, plan)
        docs = None
        if self.documentation:
            docs = self.documentation.document(request, patch)
        return patch, validation, docs
###########################################################################


###########################################################################
# ADAPTERS LAYER – wrap Agno Agents so they satisfy the ports
###########################################################################
from agno.agent import Agent, Message  # imported *only* here


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
        text = self._ask(f"Analyze the following request:\n{request.user_prompt}")
        return AnalysisResult(details=text)


class ModifierAdapter(_AgentPortAdapter, IModifier):
    def modify(self, request: ModificationRequest, analysis: AnalysisResult) -> ModificationPlan:
        text = self._ask(
            "Generate code changes based on analysis:\n" + analysis.details
        )
        return ModificationPlan(diff_hints=text)


class ValidatorAdapter(_AgentPortAdapter, IValidator):
    def validate(self, request: ModificationRequest, plan: ModificationPlan) -> ValidationReport:
        text = self._ask("Validate the proposed changes:\n" + plan.diff_hints)
        # Placeholder parse – when we switch to Pydantic response schema this
        # will become structured.
        ok = "PASSED" in text.upper()
        return ValidationReport(ok=ok, messages=[text])


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

        try:
            payload = json.loads(plan.diff_hints)
            file_path = pathlib.Path(request.project_root, payload["file_path"]).as_posix()
            original = payload["original"].splitlines(keepends=True)
            modified = payload["modified"].splitlines(keepends=True)
        except Exception as exc:
            # Any parsing failure → empty diff so upstream can handle gracefully
            return Patch(unified_diff=f"# DiffingAgent error: {exc}")

        diff_lines = difflib.unified_diff(
            original,
            modified,
            fromfile=file_path + " (original)",
            tofile=file_path + " (modified)",
            lineterm="",
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
            role="Analyze code structure and identify modification points",
            tools=[extract_function, analyze_code_with_semantic_graph],
        )


class ModifierAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Code Modifier",
            role="Modify code according to requirements",
            tools=[
                modify_function_content,
                apply_function_to_file,
                delete_function,
                add_function,
            ],
        )


class ValidatorAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Code Validator",
            role="Validate code changes against multiple criteria",
            tools=[validate_modification],
        )
logger = logging.getLogger(__name__)
class ManagerAgent(Agent):
    """Thin Agno agent that simply drives the *Interactor* and streams back
    the final patch.  All business rules live in `ModifyCodeInteractor`.
    """

    def __init__(self, project_path: Path):
        super().__init__()
        print(">>> 🔥  ManagerAgent HAS BEEN INSTANTIATED  🔥 <<<")
        self._project_path = project_path
        # Wire concrete agents into port adapters
        self._interactor = ModifyCodeInteractor(
            analyzer=AnalyzerAdapter(AnalyzerAgent()),
            modifier=ModifierAdapter(ModifierAgent()),
            validator=ValidatorAdapter(ValidatorAgent()),
            diffing=DiffingAdapter(self._create_diffing_agent()),
            documentation=DocumentationAdapter(self._create_docs_agent()),
        )

    # These two can later be replaced with your real implementations
    def _create_diffing_agent(self) -> Agent:
        from agno.agent import Agent as _A

        class _StubDiffAgent(_A):
            def predict(self, messages: List[Message]) -> str:
                return "[DiffingAgent‑stub] TODO: implement real diffing logic."

        return _StubDiffAgent()

    def _create_docs_agent(self) -> Agent:
        from agno.agent import Agent as _A

        class _StubDocsAgent(_A):
            def predict(self, messages: List[Message]) -> str:
                return "[DocsAgent‑stub] TODO: implement docs update logic."

        return _StubDocsAgent()

    # Agno entry point ----------------------------------------------------
    def predict(self, messages: List[Message]):  # noqa: D401 – imperative form
        user_msg = messages[-1].content
        request = ModificationRequest(Path(self._project_path), user_msg)
        patch, validation, docs = self._interactor.execute(request)

        reply = (
            "## Patch\n" + patch.unified_diff + "\n\n" +
            "## Validation\n" + "\n".join(validation.messages)
        )
        if docs:
            reply += "\n\n## Documentation Update\n" + docs.summary
        return reply
###########################################################################


# Public factory used by adapter ------------------------------------------

def build_code_modification_team(project_path: Path | str) -> Team:
    manager = ManagerAgent(Path(project_path))
    return Team(
        name="Code‑Modification Team (Manager‑Clean) ",
        mode="coordinate",
        members=[manager],  # Only leader receives user messages
        messages_to_members={manager.name: "*"},
    )
