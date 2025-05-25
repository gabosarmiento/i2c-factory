# tests/unit/test_js_routing_and_indexing.py

import pytest
from pathlib import Path

from agno.document.base import Document
from i2c.agents.modification_team.chunkers.jsx_code import JSXCodeChunkingStrategy
from i2c.agents.modification_team.chunkers.js_code  import JSCodeChunkingStrategy
from i2c.agents.modification_team.chunkers.generic  import GenericTextChunkingStrategy

from i2c.agents.modification_team.context_reader.context_indexer import (
    get_js_chunks,
    ContextIndexer
)


@pytest.fixture
def pure_js_doc(tmp_path):
    p = tmp_path / "pure.js"
    p.write_text("console.log('hello world');")
    return Document(content=p.read_text(), meta_data={'file_path': str(p)})

@pytest.fixture
def mixed_jsx_doc(tmp_path):
    p = tmp_path / "mixed.js"
    # contains an embedded JSX snippet
    p.write_text("const Comp = () => <div>Hi</div>;\n")
    return Document(content=p.read_text(), meta_data={'file_path': str(p)})


def test_get_js_chunks_prefers_jsx(monkeypatch, mixed_jsx_doc):
    fake_jsx = [Document("A", {}), Document("B", {})]
    monkeypatch.setattr(JSXCodeChunkingStrategy, 'chunk', lambda self, doc: fake_jsx)
    monkeypatch.setattr(JSCodeChunkingStrategy,   'chunk', lambda self, doc: (_ for _ in ()).throw(AssertionError("JS parser called")))
    monkeypatch.setattr(GenericTextChunkingStrategy, 'chunk', lambda self, doc: (_ for _ in ()).throw(AssertionError("Generic fallback called")))

    result = get_js_chunks(mixed_jsx_doc)
    assert result is fake_jsx


def test_get_js_chunks_delegates_to_js_parser(monkeypatch, pure_js_doc):
    jsx_chunks = [Document("only", {})]
    js_chunks  = [Document("parsedJS", {})]
    monkeypatch.setattr(JSXCodeChunkingStrategy, 'chunk', lambda self, doc: jsx_chunks)
    monkeypatch.setattr(JSCodeChunkingStrategy,   'chunk', lambda self, doc: js_chunks)
    monkeypatch.setattr(GenericTextChunkingStrategy, 'chunk', lambda self, doc: (_ for _ in ()).throw(AssertionError("Generic fallback called")))

    result = get_js_chunks(pure_js_doc)
    assert result == js_chunks


def test_get_js_chunks_falls_back_to_generic_on_js_error(monkeypatch, pure_js_doc):
    monkeypatch.setattr(JSXCodeChunkingStrategy, 'chunk', lambda self, doc: [])
    def raise_js_error(self, doc):
        raise RuntimeError("boom")
    monkeypatch.setattr(JSCodeChunkingStrategy, 'chunk', raise_js_error)

    generic_chunks = [Document("GENERIC", {})]
    monkeypatch.setattr(GenericTextChunkingStrategy, 'chunk', lambda self, doc: generic_chunks)

    result = get_js_chunks(pure_js_doc)
    assert result == generic_chunks


def test_context_indexer_uses_get_js_chunks(monkeypatch, tmp_path):
    # write a small .js file
    file = tmp_path / "test.js"
    file.write_text("const X = () => <span/>;")

    # Monkeypatch get_js_chunks to observe the call
    called = {'yes': False}
    def fake_get_js_chunks(doc):
        called['yes'] = True
        return [Document("chunked-by-jsx", {})]

    monkeypatch.setattr(
        'i2c.agents.modification_team.context_reader.context_indexer.get_js_chunks',
        fake_get_js_chunks
    )

    # Instantiate ContextIndexer with project_root
    ci = ContextIndexer(tmp_path)  # <-- pass in project_root

    # Run the indexing step; it should invoke get_js_chunks internally
    chunk_props = ci.chunk_and_embed_and_get_chunk_properties(file)
    assert called['yes'], "Expected get_js_chunks to be used for .js files"

    # chunk_and_embed_and_get_chunk_properties returns a list of chunk dicts;
    # the 'content' key should match our fake Document content.
    assert any(cp['content'] == "chunked-by-jsx" for cp in chunk_props)
