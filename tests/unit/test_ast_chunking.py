import hashlib
import textwrap
import pytest
from agno.document.base import Document
from i2c.agents.modification_team.chunkers.ast_chunker import ASTChunkingStrategy, SimpleLineChunker

def test_basic_ast_splitting():
    source = textwrap.dedent("""\
        import math
        from os import path as ospath

        X = 5
        Y: int = 10

        def foo(a, b):
            return a + b

        async def bar(c):
            return await foo(c, c)

        class MyClass:
            def method(self):
                pass

        print('done')
    """)
    doc = Document(content=source, meta_data={'file_path': 'module.py'})
    chunks = ASTChunkingStrategy().chunk(doc)

    # We should get exactly 8 chunks
    assert len(chunks) == 8
    types = [c.meta_data['chunk_type'] for c in chunks]
    assert types == [
        'import', 'import', 'assignment', 'assignment',
        'function', 'async_function', 'class', 'other'
    ]

    names = [c.meta_data['chunk_name'] for c in chunks]
    assert names[:4] == ['math', 'ospath', 'X', 'Y']
    assert 'foo' in names and 'bar' in names and 'MyClass' in names and 'Expr' in names

    # Check snippet contents
    assert "def foo" in chunks[4].content
    assert "async def bar" in chunks[5].content
    assert chunks[6].content.strip().startswith("class MyClass")
    assert "print('done')" in chunks[7].content

def test_empty_init_module_fallback():
    doc = Document(content="", meta_data={'file_path': 'pkg/__init__.py'})
    chunks = ASTChunkingStrategy().chunk(doc)

    # Empty __init__.py should yield exactly one module_init chunk
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.content == ""
    assert chunk.meta_data['chunk_type'] == 'module_init'
    assert chunk.meta_data['chunk_name'] == '__init__'

def test_empty_non_init_returns_no_chunks():
    doc = Document(content="", meta_data={'file_path': 'other.py'})
    chunks = ASTChunkingStrategy().chunk(doc)

    # No AST nodes, not __init__.py, and SimpleLineChunker on empty yields no chunks
    assert chunks == []

def test_syntax_error_fallback_to_line_chunker():
    bad = "def broken(:\n    pass"
    doc = Document(content=bad, meta_data={'file_path': 'bad.py'})
    chunks = ASTChunkingStrategy().chunk(doc)

    # Should fall back to SimpleLineChunker
    expected = SimpleLineChunker().chunk(doc)
    assert chunks == expected

def test_type_comments_and_numeric_underscore():
    src = "x = 1  # type: int\ny = 1_000\n"
    doc = Document(content=src, meta_data={'file_path': 'test.py'})
    chunks = ASTChunkingStrategy().chunk(doc)

    # Two assignments
    assert len(chunks) == 2
    # First assignment still includes the comment
    assert chunks[0].meta_data['chunk_type'] == 'assignment'
    assert '# type: int' in chunks[0].content
    # Numeric underscore is preserved
    assert chunks[1].meta_data['chunk_name'] == 'y'
    assert '1_000' in chunks[1].content

def test_expr_chunk_for_print():
    src = "print('hello')\n"
    doc = Document(content=src, meta_data={'file_path': 'expr.py'})
    chunks = ASTChunkingStrategy().chunk(doc)

    # A bare expression at top level becomes an 'other' chunk named 'Expr'
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.meta_data['chunk_type'] == 'other'
    assert chunk.meta_data['chunk_name'] == 'Expr'
    assert "print('hello')" in chunk.content
    
def test_empty_init_module_fallback():
    doc = Document(content="", meta_data={"file_path":"pkg/__init__.py"})
    chunks = ASTChunkingStrategy().chunk(doc)
    assert len(chunks) == 1
    assert chunks[0].meta_data["chunk_type"] == "init_file"

def test_empty_non_init_returns_no_chunks():
    doc = Document(content="", meta_data={"file_path":"other.py"})
    assert ASTChunkingStrategy().chunk(doc) == []

