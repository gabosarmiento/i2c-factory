# tests/utils/snippet_utils.py
import ast
from pathlib import Path

def extract_function_snippet(file_path: Path, func_name: str):
    """
    Extract the source code and AST node for a function named `func_name` from the given file.

    Args:
        file_path: Path to the .py file.
        func_name: Name of the function to extract.

    Returns:
        A tuple of (function_source: str, function_ast_node: ast.FunctionDef).
    """
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            func_src = ast.get_source_segment(source, node)
            return func_src, node
    raise ValueError(f"Function '{func_name}' not found in {file_path}")

def splice_back(file_path: Path, func_node: ast.FunctionDef, new_func_src: str):
    """
    Replace the old function code in `file_path` with `new_func_src`.

    Args:
        file_path: Path to the .py file.
        func_node: AST node of the original function (provides lineno/end_lineno).
        new_func_src: The new source code for the function, including signature and body.
    """
    original_lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
    # AST nodes use 1-based line numbers
    start = func_node.lineno - 1
    end = func_node.end_lineno
    # Prepare new function lines with proper line endings
    new_lines = new_func_src.splitlines(keepends=True)
    # Splice the new function in place of the old
    updated = original_lines[:start] + new_lines + original_lines[end:]
    file_path.write_text("".join(updated), encoding="utf-8")
