
import os
from functools import lru_cache

try:
    import yaml
except ImportError:
    yaml = None

@lru_cache()
def load_config(path: str = 'config.yaml') -> dict:
    """
    Load configuration from a YAML file or fall back to environment variables.
    """
    # Default settings
    defaults = {
        'EMBEDDING_MODEL': os.getenv('EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2'),
        'MAX_FILE_SIZE': int(os.getenv('MAX_FILE_SIZE_READ', '102400')),
        'WORKERS': int(os.getenv('CONTEXT_INDEXER_WORKERS', str(os.cpu_count() or 4))),
        'SKIP_DIRS': os.getenv('SKIP_DIRS', '.git,__pycache__,.venv,node_modules').split(','),
    }

    if yaml and os.path.exists(path):
        with open(path, 'r') as f:
            data = yaml.safe_load(f) or {}
        # Merge defaults with YAML overrides
        return {**defaults, **data}

    return defaults
