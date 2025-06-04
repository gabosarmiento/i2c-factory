# utils/markdown.py

def strip_markdown_code_block(text: str) -> str:
    """
    Removes Markdown-style code fences (``` or ```lang) from the beginning and/or end.
    Works across all languages (e.g., python, js, jsx, go).
    Does NOT touch embedded backticks in code or comments.
    """
    text = text.strip()
    lines = text.splitlines()

    # Remove leading ``` or ```<lang>
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]

    # Remove trailing ```
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines)