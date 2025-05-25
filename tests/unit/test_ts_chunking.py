import re
import pytest
from agno.document.base import Document
from i2c.agents.modification_team.chunkers.ts_code import TSCodeChunkingStrategy

# A complex, multi-feature TypeScript snippet for thorough testing
MULTI_LINE_TS = """\
import { HttpClient } from './http';
import * as crypto from 'crypto';

// -- ADVANCED TYPES --
type Callback<T> = (data: T) => void;
interface ApiResponse<T> {
  status: number;
  payload: T;
}

// -- DECORATOR & CLASS --
function Log(target: any, prop: string, desc: PropertyDescriptor) {
  const original = desc.value;
  desc.value = function (...args: any[]) {
    console.log(`Calling ${prop} with`, args);
    return original.apply(this, args);
  };
  return desc;
}

export class SecureService<T> {
  private cache: Map<string, T> = new Map();

  constructor(private http: HttpClient) {}

  @Log
  async fetch(endpoint: string): Promise<ApiResponse<T>> {
    const res = await this.http.get(endpoint);
    const hash = crypto.createHash('sha256').update(endpoint).digest('hex');
    this.cache.set(hash, res.data);
    return { status: 200, payload: res.data };
  }

  getFromCache(key: string): T | undefined {
    return this.cache.get(key);
  }
}

// -- NESTED STRUCTURES & GENERICS --
export function buildTree<T>(nodes: T[], idFn: (n: T) => string): Record<string, T[]> {
  const tree: Record<string, T[]> = {};
  for (const node of nodes) {
    const id = idFn(node);
    if (!tree[id]) tree[id] = [];
    tree[id].push(node);
  }
  return tree;
}

// -- MULTILINE STRINGS & TEMPLATES --
export const render = (username: string): string => {
  return `
    <div>
      <h1>Welcome, ${username}!</h1>
      <p>Enjoy your session.</p>
    </div>
  `;
};
"""

@pytest.fixture
def ts_code(tmp_path):
    p = tmp_path / "complex.ts"
    p.write_text(MULTI_LINE_TS)
    return p.read_text()

@pytest.fixture
def chunks_and_strat(ts_code):
    strat = TSCodeChunkingStrategy()  # max_content_length pulled from MAX_TS_CHUNK_CONTENT env
    doc = Document(content=ts_code, meta_data={})
    return strat.chunk(doc), strat

def test_reconstructs_original_code(chunks_and_strat, ts_code):
    chunks, _ = chunks_and_strat
    reconstructed = "".join(ch.content for ch in chunks).strip()
    assert reconstructed == ts_code.strip(), "Reconstructed code does not match the original."

def test_chunk_size_limits(chunks_and_strat):
    chunks, strat = chunks_and_strat
    limit = strat.max_content_length
    for i, ch in enumerate(chunks):
        assert len(ch.content) <= limit, f"Chunk {i} exceeds max size: {len(ch.content)} > {limit}"

def test_balanced_curly_braces(chunks_and_strat):
    chunks, _ = chunks_and_strat
    for i, ch in enumerate(chunks):
        open_braces = ch.content.count("{")
        close_braces = ch.content.count("}")
        assert open_braces >= close_braces, (
            f"Chunk {i} may end mid-block: {open_braces} '{{' vs {close_braces} '}}'"
        )

def test_preserves_multiline_template_literals(chunks_and_strat):
    chunks, _ = chunks_and_strat
    for ch in chunks:
        if "`" in ch.content:
            assert ch.content.count("`") % 2 == 0, "Unbalanced template literal backticks"

def test_no_chunk_ends_with_split_declaration(chunks_and_strat):
    chunks, _ = chunks_and_strat
    pattern = re.compile(r"^\s*(export\s+)?(function|class|type|interface|const|let)\b.*[^;{]$")
    for i, ch in enumerate(chunks[:-1]):
        last_line = ch.content.rstrip().splitlines()[-1]
        assert not pattern.match(last_line), f"Chunk {i} ends with incomplete declaration: '{last_line}'"

def test_first_chunk_starts_correctly(chunks_and_strat):
    chunks, _ = chunks_and_strat
    assert re.match(r"^(import|export|type|interface|class|const|let|var)", chunks[0].content.lstrip()), \
        "First chunk doesn't start with a valid TS construct"

def test_last_chunk_ends_correctly(chunks_and_strat):
    chunks, _ = chunks_and_strat
    last = chunks[-1].content.rstrip()
    assert last.endswith("}") or last.endswith(";") or last.endswith("`"), \
        f"Last chunk ends abruptly: '{last[-50:]}'"

def test_empty_file_yields_single_empty_chunk():
    strat = TSCodeChunkingStrategy()
    doc = Document(content="", meta_data={})
    chunks = strat.chunk(doc)
    assert len(chunks) == 1, "Empty file should produce exactly one chunk"
    assert chunks[0].content == "", "Chunk from empty file should have empty content"

def test_fallback_on_oversized_file():
    # Force a very small max to trigger fallback
    small_limit = 5
    strat = TSCodeChunkingStrategy(max_content_length=small_limit)
    content = "abcdef"  # length 6 > 5
    doc = Document(content=content, meta_data={})
    chunks = strat.chunk(doc)
    assert len(chunks) == 1, "Oversized file should not be split"
    assert chunks[0].content == content, "Fallback chunk should equal original content"
