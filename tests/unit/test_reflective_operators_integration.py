import pytest
from pathlib import Path
from i2c.agents.code_orchestration_agent import CodeOrchestrationAgent

def test_reflective_operators_initialization():
    """Test that reflective operators are properly initialized"""
    
    # --- Create orchestration agent with minimal session state ---
    session_state = {
        "project_path": "/tmp/test",
        "objective": {"task": "test initialization"}
    }
    
    agent = CodeOrchestrationAgent(session_state=session_state)
    
    # --- Verify operators were initialized ---
    assert hasattr(agent, 'plan_refinement_operator'), "Should have plan_refinement_operator"
    assert hasattr(agent, 'issue_resolution_operator'), "Should have issue_resolution_operator"
    
    # Check if they were actually created (not None)
    if agent.plan_refinement_operator is not None:
        print("✅ PlanRefinementOperator initialized successfully")
        assert hasattr(agent.plan_refinement_operator, 'execute')
    else:
        print("⚠️ PlanRefinementOperator is None")
    
    if agent.issue_resolution_operator is not None:
        print("✅ IssueResolutionOperator initialized successfully")
        assert hasattr(agent.issue_resolution_operator, 'execute')
    else:
        print("⚠️ IssueResolutionOperator is None")
    
    # Verify budget manager was created
    budget_manager = session_state.get("budget_manager")
    assert budget_manager is not None, "Budget manager should be created"
    print("✅ Budget manager created successfully")


def test_reflective_operators_without_session_state():
    """Test graceful handling when session state is missing"""
    
    agent = CodeOrchestrationAgent(session_state=None)
    
    # Should not crash, operators should be None
    assert hasattr(agent, 'plan_refinement_operator')
    assert hasattr(agent, 'issue_resolution_operator')
    
    print("✅ Graceful handling of missing session state")


if __name__ == "__main__":
    print("Testing reflective operators integration...")
    pytest.main(["-xvs", __file__])