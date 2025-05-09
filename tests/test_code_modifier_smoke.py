import tempfile
import shutil
from pathlib import Path

import pytest

# Adjust the import path to wherever your agent lives
from agents.modification_team.code_modifier import code_modifier_agent

@pytest.fixture
def tmp_project_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)

def test_smoke_python_modify(tmp_project_dir):
    # 1) Write a trivial Python file
    src = tmp_project_dir / "foo.py"
    src.write_text(
        "def foo(x: int) -> int:\n"
        "    return x\n",
        encoding="utf-8",
    )

    # 2) Ask the agent to add a docstring
    modification_step = {
        "action": "modify",
        "file": "foo.py",
        "what": "Add a docstring",
        "how": "Insert a triple-quoted docstring '''Return x''' directly below the def line"
    }

    # 3) Run the modification
    modified = code_modifier_agent.modify_code(modification_step, tmp_project_dir)

    # 4) Smoke assertions
    assert isinstance(modified, str)
    assert "'''Return x'''" in modified or '"""Return x"""' in modified

@pytest.mark.skipif(shutil.which("tsc") is None, reason="TypeScript compiler not found")
def test_smoke_typescript_modify(tmp_project_dir):
    # 1) Write a trivial TS file
    ts = tmp_project_dir / "bar.ts"
    ts.write_text(
        "function bar(x: number): number {\n"
        "    return x;\n"
        "}\n",
        encoding="utf-8",
    )
    # ensure tsconfig exists
    (tmp_project_dir / "tsconfig.json").write_text(
        '{"compilerOptions":{"strict":true,"noEmit":true}}',
        encoding="utf-8",
    )

    # 2) Ask the agent to add a comment
    modification_step = {
        "action": "modify",
        "file": "bar.ts",
        "what": "Add a comment",
        "how": "Insert /* smoke test */ above the function declaration"
    }

    # 3) Run the modification
    modified = code_modifier_agent.modify_code(modification_step, tmp_project_dir)

    # 4) Smoke assertions
    assert isinstance(modified, str)
    assert "/* smoke test */" in modified

def test_smoke_invalid_path(tmp_project_dir):
    # If the file doesn't exist, agent should still run without crashing
    modification_step = {
        "action": "modify",
        "file": "does_not_exist.py",
        "what": "Nothing",
        "how": "Do nothing"
    }
    modified = code_modifier_agent.modify_code(modification_step, tmp_project_dir)
    assert isinstance(modified, str)
