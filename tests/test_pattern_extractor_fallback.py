# test_pattern_extractor_fallback.py
from i2c.bootstrap import initialize_environment
initialize_environment()
from i2c.agents.knowledge.pattern_extractor import PatternExtractorAgent

# Simulated borderline LLM responses
borderline_responses = [
    # Case 1: Markdown-wrapped JSON
    """```json
    {
      "imports": ["import fastapi", "from pydantic import BaseModel"],
      "file_structure": ["main.py", "api/routes.py"],
      "conventions": ["snake_case for variables"],
      "architecture": ["layered architecture"],
      "examples": ["example code here"]
    }
    ```""",

    # Case 2: Trailing comma
    """{
      "imports": ["import fastapi",],
      "file_structure": ["main.py"],
      "conventions": [],
      "architecture": [],
      "examples": []
    }""",

    # Case 3: Explanation + JSON
    """Sure! Here's what I extracted:
    {
      "imports": ["import numpy as np"],
      "file_structure": ["notebooks/data_analysis.ipynb"],
      "conventions": ["camelCase for functions"],
      "architecture": [],
      "examples": ["np.array([1,2,3])"]
    }""",

    # Case 4: Missing closing brace
    """{
      "imports": ["import pandas as pd"],
      "file_structure": [],
      "conventions": [],
      "architecture": [],
      "examples": []
    """,

    # Case 5: Plain string
    "No patterns detected in documentation."
]

def test_pattern_extraction_from_edge_cases():
    agent = PatternExtractorAgent()

    for idx, raw_content in enumerate(borderline_responses, start=1):
        print(f"\n--- Test Case {idx} ---")
        result = agent.extract_actionable_patterns(raw_content)

        print("✅ Result keys:", list(result.keys()))
        for key, val in result.items():
            print(f"  {key}: {val}")

if __name__ == "__main__":
    test_pattern_extraction_from_edge_cases()
