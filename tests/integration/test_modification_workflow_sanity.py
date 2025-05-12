import pytest
from i2c.db_utils import get_db_connection
from i2c.workflow.modification.rag_config import get_embed_model
from i2c.agents.modification_team.code_modification_manager import build_code_modification_team

def test_db_connection():
    db = get_db_connection()
    assert db is not None, "DB connection failed"
    print(f"[OK] DB connected: {db}")

def test_embed_model_loading():
    embed_model = get_embed_model()
    assert embed_model is not None, "Embed model loading failed"
    dummy_embedding = embed_model.encode(["test string"])  # <-- Fixed here
    assert dummy_embedding is not None and len(dummy_embedding) > 0, "Embedding model did not return result"
    print(f"[OK] Embed model works: {dummy_embedding[0][:5]}...")  # Only show slice

def test_modification_team_build():
    team = build_code_modification_team(project_path="output/assets/project", db=None, embed_model=None)  # <-- Fixed here
    assert team is not None, "Failed to build modification team"
    assert hasattr(team, 'members') and len(team.members) > 0, "Team has no members"
    print(f"[OK] Modification team built with members: {[member.name for member in team.members]}")
