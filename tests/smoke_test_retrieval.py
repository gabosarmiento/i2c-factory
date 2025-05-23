# smoke_test_retrieval.py
from i2c.bootstrap import initialize_environment
initialize_environment()
import os
from pathlib import Path
# from i2c.agents.modification_team.retrieval_tools import create_retrieval_tools
from i2c.agents.modification_team.retrieval_tools import (
    create_retrieval_tools,
    vector_retrieve,        # <-- raw function
    github_fetch,
    get_project_context
)
from i2c.agents.modification_team.code_modification_manager_agno import (
    build_code_modification_team,
    apply_modification
)

# 1) Dummy modification step
step = {
    "file": "test_project/greetings.py",            
    "action": "modify",
    "what": "Insert a comment referencing Agno Agent.run usage",
    "how":  ""
}

# 2) Enable retrieval
session = {"use_retrieval_tools": True}

# 3) Prepare a little retrieved context
tools = create_retrieval_tools(session)
# e.g. fetch top 3 knowledge-base snippets about Agent.run
retrieved = vector_retrieve(
    query="Agent.run usage",
    source="knowledge",
    limit=3
)
print("=== Retrieved Context ===")
print(retrieved)
print("=========================")

# 4) Build and invoke
team = build_code_modification_team(session_state=session)
try:
    result = apply_modification(
        step,
        Path("."),
        retrieved_context=retrieved,
        session_state=session
    )
    print("=== Retrieval result diff ===")
    print(result.unified_diff)
except Exception as e:
    print("❌ Retrieval flow failed:", e)
