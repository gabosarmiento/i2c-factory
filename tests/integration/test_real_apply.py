# tests/integration/test_modification_pipeline_live.py

import os
import json
import pytest
from pathlib import Path
from i2c.bootstrap import initialize_environment, PROJECT_ROOT

# 1) Initialize full environment (Groq, DB, models, etc.)
initialize_environment()

# 2) Use real LLM agent if available
from builtins import llm_xs

# 3) Default output folder
os.environ['DEFAULT_PROJECT_ROOT'] = str(PROJECT_ROOT / 'test_output')

# 4) System under test
from i2c.workflow.modification.code_modifier_adapter import apply_modification


@pytest.fixture
def realistic_test_file(tmp_path):
    file = tmp_path / "foo" / "danger_zone.py"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('''
import math, ctypes

class User:
    def __init__(self, name):
        self.name = name
        self._id = hash(name)
        self._raw = ctypes.create_string_buffer(b'secret')

    def activate(self):
        # complexity: check if name length is prime
        n = len(self.name)
        self.active = n > 1 and all(n % i != 0 for i in range(2, int(math.sqrt(n)) + 1))

    def __del__(self):
        del self._raw

def risky(data):
    if not data: raise ValueError("fail")
    m = [data[i:i+2] for i in range(0, len(data), 2)]
    return sum(m[0]) * len(m)

def fib(n): return fib(n-1) + fib(n-2) if n > 1 else n  # O(2^n)
''')
    return file


def test_live_pipeline_on_realistic_file(realistic_test_file):
    print("\n🚀 Running apply_modification() on realistic hard file")

    project_root = realistic_test_file.parent
    step = {"user_prompt": "Refactor this code to be safer and more maintainable."}

    result = apply_modification(step, project_root)

    if isinstance(result, dict):
        body = result.get("raw_reply", "")
        patch = body.split("## Patch", 1)[1].split("\n##", 1)[0].strip()
    else:
        patch = result.unified_diff

    print("\n🔎 PATCH RESULT:\n", patch)

    # Minimal assertions
    assert "--- danger_zone.py (original)" in patch
    assert "+++ danger_zone.py (modified)" in patch
    assert "@@" in patch
    assert "+print" in patch or "+def" in patch or "+self.active" in patch
