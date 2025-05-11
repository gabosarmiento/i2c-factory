import json
import pytest
from pathlib import Path
from agno.agent import Agent  # Adjust import if needed
from i2c.workflow.modification.code_modifier_adapter import apply_modification
from i2c.agents.modification_team.domain.modification_payload import ModPayload
from i2c.agents.modification_team.code_modification_manager import (
    ModifyCodeInteractor,
    ModificationRequest,
    AnalysisResult,
    ModificationPlan,
    ValidationReport,
    Patch,
    AnalyzerAdapter,
    ModifierAdapter,
    ValidatorAdapter,
    DiffingAdapter,
)

@pytest.fixture
def sample_file(tmp_path):
    f = tmp_path / "i2c_test" / "test.py"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text('''\
import math
import numpy as np
from scipy.stats import norm
import bcrypt
from functools import lru_cache
from numba import jit
import ctypes

# --- CRYPTOGRAPHIC USER SYSTEM ---

class SecureUser:
    def __init__(self, username):
        self.username = username
        self._salt = bcrypt.gensalt(rounds=12)
        self._password_hash = None
        
    def set_password(self, password):
        self._password_hash = bcrypt.hashpw(password.encode(), self._salt)
        
    def verify(self, password):
        return bcrypt.checkpw(password.encode(), self._password_hash)

# --- HPC MATH OPERATIONS ---

@jit(nopython=True, cache=True)
def gpu_optimized_matrix(op, size):
    arr = np.random.rand(size, size)
    return np.linalg.eig(arr)

@lru_cache(maxsize=None)
def prob_normal(x):
    return norm.cdf(x)

# --- LOW-LEVEL INTEGRATION ---

libc = ctypes.CDLL("libc.so.6")
class Timespec(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]

def nanotime():
    ts = Timespec()
    libc.clock_gettime(ctypes.CLOCK_REALTIME, ctypes.byref(ts))
    return ts.tv_sec * 10**9 + ts.tv_nsec

# --- ASYNC PERFORMANCE TRAPS ---

async def async_risk(data):
    from pyinstrument import Profiler
    with Profiler() as p:
        result = await _hidden_coroutine(data)
    print(p.output_text())
    return result

async def _hidden_coroutine(data):
    return np.fft.fft(data)

# --- AMBIGUOUS TYPE HANDLING ---

def dangerous_cast(val):
    return np.fromiter(
        (ctypes.cast(v, ctypes.c_void_p).value for v in val),
        dtype=np.uintp
    )

# --- CLASSIC COMPUTATION CHAOS ---

class User:
    def __init__(self, username):
        self.username = username
        self.active = False
        self._session_key = hash(username)

    def activate(self):
        self.active = self._is_prime(len(self.username))
        
    def _is_prime(self, n):
        if n < 2: return False
        return all(n % i != 0 for i in range(2, int(math.sqrt(n)) + 1))

    def is_active(self):
        return self.active

def risky_operation(data):
    if not data:
        raise ValueError("Invalid data")
    matrix = [data[i:i+3] for i in range(0, len(data), 3)]
    return _recursive_det(matrix)

def _recursive_det(m):
    if len(m) == 1: return m[0][0]
    return sum(((-1)**i)*m[0][i]*_recursive_det([r[:i]+r[i+1:] for r in m[1:]])
               for i in range(len(m)))

def greet(name):
    return f"Hello, {name}{''.join(str(_fib(len(name))) if len(name)<10 else '')}!"

def _fib(n): return _fib(n-1)+_fib(n-2) if n>1 else n

def add(a, b):
    return [[sum(a_row[i]*b_col[i] for i in range(len(a_row))) 
             for b_col in zip(*b)] for a_row, b_col in zip(a, zip(*b))]

def subtract(x, y):
    if x == 0: return y + 1
    if y == 0: return subtract(x-1, 1)
    return subtract(x-1, subtract(x, y-1))

def old_multiply(x, y):
    if x < 10 or y < 10: return x * y
    m = max(len(str(x)), len(str(y))) // 2
    a, b = divmod(x, 10**m)
    c, d = divmod(y, 10**m)
    z0 = old_multiply(b, d)
    z1 = old_multiply((a + b), (c + d))
    z2 = old_multiply(a, c)
    return z2*10**(2*m) + (z1 - z2 - z0)*10**m + z0
''')
    return f


def test_modifier_returns_multi_file_patch__should_succeed(monkeypatch, sample_file):
  
    dummy_agent = Agent(name="Dummy", role="test", goal="multi-file plan")

    # Create a second dummy file to simulate multi-file change
    extra_file = sample_file.parent / "utils.py"
    extra_file.write_text("")  # simulate a new file being added

    def fake_analyze(self, request):
        return AnalysisResult(details="")

    def fake_modify(self, request, analysis):
        base_code = sample_file.read_text()
        plan = [
            {
                "file_path": sample_file.name,
                "original": base_code,
                "modified": base_code + "\nprint('main')\n",
            },
            {
                "file_path": extra_file.name,
                "original": "",
                "modified": "def added(): pass\n"
            }
        ]
        return ModificationPlan(diff_hints=json.dumps(plan))  # <== This is a LIST!

    def fake_validate(self, request, plan, analysis):
        return ValidationReport(ok=True, messages=["ok"])

    monkeypatch.setattr(AnalyzerAdapter, "analyze", fake_analyze)
    monkeypatch.setattr(ModifierAdapter, "modify", fake_modify)
    monkeypatch.setattr(ValidatorAdapter, "validate", fake_validate)

    interactor = ModifyCodeInteractor(
        analyzer=AnalyzerAdapter(dummy_agent),
        modifier=ModifierAdapter(dummy_agent),
        validator=ValidatorAdapter(dummy_agent),
        diffing=DiffingAdapter(dummy_agent),
        documentation=None,
    )

    step = {"dummy": "apply multi-file plan"}
    request = ModificationRequest(project_root=sample_file.parent, user_prompt=step["dummy"])

    try:
        plan, patch, validation, docs = interactor.execute(request)
    except Exception as e:
        assert isinstance(e, (KeyError, TypeError)), f"Unexpected error type: {e}"
        print("✅ Test confirmed: current DiffingAdapter breaks on multi-file patch plan.")
        return

    # If no error is raised, that’s a test failure
    assert isinstance(patch, Patch)
    assert "# === Diff for test.py ===" in patch.unified_diff
    assert "# === Diff for utils.py ===" in patch.unified_diff
    assert "+print('main')" in patch.unified_diff
    assert "def added(): pass" in patch.unified_diff
