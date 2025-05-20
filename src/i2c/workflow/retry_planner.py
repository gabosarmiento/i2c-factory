
from i2c.workflow.reflective_validation import ValidationResult

class RetryPlanner:
    def __init__(self, project_path: str):
        self.project_path = project_path

    def plan_retry(self, result: ValidationResult) -> dict:
        if result.success:
            return {"retry_needed": False, "reason": "Validation passed."}

        plan = {
            "retry_needed": True,
            "reason": result.failure_type,
            "actions": []
        }

        if result.failure_type == "syntax_error":
            plan["actions"].append("Use LLM to reformat or fix indentation in failing file.")
        elif result.failure_type == "import_error":
            plan["actions"].append("Check and regenerate missing import/module.")
        elif result.failure_type == "attribute_error":
            plan["actions"].append("Recheck method/attribute names across modified files.")
        elif result.failure_type == "test_failure":
            plan["actions"].append("Review failed test logic and regenerate test/function.")
        else:
            plan["actions"].append("Manual review required. Unknown error.")

        return plan
