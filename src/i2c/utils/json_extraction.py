import json

def extract_json(content: str) -> dict:
    """
    Extract and parse the first valid JSON object from a string.
    Uses bracket counting to handle nested braces.
    """
    brace_count = 0
    start_idx = None

    for idx, char in enumerate(content):
        if char == '{':
            if brace_count == 0:
                start_idx = idx
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx is not None:
                json_candidate = content[start_idx:idx+1]
                try:
                    return json.loads(json_candidate)
                except json.JSONDecodeError:
                    continue

    raise ValueError(f"Content is a string but no valid JSON found: {content}")


def extract_json_with_fallback(content: str, fallback: dict | None = None) -> dict:
    """
    Try to extract JSON. If it fails, return fallback if provided.
    """
    try:
        return extract_json(content)
    except Exception as e:
        from i2c.cli.controller import canvas  # only if canvas is available
        if 'canvas' in globals():
            canvas.warning(f"Fallback used due to JSON extraction error: {e}")
        if fallback:
            return fallback
        raise
