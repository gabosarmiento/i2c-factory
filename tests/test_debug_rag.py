import sys
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock
import importlib.util


def load_debug_rag_module(
    monkeypatch,
    mock_db,
    mock_code_tbl,
    mock_kb_tbl,
    mock_idx
):
    """
    Monkeypatch all external side-effects, then load debug_rag.py
    as a fresh module and return it.
    """
    # 1) Remove any cached import
    sys.modules.pop("debug_rag", None)

    # 2) Patch out i2c.bootstrap.initialize_environment and PROJECT_ROOT
    import i2c.bootstrap as bb
    monkeypatch.setattr(bb, "initialize_environment", lambda: None)
    monkeypatch.setattr(bb, "PROJECT_ROOT", Path("/dummy"))

    # 3) Patch LanceDB utils
    import i2c.db_utils as dbu
    monkeypatch.setattr(dbu, "get_db_connection", lambda: mock_db)
    monkeypatch.setattr(
        dbu,
        "get_or_create_table",
        lambda db, tbl, schema: mock_code_tbl
        if tbl == dbu.TABLE_CODE_CONTEXT
        else mock_kb_tbl
    )
    # Ensure these constants exist
    monkeypatch.setattr(dbu, "TABLE_CODE_CONTEXT", "code_context")
    monkeypatch.setattr(dbu, "SCHEMA_CODE_CONTEXT", {})
    monkeypatch.setattr(dbu, "TABLE_KNOWLEDGE_BASE", "knowledge_base")
    monkeypatch.setattr(dbu, "SCHEMA_KNOWLEDGE_BASE", {})
    monkeypatch.setattr(dbu, "VECTOR_DIMENSION", 3)

    # 4) Patch ContextIndexer to use our mock
    import i2c.agents.modification_team.context_reader.context_indexer as ci_mod
    monkeypatch.setattr(ci_mod, "ContextIndexer", lambda root: mock_idx)

    

    # 6) Find debug_rag.py anywhere under project root
    project_root = Path(__file__).parent.parent.resolve()
    candidates = list(project_root.rglob("src/i2c/scripts/debug_rag.py"))
    if not candidates:
        pytest.skip("debug_rag.py not found in project directory")
    debug_path = candidates[0]

    # 7) Dynamically load debug_rag.py
    spec = importlib.util.spec_from_file_location("debug_rag", str(debug_path))
    dr = importlib.util.module_from_spec(spec)
    sys.modules["debug_rag"] = dr
    spec.loader.exec_module(dr)

    # 8) Ensure main() parses no extra args
    monkeypatch.setattr(sys, "argv", [str(debug_path)])

    return dr


def test_exit_on_zero_chunks(monkeypatch):
    # Prepare mocks
    mock_db = MagicMock()
    mock_code_tbl = MagicMock()
    mock_kb_tbl = MagicMock()
    # index_project returns zero chunks
    mock_idx = MagicMock()
    mock_idx.index_project.return_value = {"chunks_indexed": 0}

    dr = load_debug_rag_module(monkeypatch, mock_db, mock_code_tbl, mock_kb_tbl, mock_idx)

    # Expect SystemExit(1)
    with pytest.raises(SystemExit) as se:
        dr.main()
    assert se.value.code == 1


def test_empty_search_reports(monkeypatch, capsys):
    # Prepare mocks
    mock_db = MagicMock()
    # code_tbl.search(...).limit(...).to_pandas() → empty DataFrame
    searcher = MagicMock()
    searcher.limit.return_value = searcher
    searcher.to_pandas.return_value = pd.DataFrame()
    mock_code_tbl = MagicMock(search=MagicMock(return_value=searcher))
    mock_kb_tbl = MagicMock()
    # index_project returns some chunks
    mock_idx = MagicMock()
    mock_idx.index_project.return_value = {"chunks_indexed": 5}
    mock_idx.embed_model = lambda text: [0.0]*3

    dr = load_debug_rag_module(monkeypatch, mock_db, mock_code_tbl, mock_kb_tbl, mock_idx)
    dr.main()

    out = capsys.readouterr().out
    assert "Query returned no rows" in out


def test_retrieve_context_prints(monkeypatch, capsys):
    # Prepare mocks
    mock_db = MagicMock()
    # code_tbl.search(...).limit(...).to_pandas() → DataFrame with one path
    df = pd.DataFrame({"path": ["src/example.py"]})
    searcher = MagicMock()
    searcher.limit.return_value = searcher
    searcher.to_pandas.return_value = df
    mock_code_tbl = MagicMock(search=MagicMock(return_value=searcher))
    mock_kb_tbl = MagicMock()
    # index_project returns some chunks
    mock_idx = MagicMock()
    mock_idx.index_project.return_value = {"chunks_indexed": 2}
    mock_idx.embed_model = lambda text: [0.0]*3

    # Override retrieve_context_for_step to return real-looking context
    import i2c.workflow.modification.rag_retrieval as rr
    monkeypatch.setattr(rr, "retrieve_context_for_step", lambda step, db, em: "SAMPLE_CONTEXT")

    dr = load_debug_rag_module(monkeypatch, mock_db, mock_code_tbl, mock_kb_tbl, mock_idx)
    dr.main()

    out = capsys.readouterr().out
    assert "retrieve_context_for_step returned:" in out
    assert "SAMPLE_CONTEXT" in out
