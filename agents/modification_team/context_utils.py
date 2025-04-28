# /agents/modification_team/context_utils.py
# Utility functions for the ContextReaderAgent: chunking and embedding.

import ast
from pathlib import Path
import os # Import os for environment variables if needed later

# --- Type Hinting and Conditional Import for SentenceTransformer ---
# Allows type hinting without runtime error if library is missing
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    # This block is only processed by type checkers
    from sentence_transformers import SentenceTransformer
else:
    # This block is processed at runtime
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        # Set SentenceTransformer to None if the library isn't installed
        SentenceTransformer = None
        print("❌ Error: sentence-transformers library not found. Please install: pip install sentence-transformers")
# --- End Import Handling ---

# Import CLI controller for logging
try:
    from cli.controller import canvas
except ImportError:
    # Basic fallback logger if canvas isn't available
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_UTIL] {msg}")
        def error(self, msg): print(f"[ERROR_UTIL] {msg}")
        def info(self, msg): print(f"[INFO_UTIL] {msg}")
    canvas = FallbackCanvas()

# Embedding model name - Ensure this matches the vector dimension in db_utils.SCHEMA
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'

# --- Load Embedding Model Once at Module Level ---
_embedding_model: Optional['SentenceTransformer'] = None # Use forward reference string for type hint if needed, or Optional[SentenceTransformer] if import worked
if SentenceTransformer:
    try:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        canvas.info(f"[ContextUtils] Loaded embedding model '{EMBEDDING_MODEL_NAME}' successfully.")
    except Exception as e:
        _embedding_model = None # Ensure it's None on failure
        canvas.warning(f"[ContextUtils] Failed to load embedding model '{EMBEDDING_MODEL_NAME}': {e}")
else:
    canvas.warning("[ContextUtils] Skipping embedding model loading: sentence-transformers not installed.")
# --- End Model Loading ---


# --- Embedding Generation ---
# Updated function signature - no longer needs embedding_model passed in
def generate_embedding(text: str) -> Optional[List[float]]:
    """Generates a vector embedding for the given text using the pre-loaded model."""
    # Use the globally loaded model instance
    if _embedding_model and text:
        try:
            embedding = _embedding_model.encode(text, convert_to_numpy=False)
            # Ensure result is a list of floats
            return [float(x) for x in embedding]
        except Exception as e:
            print(f"      ❌ Error generating embedding: {e}")
            return None
    elif not _embedding_model:
         print("      ⚠️ Cannot generate embedding: Model not loaded or failed to load.")
    elif not text:
         print("      ⚠️ Cannot generate embedding: Input text is empty.")
    return None

# --- Python Code Chunking ---
def extract_python_chunks(file_path: Path, code_content: str) -> list[dict]:
    """Parses Python code using AST to extract functions and classes."""
    chunks = []
    try:
        tree = ast.parse(code_content, filename=str(file_path))
        for node in ast.walk(tree):
            chunk_type = None
            chunk_name = None
            node_code = None

            if isinstance(node, ast.FunctionDef):
                chunk_type = "function"
                chunk_name = node.name
            elif isinstance(node, ast.ClassDef):
                chunk_type = "class"
                chunk_name = node.name

            if chunk_type and chunk_name:
                try:
                    # Get the source code segment for the node
                    node_code = ast.get_source_segment(code_content, node, padded=True)
                    if node_code:
                        chunks.append({
                            "name": chunk_name,
                            "type": chunk_type,
                            "code": node_code.strip()
                        })
                except Exception as seg_e:
                     # Use canvas for logging if available
                     canvas.warning(f"      ⚠️ Warning: Could not get source segment for {chunk_type} '{chunk_name}' in {file_path.name}: {seg_e}")

    except SyntaxError as e:
        canvas.warning(f"   ⚠️ Skipping AST parsing for {file_path.name} due to SyntaxError: {e}")
    except Exception as e:
        canvas.warning(f"   ⚠️ Error during AST parsing for {file_path.name}: {e}")

    # If no functions/classes found, or if parsing failed, index the whole file
    if not chunks and code_content:
         canvas.info(f"      No functions/classes found/parsed in {file_path.name}. Indexing whole file.")
         chunks.append({"name": file_path.stem, "type": "file", "code": code_content})

    return chunks
