from pathlib import Path

# Import your language-specific and generic chunkers
from .chunkers.python_code import PythonCodeChunkingStrategy
from .chunkers.java_code import JavaCodeChunkingStrategy
from .chunkers.js_code import JSCodeChunkingStrategy
from .chunkers.ts_code import TSCodeChunkingStrategy
from .chunkers.html_code import HTMLCodeChunkingStrategy
from .chunkers.generic import GenericTextChunkingStrategy
from .chunkers.go_code import GoCodeChunkingStrategy

# Map file extensions to chunker classes
_EXTENSION_MAP = {
    '.py': PythonCodeChunkingStrategy,
    '.java': JavaCodeChunkingStrategy,
    '.ts': TSCodeChunkingStrategy,
    '.tsx': TSCodeChunkingStrategy,
    '.js': JSCodeChunkingStrategy,
    '.html': HTMLCodeChunkingStrategy,
    '.htm': HTMLCodeChunkingStrategy,
    '.go': GoCodeChunkingStrategy,
}

def get_chunker_for_path(path: Path):
    """
    Return an instance of the appropriate chunker based on file extension.
    Falls back to a generic text-based chunker.
    """
    chunker_cls = _EXTENSION_MAP.get(path.suffix, GenericTextChunkingStrategy)
    return chunker_cls()