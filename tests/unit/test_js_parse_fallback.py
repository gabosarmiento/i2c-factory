import pytest
from agno.document.base import Document
from i2c.agents.modification_team.chunkers.js_code import JSCodeChunkingStrategy
from i2c.agents.modification_team.chunkers.jsx_code import JSXCodeChunkingStrategy

class DummyJSX(JSXCodeChunkingStrategy):
    def chunk(self, document):
        # we just want to see that we got routed here
        return [Document(content="<<JSX CHUNK>>", meta_data={'chunk_type': 'jsx_file'})]

@pytest.fixture(autouse=True)
def patch_jsx(monkeypatch):
    # whenever the JSCodeChunker does JSXCodeChunkingStrategy(),
    # return our dummy
    monkeypatch.setattr(
        'i2c.agents.modification_team.chunkers.js_code.JSXCodeChunkingStrategy',
        lambda: DummyJSX()
    )

def test_esprima_parse_error_routes_to_jsx(monkeypatch):
    # make esprima.parseScript always throw
    import i2c.agents.modification_team.chunkers.js_code as js_mod
    monkeypatch.setattr(js_mod.esprima, 'parseScript',
                        lambda *args, **kwargs: (_ for _ in ()).throw(Exception("boom")))

    doc = Document(
        content="const X = () => <div/>;", 
        meta_data={'file_path': 'file.js'}
    )
    chunks = JSCodeChunkingStrategy().chunk(doc)

    # should be exactly our dummy JSX chunk
    assert len(chunks) == 1
    assert chunks[0].content == "<<JSX CHUNK>>"
    assert chunks[0].meta_data['chunk_type'] == 'jsx_file'

def test_esprima_no_chunks_routes_to_jsx(monkeypatch):
    # simulate esprima.parseScript giving a tree with an empty body
    class FakeTree: body = []
    import i2c.agents.modification_team.chunkers.js_code as js_mod
    monkeypatch.setattr(js_mod.esprima, 'parseScript',
                        lambda *args, **kwargs: FakeTree())

    doc = Document(
        content="// just comments or something", 
        meta_data={'file_path': 'file.js'}
    )
    chunks = JSCodeChunkingStrategy().chunk(doc)

    assert len(chunks) == 1
    assert chunks[0].content == "<<JSX CHUNK>>"
    assert chunks[0].meta_data['chunk_type'] == 'jsx_file'
