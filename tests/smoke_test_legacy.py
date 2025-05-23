# smoke_test_legacy.py
from i2c.bootstrap import initialize_environment
initialize_environment()
from pathlib import Path
from i2c.agents.modification_team.code_modification_manager_agno import (
    build_code_modification_team,
    apply_modification
)

# 1) Prepare a dummy modification step
step = {
    "file": "test_project/greetings.py",           # point at a real file under project
    "action": "modify",
    "what": "Do nothing (legacy smoke)",
    "how":  ""
}

# 2) Force legacy path
session = {"use_retrieval_tools": False}

# 3) Build the team and run
team = build_code_modification_team(session_state=session)
# Here retrieved_context can be empty, since legacy ignores it
result = apply_modification(step, Path("."), retrieved_context="", session_state=session)

print("Legacy result diff:", result.unified_diff)
