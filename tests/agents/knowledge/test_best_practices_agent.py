# tests/agents/knowledge/test_best_practices_agent.py
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import pandas as pd
import numpy as np
import json
from i2c.agents.knowledge.best_practices_agent import BestPracticesAgent
from i2c.agents.budget_manager import BudgetManagerAgent
from i2c.bootstrap import initialize_environment
initialize_environment()
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
    table.search.return_value.select.return_value.limit.return_value.to_df.return_value = pd.DataFrame({
        "content": ["def example(): pass"]
    })
    conn.open_table.return_value = table
    return conn

def test_best_practices_success(budget_manager, embed_model, db_connection):
    agent = BestPracticesAgent(budget_manager=budget_manager, embed_model=embed_model)
    
    # Mock the cost tracker
    agent.cost_tracker = Mock()
    agent.cost_tracker.trajectory = []
    
    # Mock the _execute_reasoning_step method
    def mock_execute_reasoning_step(phase_id, step_id, prompt, model_tier, **kwargs):
        return {
            "response": """```json
            [
                {"practice": "Use descriptive function names", "rationale": "Improves code readability"}
            ]
            ```""",
            "reasoning": "Test reasoning"
        }
    
    agent._execute_reasoning_step = Mock(side_effect=mock_execute_reasoning_step)
    
    # Mock retrieve_context_for_step
    with patch("agents.knowledge.best_practices_agent.retrieve_context_for_step", return_value=["def example(): pass"]):
        success, result = agent.execute(
            user_request="improve function naming",
            project_path=Path("/tmp"),
            language="python",
            db_connection=db_connection
        )
        
        assert success
        assert len(result["best_practices"]) == 1
        assert result["best_practices"][0]["practice"] == "Use descriptive function names"
        assert result["valid"]
        assert result["iterations"] == 0
        assert "reasoning_trajectory" in result

def test_best_practices_no_context(budget_manager, embed_model, db_connection):
    agent = BestPracticesAgent(budget_manager=budget_manager, embed_model=embed_model)
    
    # Mock the cost tracker
    agent.cost_tracker = Mock()
    agent.cost_tracker.trajectory = []
    
    # Mock the _execute_reasoning_step method
    def mock_execute_reasoning_step(phase_id, step_id, prompt, model_tier, **kwargs):
        return {
            "response": """```json
            [
                {"practice": "Use type hints", "rationale": "Improves type safety"}
            ]
            ```""",
            "reasoning": "Test reasoning"
        }
    
    agent._execute_reasoning_step = Mock(side_effect=mock_execute_reasoning_step)
    
    with patch("agents.knowledge.best_practices_agent.retrieve_context_for_step", return_value=[]):
        success, result = agent.execute(
            user_request="improve type safety",
            project_path=Path("/tmp"),
            language="python",
            db_connection=db_connection
        )
        
        assert success
        assert len(result["best_practices"]) == 1
        assert result["best_practices"][0]["practice"] == "Use type hints"
        assert result["valid"]
        assert "reasoning_trajectory" in result

def test_best_practices_validation_failure(budget_manager, embed_model, db_connection):
    agent = BestPracticesAgent(budget_manager=budget_manager, embed_model=embed_model)
    
    # Mock the cost tracker
    agent.cost_tracker = Mock()
    agent.cost_tracker.trajectory = []
    
    # First response with invalid practice, then fixed
    def mock_execute_reasoning_step(phase_id, step_id, prompt, model_tier, **kwargs):
        if step_id == "analyze_practices":
            return {
                "response": """```json
                [
                    {"practice": "Short", "rationale": "Invalid practice"}
                ]
                ```""",
                "reasoning": "Test reasoning"
            }
        else:
            return {
                "response": """```json
                [
                    {"practice": "Use descriptive function names", "rationale": "Improves code readability"}
                ]
                ```""",
                "reasoning": "Fixed reasoning"
            }
    
    agent._execute_reasoning_step = Mock(side_effect=mock_execute_reasoning_step)
    
    with patch("agents.knowledge.best_practices_agent.retrieve_context_for_step", return_value=[]):
        success, result = agent.execute(
            user_request="improve code",
            project_path=Path("/tmp"),
            language="python",
            db_connection=db_connection
        )
        
        assert success  # Should succeed after fixing
        assert result["valid"] is True
        assert result["iterations"] >= 1
        assert "reasoning_trajectory" in result

def test_best_practices_exception_handling(budget_manager, embed_model, db_connection):
    agent = BestPracticesAgent(budget_manager=budget_manager, embed_model=embed_model)
    
    # Mock the cost tracker
    agent.cost_tracker = Mock()
    agent.cost_tracker.trajectory = []
    
    with patch("agents.knowledge.best_practices_agent.retrieve_context_for_step", side_effect=Exception("RAG error")):
        success, result = agent.execute(
            user_request="improve code",
            project_path=Path("/tmp"),
            language="python",
            db_connection=db_connection
        )
        
        assert not success
        assert "RAG error" in result["error"]
        assert "reasoning_trajectory" in result

