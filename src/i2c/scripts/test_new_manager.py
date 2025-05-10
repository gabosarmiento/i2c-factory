from i2c.bootstrap import initialize_environment
initialize_environment()
from pathlib import Path
from i2c.workflow.modification.code_modifier_adapter import apply_modification

# Test modification
test_step = {
    'action': 'modification',
    'file': 'test.py',  # Update with an actual file in your project
    'function': 'example_function',  # Update with an actual function 
    'what': 'Log text at the start and the result at the end',
    'how': 'Insert a logging statement at the start showing the input, and another at the end showing the result.'
}

result = apply_modification(test_step, Path("./i2c_test"))
print(result)