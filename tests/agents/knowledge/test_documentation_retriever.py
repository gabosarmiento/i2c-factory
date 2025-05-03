# tests/agents/knowledge/test_documentation_retriever.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import pandas as pd
import numpy as np
import json
from agents.knowledge.documentation_retriever import DocumentationRetrieverAgent
from agents.budget_manager import BudgetManagerAgent

@pytest.fixture
def budget_manager():
    return Mock(spec=BudgetManagerAgent, consumed_tokens_session=0, consumed_cost_session=0)

@pytest.fixture
def embed_model():
    model = Mock()
    model.encode.return_value = np.array([0.1] * 384)
    return model

@pytest.fixture
def db_connection():
    conn = Mock()
    table = Mock()
    
    # Create a proper mock for the search chain
    search_result = Mock()
    select_result = Mock()
    limit_result = Mock()
    
    # Set up the dataframe that will be returned
    df = pd.DataFrame({
        "source": ["doc1.md", "doc2.md"],
        "content": ["Sample doc content 1", "Sample doc content 2"]
    })
    limit_result.to_df.return_value = df
    select_result.limit.return_value = limit_result
    search_result.select.return_value = select_result
    table.search.return_value = search_result
    
    # Mock the schema to properly handle vector field validation
    schema = Mock()
    schema.get_field_index.return_value = 0
    field = Mock()
    field.type.list_size = 384
    schema.field.return_value = field
    # Make schema iterable to avoid 'Mock not iterable' error
    schema.__iter__ = Mock(return_value=iter([field]))
    field.name = "vector"
    table.schema = schema
    
    conn.open_table.return_value = table
    return conn

def test_documentation_retriever_success(budget_manager, embed_model, db_connection):
    agent = DocumentationRetrieverAgent(budget_manager=budget_manager, embed_model=embed_model)
    
    # Mock the cost tracker
    agent.cost_tracker = Mock()
    agent.cost_tracker.trajectory = []
    
    # Mock the _execute_reasoning_step method
    def mock_execute_reasoning_step(phase_id, step_id, prompt, model_tier, **kwargs):
        return {
            "response": """```json
            [
                {"source": "doc1.md", "content": "Sample doc content 1", "relevance_score": 0.9}
            ]
            ```""",
            "reasoning": "Test reasoning"
        }
    
    agent._execute_reasoning_step = Mock(side_effect=mock_execute_reasoning_step)
    
    # Patch query_context directly to avoid database issues
    with patch("agents.knowledge.documentation_retriever.query_context") as mock_query:
        mock_query.return_value = pd.DataFrame({
            "source": ["doc1.md", "doc2.md"],
            "content": ["Sample doc content 1", "Sample doc content 2"]
        })
        
        success, result = agent.execute(
            query="test query",
            project_path=Path("/tmp"),
            language="python",
            db_connection=db_connection
        )
    
    assert success
    assert len(result["documents"]) == 1
    assert result["documents"][0]["source"] == "doc1.md"
    assert result["valid"]
    assert result["iterations"] == 0
    assert "reasoning_trajectory" in result

def test_documentation_retriever_no_results(budget_manager, embed_model, db_connection):
    agent = DocumentationRetrieverAgent(budget_manager=budget_manager, embed_model=embed_model)
    
    # Mock the cost tracker
    agent.cost_tracker = Mock()
    agent.cost_tracker.trajectory = []
    
    db_connection.open_table.return_value.search.return_value.select.return_value.limit.return_value.to_df.return_value = pd.DataFrame()
    
    success, result = agent.execute(
        query="test query",
        project_path=Path("/tmp"),
        language="python",
        db_connection=db_connection
    )
    
    assert not success
    assert result["error"] == "No documentation retrieved"
    assert "reasoning_trajectory" in result

def test_documentation_retriever_validation_failure(budget_manager, embed_model, db_connection):
    agent = DocumentationRetrieverAgent(budget_manager=budget_manager, embed_model=embed_model)
    
    # Mock the cost tracker
    agent.cost_tracker = Mock()
    agent.cost_tracker.trajectory = []
    
    # First response with invalid relevance score
    def mock_execute_reasoning_step(phase_id, step_id, prompt, model_tier, **kwargs):
        if step_id == "analyze_docs":
            return {
                "response": """```json
                [
                    {"source": "doc1.md", "content": "Sample doc content 1", "relevance_score": 2.0}
                ]
                ```""",
                "reasoning": "Test reasoning"
            }
        else:
            return {
                "response": """```json
                [
                    {"source": "doc1.md", "content": "Sample doc content 1", "relevance_score": 0.9}
                ]
                ```""",
                "reasoning": "Fixed reasoning"
            }
    
    agent._execute_reasoning_step = Mock(side_effect=mock_execute_reasoning_step)
    
    # Patch query_context directly
    with patch("agents.knowledge.documentation_retriever.query_context") as mock_query:
        mock_query.return_value = pd.DataFrame({
            "source": ["doc1.md", "doc2.md"],
            "content": ["Sample doc content 1", "Sample doc content 2"]
        })
        
        success, result = agent.execute(
            query="test query",
            project_path=Path("/tmp"),
            language="python",
            db_connection=db_connection
        )
    
    assert success  # Should succeed after fixing
    assert result["valid"] is True
    assert result["iterations"] >= 1
    assert "reasoning_trajectory" in result

def test_documentation_retriever_exception_handling(budget_manager, embed_model, db_connection):
    agent = DocumentationRetrieverAgent(budget_manager=budget_manager, embed_model=embed_model)
    
    # Mock the cost tracker
    agent.cost_tracker = Mock()
    agent.cost_tracker.trajectory = []
    
    with patch("agents.knowledge.documentation_retriever.query_context", side_effect=Exception("DB error")):
        success, result = agent.execute(
            query="test query",
            project_path=Path("/tmp"),
            language="python",
            db_connection=db_connection
        )
        
        assert not success
        assert "DB error" in result["error"]
        assert "reasoning_trajectory" in result

