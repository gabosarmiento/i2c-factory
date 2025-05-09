# tests/integration/test_full_workflow.py
from i2c.tools.neurosymbolic.validators import DependencyValidator
from i2c.tools.neurosymbolic.graph import ProjectGraph
from i2c.agents.modification_team.code_modifier import CodeModifierAgent

def test_circular_dependency_handling(test_project):
    # Create circular dependency
    (test_project / "src/a.py").write_text("import b")
    (test_project / "src/b.py").write_text("import a")
    
    validator = DependencyValidator(ProjectGraph(test_project))
    errors = validator.validate("src/a.py", "modify", "")
    
    assert any("Circular dependency" in e for e in errors['errors'])

def test_validation_failure_recovery():
    agent = CodeModifierAgent()
    invalid_code = "def calculate(x): return 'invalid'"
    
    # Mock failed validation
    mock_validation = {
        'valid': False,
        'errors': ["Type mismatch for calculate"]
    }
    
    # Test fix prompt generation
    fix_prompt = agent._create_fixing_prompt(
        invalid_code,
        mock_validation
    )
    
    assert "Type mismatch" in fix_prompt
    assert "REPAIR REQUIREMENTS" in fix_prompt