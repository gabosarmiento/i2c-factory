import json
import pytest

# Dummy class with your helpers; replace with your actual ModifierAdapter import!
class ModifierAdapter:
    def _parse_agent_response(self, raw_reply, rel_path, original_content):
        import re
        if not raw_reply:
            return None
        try:
            data = json.loads(raw_reply)
            if isinstance(data, dict) and "modified" in data:
                return {"file_path": data.get("file_path", rel_path), "modified": data["modified"]}
        except Exception:
            pass
        if "FILE:" in raw_reply:
            lines = raw_reply.strip().split("\n")
            for i, line in enumerate(lines):
                if line.startswith("FILE:"):
                    file_path = line[5:].strip()
                    if i+2 < len(lines):
                        modified_src = "\n".join(lines[i+2:])
                        return {"file_path": file_path, "modified": modified_src}
        code_block_pattern = r"```(?:python)?(.*?)```"
        matches = re.findall(code_block_pattern, raw_reply, re.DOTALL)
        if matches:
            largest_block = max(matches, key=len).strip()
            if len(largest_block) > 5:
                return {"file_path": rel_path, "modified": largest_block}
        return None

    def _apply_specific_file_fixes(self, file_path, original_content, modified_content, what, how):
        import re
        result = modified_content
        # Remove duplicate unittest.main()
        if file_path.startswith("test_") and "unittest.main()" in result:
            lines = result.splitlines()
            main_indices = [i for i, line in enumerate(lines) if "unittest.main()" in line]
            for idx in main_indices[:-1]:
                lines[idx] = "#     unittest.main() # Removed duplicate"
            result = "\n".join(lines)
        # Remove unknown.py
        result = "\n".join([line for line in result.splitlines() if "unknown.py" not in line])
        # If still empty, use original with TODO
        if not result.strip() and original_content.strip():
            result = original_content + f"\n\n# TODO: Implement {what}\n# {how}\n"
        return result

@pytest.fixture
def adapter():
    return ModifierAdapter()

def test_parse_json_response(adapter):
    response = '{"file_path": "foo.py", "modified": "print(1)"}'
    result = adapter._parse_agent_response(response, "foo.py", "")
    assert result["file_path"] == "foo.py"
    assert "print(1)" in result["modified"]

def test_parse_file_prefix_response(adapter):
    response = "FILE: foo.py\n\nprint(2)\n"
    result = adapter._parse_agent_response(response, "foo.py", "")
    assert result["file_path"] == "foo.py"
    assert "print(2)" in result["modified"]

def test_parse_markdown_code_block(adapter):
    response = "```python\nprint(3)\n```"
    result = adapter._parse_agent_response(response, "foo.py", "")
    assert "print(3)" in result["modified"]

def test_parse_empty_response(adapter):
    result = adapter._parse_agent_response("", "foo.py", "")
    assert result is None

def test_fix_duplicate_unittest_main(adapter):
    file_path = "test_sample.py"
    content = (
        "import unittest\n"
        "def foo(): pass\n"
        "unittest.main()\n"
        "unittest.main()\n"
    )
    fixed = adapter._apply_specific_file_fixes(file_path, content, content, "anything", "anything")
    # Only one real unittest.main() should remain (one is commented)
    assert fixed.count("unittest.main()") == 2  # 1 real, 1 commented
    assert fixed.count("# Removed duplicate") == 1

def test_fix_removes_unknown_py(adapter):
    original = "# unknown.py\nprint('hello')"
    fixed = adapter._apply_specific_file_fixes("foo.py", original, original, "what", "how")
    assert "unknown.py" not in fixed

def test_fix_empty_content_returns_original_with_todo(adapter):
    original = "print('keep me!')"
    fixed = adapter._apply_specific_file_fixes("foo.py", original, "", "do something", "by magic")
    assert "keep me!" in fixed
    assert "TODO" in fixed

