import pytest
import json
from pathlib import Path

from agno.agent import Agent, Message
from i2c.agents.modification_team.code_modification_manager import (
    ManagerAgent,
    AnalyzerAdapter,
    ModifierAdapter,
    ValidatorAdapter,
    DiffingAdapter,
    DocumentationAdapter,
    ModificationRequest,
    AnalysisResult,
    ModificationPlan,
    ValidationReport,
    DocumentationUpdate,
    ModifyCodeInteractor,
)
from i2c.agents.modification_team.patch import Patch


class DummyAnalysis(AnalysisResult):
    def __init__(self):
        super().__init__(details="dummy")


class DummyPlan(ModificationPlan):
    def __init__(self):
        super().__init__(diff_hints=json.dumps({
            "file_path": "foo.py",
            "original": "x=1\n",
            "modified": "x=1\nprint('hi')\n",
        }))


@pytest.fixture
def dummy_agent():
    # minimal Agent with session_state
    agent = Agent(name="DummyAgent", role="tester", tools=[])
    agent.team_session_state = {}
    return agent


@pytest.fixture(autouse=True)
def stub_ask(monkeypatch):
    calls = []

    def fake_ask(self, prompt: str) -> str:
        calls.append((self.__class__.__name__, prompt))
        # Analyzer: plain analysis
        if isinstance(self, AnalyzerAdapter) and prompt.startswith("Analyze the following"):
            return "analysis text"
        if isinstance(self, AnalyzerAdapter) and "analyze_code_with_semantic_graph" in prompt:
            return json.dumps({"ripple_risk": []})
        if isinstance(self, ModifierAdapter):
            return json.dumps({
                "file_path": "foo.py",
                "original": "x=1\n",
                "modified": "x=1\nprint('hi')\n",
            })
        if isinstance(self, ValidatorAdapter):
            return "PASSED"
        if isinstance(self, DocumentationAdapter):
            return "Doc summary"
        return ""

    for cls in (AnalyzerAdapter, ModifierAdapter, ValidatorAdapter, DocumentationAdapter):
        monkeypatch.setattr(cls, "_ask", fake_ask)
    return calls


def test_analyzer_prompts_and_output(dummy_agent, stub_ask):
    req = ModificationRequest(Path('.'), 'modify foo')
    adapter = AnalyzerAdapter(dummy_agent)
    analysis = adapter.analyze(req)

    assert isinstance(analysis, AnalysisResult)
    assert 'analysis text' in analysis.details

    names = [n for n,_ in stub_ask]
    assert names.count('AnalyzerAdapter') == 2
    assert 'Analyze the following modification request' in stub_ask[0][1]


def test_modifier_prompts_and_output(dummy_agent, stub_ask):
    Path('foo.py').write_text('x=1\n')
    req = ModificationRequest(Path('.'), 'modify foo')
    adapter = ModifierAdapter(dummy_agent)
    plan = adapter.modify(req, DummyAnalysis())

    assert isinstance(plan, ModificationPlan)
    payload = json.loads(plan.diff_hints)
    assert payload.get('file_path') == 'foo.py'
    assert "print('hi')" in payload.get('modified', '')

    mod_calls = [p for cls, p in stub_ask if cls == 'ModifierAdapter']
    assert mod_calls
    assert 'FILE:' in mod_calls[0] or 'json' in mod_calls[0]


def test_validator_prompts_and_output(dummy_agent, stub_ask):
    req = ModificationRequest(Path('.'), 'modify foo')
    adapter = ValidatorAdapter(dummy_agent)
    report = adapter.validate(req, DummyPlan(), DummyAnalysis())

    assert isinstance(report, ValidationReport)
    assert report.ok
    assert report.messages == ['PASSED']

    val_call = next(p for cls, p in stub_ask if cls == 'ValidatorAdapter')
    assert 'Validate the proposed changes' in val_call

import json
from pathlib import Path
from agno.agent import Agent, Message
from i2c.agents.modification_team.code_modification_manager import (
    ManagerAgent, ModifyCodeInteractor,
    AnalyzerAdapter, ModifierAdapter, ValidatorAdapter, DiffingAdapter, DocumentationAdapter
)


def with_state(agent: Agent):
    agent.team_session_state = {}
    return agent


def test_manager_delegates_and_returns_full_markdown(monkeypatch):
    # Patch _ask to simulate expected behavior
    def fake_ask(self, prompt):
        if "Analyze" in prompt:
            return "analysis text"
        if "semantic_graph" in prompt:
            return json.dumps({"ripple_risk": []})
        if isinstance(self, ModifierAdapter):
            return json.dumps({
                "file_path": "foo.py",
                "original": "x=1\n",
                "modified": "x=1\nprint('hi')\n"
            })
        if isinstance(self, ValidatorAdapter):
            return "PASSED"
        if isinstance(self, DocumentationAdapter):
            return "Doc summary"
        return "default"

    for cls in [AnalyzerAdapter, ModifierAdapter, ValidatorAdapter, DocumentationAdapter]:
        monkeypatch.setattr(cls, "_ask", fake_ask)

    manager = ManagerAgent(project_path=Path("."))
    manager.team_session_state = {}

    # Inject mock interactor with working agents
    manager._interactor = ModifyCodeInteractor(
        analyzer=AnalyzerAdapter(with_state(Agent(name="Analyzer", role="analyzes", tools=[]))),
        modifier=ModifierAdapter(with_state(Agent(name="Modifier", role="modifies", tools=[]))),
        validator=ValidatorAdapter(with_state(Agent(name="Validator", role="validates", tools=[]))),
        diffing=DiffingAdapter(with_state(Agent(name="Diffing", role="diffs", tools=[]))),
        documentation=DocumentationAdapter(with_state(Agent(name="Doc", role="writes docs", tools=[]))),
    )

    message = Message(
        role="user",
        content=json.dumps({
            "modification_step": {"user_prompt": "modify foo"},
            "retrieved_context": None
        })
    )

    result = manager.predict([message])

    assert isinstance(result, str)
    assert "## Patch" in result
    assert "## Validation" in result
    assert "## Documentation Update" in result
    assert "print('hi')" in result
    assert "PASSED" in result
    assert "## Documentation Update" in result
    assert "* **foo.py**" in result
