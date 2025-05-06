
# tests/agents/knowledge/test_knowledge_manager.py
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import pandas as pd
import numpy as np
from i2c.db_utils import SCHEMA_KNOWLEDGE_BASE
from i2c.agents.knowledge.knowledge_manager import ExternalKnowledgeManager
from i2c.bootstrap import initialize_environment
initialize_environment()
@pytest.fixture
def embed_model():
    model = Mock()
    model.encode.return_value = np.array([0.1] * 384)
    return model

@pytest.fixture
def db_connection():
    conn = Mock()
    table = Mock()
    table.delete.return_value = 1
    table.add.return_value = None
    table.schema = SCHEMA_KNOWLEDGE_BASE
    conn.open_table.return_value = table
    conn.table_names.return_value = ["knowledge_base"]
    return conn

def test_ingest_knowledge_success(embed_model, db_connection):
    with patch("agents.knowledge.knowledge_manager.get_db_connection", return_value=db_connection):
        # Mock add_or_update_chunks to avoid schema validation
        with patch("agents.knowledge.knowledge_manager.add_or_update_chunks") as mock_add:
            manager = ExternalKnowledgeManager(embed_model=embed_model)
            
            success = manager.ingest_knowledge(
                source="test.md",
                content="Sample documentation content"
            )
            
            assert success
            mock_add.assert_called_once()

def test_ingest_knowledge_empty_content(embed_model, db_connection):
    with patch("agents.knowledge.knowledge_manager.get_db_connection", return_value=db_connection):
        manager = ExternalKnowledgeManager(embed_model=embed_model)
        
        success = manager.ingest_knowledge(
            source="test.md",
            content=""
        )
        
        assert not success

def test_retrieve_knowledge_success(embed_model, db_connection):
    with patch("agents.knowledge.knowledge_manager.get_db_connection", return_value=db_connection):
        with patch("agents.knowledge.knowledge_manager.retrieve_context_for_planner") as mock_retrieve:
            mock_retrieve.return_value = pd.DataFrame({
                "source": ["doc1.md"],
                "content": ["Sample content"]
            })
            
            manager = ExternalKnowledgeManager(embed_model=embed_model)
            results = manager.retrieve_knowledge(query="test query")
            
            assert len(results) == 1
            assert results[0]["source"] == "doc1.md"
            mock_retrieve.assert_called()

def test_batch_ingest_from_files(embed_model, db_connection, tmp_path):
    with patch("agents.knowledge.knowledge_manager.get_db_connection", return_value=db_connection):
        manager = ExternalKnowledgeManager(embed_model=embed_model)
        
        file1 = tmp_path / "doc1.md"
        file1.write_text("Content 1")
        file2 = tmp_path / "doc2.md"
        file2.write_text("Content 2")
        
        # Ensure ingest_knowledge succeeds for each file
        with patch.object(manager, 'ingest_knowledge', return_value=True):
            success_count = manager.batch_ingest_from_files([file1, file2])
        
        assert success_count == 2

def test_ingest_knowledge_db_failure(embed_model):
    with patch("agents.knowledge.knowledge_manager.get_db_connection", return_value=None):
        with pytest.raises(ConnectionError):
            ExternalKnowledgeManager(embed_model=embed_model)