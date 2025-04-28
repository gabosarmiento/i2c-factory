# /agents/modification_team/context_reader/context_indexer.py
# Contains the core logic for indexing project context into LanceDB.

from pathlib import Path
from typing import Any

# Import DB utilities
try:
    from ....db_utils import get_db_connection, get_or_create_table, add_or_update_chunks
except ImportError:
    from db_utils import get_db_connection, get_or_create_table, add_or_update_chunks

# Import context utilities
try:
    from ..context_utils import extract_python_chunks, generate_embedding
except ImportError:
    from agents.modification_team.context_utils import extract_python_chunks, generate_embedding

# Import Static Analysis Tools
try:
    from ..static_analysis_tools import run_ruff_checks, extract_imports
except ImportError:
    from agents.modification_team.static_analysis_tools import run_ruff_checks, extract_imports

# Import CLI for logging
try:
    from cli.controller import canvas
except ImportError:
    class FallbackCanvas: # Basic fallback logger
        def warning(self, msg): print(f"[WARN_IDX] {msg}")
        def error(self, msg): print(f"[ERROR_IDX] {msg}")
        def info(self, msg): print(f"[INFO_IDX] {msg}")
        def success(self, msg): print(f"[SUCCESS_IDX] {msg}")
    canvas = FallbackCanvas()

# Constants
MAX_FILE_SIZE_READ = 100 * 1024
MAX_FILES_TO_INDEX = 500

def index_project_context(project_path: Path, embedding_model: Any) -> dict:
    """
    Reads, chunks, analyzes (static), embeds, and indexes project files.
    """
    canvas.info(f"🤖 [ContextIndexer] Indexing context from: {project_path}")
    status = {
        "project_path": str(project_path), "files_indexed": 0,
        "files_skipped": 0, "chunks_indexed": 0, "errors": []
    }
    if not embedding_model:
        status["errors"].append("Embedding model not available."); return status
    if not project_path.is_dir():
        status["errors"].append("Project path invalid."); return status

    db = None
    table = None
    try:
        # --- <<< Get DB connection and table within this function's scope >>> ---
        canvas.info("   [DB] Establishing connection for indexing...")
        db = get_db_connection()
        if not db: raise ConnectionError("DB connection failed.")
        table = get_or_create_table(db)
        if table is None: raise ConnectionError("DB table acquisition failed.")
        canvas.info("   [DB] Connection and table ready for indexing.")
        # --- <<< End DB Handle Acquisition >>> ---

        all_files = list(project_path.rglob('*'))
        files_processed_count = 0
        total_chunks_indexed = 0
        canvas.info(f"   [DB] Found {len(all_files)} paths. Processing...")

        for file_path in all_files:
            # ... (Skipping logic remains the same) ...
            relative_path_parts = file_path.relative_to(project_path).parts
            if any(part.startswith('.') for part in relative_path_parts) or \
               any(ex in relative_path_parts for ex in ["__pycache__", "node_modules", ".git"]):
                continue

            if file_path.is_file():
                files_processed_count += 1
                relative_path = str(file_path.relative_to(project_path))
                canvas.info(f"   -> Processing: {relative_path}")
                processed_successfully = False
                file_chunks_to_add = []

                try:
                    fsize = file_path.stat().st_size
                    if fsize == 0 or fsize > MAX_FILE_SIZE_READ:
                        canvas.info(f"      ⚪ Skipping empty or large file ({fsize} bytes).")
                        status["files_skipped"] += 1; continue

                    content = file_path.read_text(encoding='utf-8', errors='ignore')

                    # Extract chunks
                    extracted_chunks = []
                    is_python_file = file_path.suffix == '.py'
                    if is_python_file:
                        extracted_chunks = extract_python_chunks(file_path, content)
                    else:
                        extracted_chunks.append({"name": file_path.name, "type": "file", "code": content})

                    # Generate embeddings and prepare data
                    embedding_failed_for_file = False
                    for chunk in extracted_chunks:
                        chunk_content = chunk.get("code")
                        if not chunk_content: continue

                        # Run Static Analysis
                        lint_errors = []
                        dependencies = []
                        if is_python_file and chunk.get("type") != "file":
                            analysis_id = f"{relative_path}::{chunk.get('name')}"
                            ruff_results = run_ruff_checks(chunk_content, analysis_id)
                            lint_errors = ruff_results.get("lint_errors", [])
                            dependencies = extract_imports(chunk_content, analysis_id)
                        elif is_python_file and chunk.get("type") == "file":
                             analysis_id = f"{relative_path} (whole file)"
                             ruff_results = run_ruff_checks(chunk_content, analysis_id)
                             lint_errors = ruff_results.get("lint_errors", [])
                             dependencies = extract_imports(chunk_content, analysis_id)

                        # Generate embedding
                        vector = generate_embedding(chunk_content) # Uses pre-loaded model

                        if vector:
                            file_chunks_to_add.append({
                                "path": relative_path,
                                "chunk_name": chunk.get("name", "N/A"),
                                "chunk_type": chunk.get("type", "file"),
                                "content": chunk_content, "vector": vector,
                                "lint_errors": lint_errors, "dependencies": dependencies,
                            })
                        else:
                            status["errors"].append(f"Embedding failed for chunk '{chunk.get('name')}' in {relative_path}")
                            embedding_failed_for_file = True

                    # Add/Update chunks for this file
                    if file_chunks_to_add and not embedding_failed_for_file:
                        add_or_update_chunks(table, relative_path, file_chunks_to_add)
                        total_chunks_indexed += len(file_chunks_to_add)
                        processed_successfully = True
                    elif embedding_failed_for_file:
                         canvas.warning(f"      ⚠️ Skipping DB add for {relative_path} due to embedding errors.")
                         status["files_skipped"] += 1
                    else:
                         canvas.warning(f"      ⚪ No valid chunks/embeddings generated for {relative_path}. Skipping.")
                         status["files_skipped"] += 1

                except Exception as e:
                    error_msg = f"Error processing file {relative_path}: {e}"
                    canvas.error(f"      ❌ {error_msg}")
                    status["errors"].append(error_msg)
                    status["files_skipped"] += 1

                if processed_successfully: status["files_indexed"] += 1

        status["chunks_indexed"] = total_chunks_indexed
        canvas.success(f"✅ [ContextIndexer] Indexing finished. Processed: {files_processed_count} files, Indexed: {status['files_indexed']} files ({status['chunks_indexed']} chunks), Skipped: {status['files_skipped']}.")

    except Exception as e:
        error_msg = f"General error during project indexing: {e}"
        canvas.error(f"   ❌ {error_msg}")
        status["errors"].append(error_msg)
    finally:
        # Attempt to close connection if it was opened
        # Note: LanceDB connection object itself might not have a close method,
        # depends on the underlying implementation. This is a best-effort.
        # if db and hasattr(db, 'close'):
        #     try:
        #         # db.close() # LanceDB connection doesn't typically need explicit close
        #         canvas.info("   [DB] Indexing connection closed (implicitly).")
        #     except Exception as close_e:
        #          canvas.warning(f"   [DB] Error closing indexing connection: {close_e}")
        pass # LanceDB connection usually managed automatically

    return status

