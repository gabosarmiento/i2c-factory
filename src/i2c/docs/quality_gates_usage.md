# Quality Gates Usage Examples

This document provides examples of how to use the enterprise quality gates in different scenarios.

## Example 1: Check Python Files

```bash
# Check a Python file with all Python quality gates
python scripts/check_quality.py src/myproject/main.py --gates python

# Check with specific gates
python scripts/check_quality.py src/myproject/main.py --gates flake8 black
```

## Example 2: Check TypeScript Files

```bash
# Check TypeScript files with TypeScript quality gates
python scripts/check_quality.py src/frontend/app.ts --gates typescript

# Specific TypeScript gates
python scripts/check_quality.py src/frontend/app.ts --gates eslint tsc
```

## Example 3: Check Multiple Files with Different Languages

```bash
# Check all files with appropriate quality gates
python scripts/check_quality.py src/backend/api.py src/frontend/app.ts --gates all
```

## Example 4: JSON Output for CI/CD Integration

```bash
# Get results in JSON format for integration with CI/CD systems
python scripts/check_quality.py src/myproject/main.py --gates python --json > quality_report.json
```

## Example 5: Using in Your Code

```python
import asyncio
from pathlib import Path
from i2c.agents.quality_team.quality_team import QualityLeadAgent

async def check_files(files_dict):
    quality_lead = QualityLeadAgent()
    
    # Run checks
    results = await quality_lead.validate_changes(
        project_path=Path.cwd(),
        modified_files=files_dict,
        quality_gates=["python"]  # Use appropriate quality gates
    )
    
    # Process results
    if results["passed"]:
        print("All checks passed!")
    else:
        print(f"Found {results['enterprise_results']['summary']['total_issues']} issues")
        
        # Show issues
        for file_path in results["enterprise_results"]["files_with_issues"]:
            print(f"Issues in {file_path}:")
            for gate, gate_result in results["enterprise_results"]["issues"][file_path].items():
                if not gate_result["passed"]:
                    print(f"  {gate} failed:")
                    for issue in gate_result["issues"]:
                        print(f"    - {issue}")
    
    return results

# Example usage
if __name__ == "__main__":
    files = {
        "my_file.py": "def hello():\n  print('world')\n"  # Black will flag indentation
    }
    
    asyncio.run(check_files(files))
```

## Example 6: Git Pre-commit Hook

Create a `.git/hooks/pre-commit` file with the following content:

```bash
#!/bin/bash

# Get a list of staged Python files
staged_files=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|js|ts|go|java)$')

if [ -n "$staged_files" ]; then
    # Run quality checks on staged files
    python scripts/check_quality.py $staged_files --gates all
    
    if [ $? -ne 0 ]; then
        echo "Quality checks failed. Please fix the issues before committing."
        exit 1
    fi
fi

exit 0
```

Make it executable with `chmod +x .git/hooks/pre-commit`.

## Quality Gates Reference

| Language   | Available Gates                     |
|------------|-------------------------------------|
| Python     | flake8, black, mypy, pytest, bandit |
| JavaScript | eslint                              |
| TypeScript | eslint, tsc                         |
| Go         | govet                               |
| Java       | checkstyle                          |