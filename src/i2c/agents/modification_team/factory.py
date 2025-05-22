from pathlib import Path
from agno.embedder.sentence_transformer import SentenceTransformerEmbedder
from .context_utils import EMBEDDING_MODEL_NAME
from i2c.llm_providers import llm_ligthweight

# Instantiate embedder
sentence_embedder = SentenceTransformerEmbedder(EMBEDDING_MODEL_NAME)

# Chunkers (language-specific and general)
from .chunkers.python_code import PythonCodeChunkingStrategy
from .chunkers.java_code import JavaCodeChunkingStrategy
from .chunkers.js_code import JSCodeChunkingStrategy
from .chunkers.ts_code import TSCodeChunkingStrategy
from .chunkers.html_code import HTMLCodeChunkingStrategy
from .chunkers.generic import GenericTextChunkingStrategy
from .chunkers.go_code import GoCodeChunkingStrategy
from .chunkers.ast_chunker import ASTChunker
from .chunkers.css_code import CSSCodeChunkingStrategy
from .chunkers.markdown_code import MarkdownChunkingStrategy
from .chunkers.shell_script import ShellScriptChunkingStrategy

from agno.document.chunking.fixed import FixedSizeChunking
from agno.document.chunking.recursive import RecursiveChunking
from agno.document.chunking.semantic import SemanticChunking
from agno.document.chunking.agentic import AgenticChunking

# ✅ Reference only — NOT used for instantiation
_EXTENSION_MAP = {
    '.py':   'ASTChunker',
    '.java': 'JavaCodeChunkingStrategy',
    '.ts':   'TSCodeChunkingStrategy',
    '.tsx':  'TSCodeChunkingStrategy',
    '.js':   'JSCodeChunkingStrategy',
    '.html': 'HTMLCodeChunkingStrategy',
    '.htm':  'HTMLCodeChunkingStrategy',
    '.go':   'GoCodeChunkingStrategy',
    '.css':  'CSSCodeChunkingStrategy',
    '.sh':   'ShellScriptChunkingStrategy',
    '.md':   'MarkdownChunkingStrategy',
    '.markdown': 'RecursiveChunking',
    '.json': 'FixedSizeChunking',
    '.yaml': 'FixedSizeChunking',
    '.yml':  'FixedSizeChunking',
    '.toml': 'FixedSizeChunking',
    '.ini':  'FixedSizeChunking',
    '.txt':  'SemanticChunking',
    '.pdf':  'AgenticChunking',
}

# Pre-instantiated chunkers (custom args or models)
_PRECONFIGURED_CHUNKERS = {
    '.txt': SemanticChunking(
        embedder=sentence_embedder,
        chunk_size=1000,
        similarity_threshold=0.6,
    ),
    '.pdf': AgenticChunking(
        model=llm_ligthweight,
        max_chunk_size=800,
    ),
    '.markdown': RecursiveChunking(chunk_size=2000, overlap=100),
    '.json': FixedSizeChunking(chunk_size=2000, overlap=200),
    '.yaml': FixedSizeChunking(chunk_size=2000, overlap=200),
    '.yml': FixedSizeChunking(chunk_size=2000, overlap=200),
    '.toml': FixedSizeChunking(chunk_size=2000, overlap=200),
    '.ini': FixedSizeChunking(chunk_size=2000, overlap=200),
}

# Class-based chunkers (safe to instantiate)
_CLASS_BASED_CHUNKERS = {
    '.ts': TSCodeChunkingStrategy,
    '.tsx': TSCodeChunkingStrategy,
    '.js': JSCodeChunkingStrategy,
    '.html': HTMLCodeChunkingStrategy,
    '.htm': HTMLCodeChunkingStrategy,
    '.go': GoCodeChunkingStrategy,
    '.java': JavaCodeChunkingStrategy,
    '.css': CSSCodeChunkingStrategy,
    '.md': MarkdownChunkingStrategy,
    '.sh': ShellScriptChunkingStrategy,
}

def get_chunker_for_path(path: Path):
    """
    Returns a ready-to-use chunker instance for a given file path.
    """
    ext = path.suffix.lower()

    if ext == '.py':
        return ASTChunker()

    if ext in _PRECONFIGURED_CHUNKERS:
        return _PRECONFIGURED_CHUNKERS[ext]

    chunker_cls = _CLASS_BASED_CHUNKERS.get(ext, GenericTextChunkingStrategy)
    try:
        return chunker_cls()
    except Exception as e:
        from i2c.cli.controller import canvas
        canvas.warning(f"Failed to instantiate {chunker_cls.__name__}: {e}")
        return GenericTextChunkingStrategy()

# ✅ Only expose the callable and the map (for reference/debug)
__all__ = ['get_chunker_for_path', '_EXTENSION_MAP']
