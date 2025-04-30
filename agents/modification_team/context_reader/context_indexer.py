# agents/modification_team/context_reader/context_indexer.py
import os
import hashlib
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from db_utils import (
    get_db_connection,
    get_or_create_table,
    add_or_update_chunks,
    TABLE_CODE_CONTEXT,
    SCHEMA_CODE_CONTEXT,
)
from agno.document.base import Document as AgnoDocument

# Plug-and-play chunker factory and embedding utility
from ..factory import get_chunker_for_path
from ..utils import embed_text
from ..config import load_config

# Load configuration
cfg = load_config()

# Logger setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class ContextIndexer:
    """
    Scans a codebase, uses file-type-specific chunkers,
    embeds each chunk, deduplicates, and writes to LanceDB.
    """
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config = cfg
        self.db = get_db_connection()
        # Extra verbose logging for debugging
        logger.info(f"DB connection result: {self.db is not None}")
        
        if self.db:
            self.table = get_or_create_table(
                self.db,
                TABLE_CODE_CONTEXT,
                SCHEMA_CODE_CONTEXT,
            )
            logger.info(f"Table creation result: {self.table is not None}")
        else:
            self.table = None
            logger.error("Failed to establish DB connection in ContextIndexer.__init__")
            
        self.seen_hashes = set()
        self.max_file_size = self.config.get('MAX_FILE_SIZE', 100 * 1024)
        self.skip_dirs = set(self.config.get('SKIP_DIRS', []))
        self.workers = self.config.get('WORKERS', os.cpu_count() or 4)

    def index_project(self) -> dict:
        status = {
            'files_indexed': 0,
            'files_skipped': 0,
            'chunks_indexed': 0,
            'errors': [],
        }
        if self.db is None or self.table is None:
        # if not self.db or not self.table:
            err = 'DB not initialized correctly.'
            logger.error(err)
            status['errors'].append(err)
            return status

        # Discover files, skipping configured directories
        files = [
            p for p in self.project_root.rglob('*')
            if p.is_file() and not any(part in self.skip_dirs for part in p.parts)
        ]
        logger.info(f'Found {len(files)} files to index.')

        # Parallel processing
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(self._process_file, f): f for f in files}
            for future in as_completed(futures):
                res = future.result()
                status['files_indexed'] += res.get('indexed', 0)
                status['files_skipped'] += res.get('skipped', 0)
                status['chunks_indexed'] += res.get('chunks', 0)
                status['errors'].extend(res.get('errors', []))

        logger.info(
            f"Indexing complete: {status['files_indexed']} files, "
            f"{status['chunks_indexed']} chunks, {status['files_skipped']} skipped."
        )
        return status

    def _process_file(self, file_path: Path) -> dict:
        result = {'skipped': 0, 'indexed': 0, 'chunks': 0, 'errors': []}

        # Pre-read size check
        try:
            size = file_path.stat().st_size
            if size > self.max_file_size:
                logger.warning(f"Skipping {file_path}: size {size} > {self.max_file_size}")
                result['skipped'] = 1
                return result
        except Exception as e:
            logger.error(f"Error accessing {file_path}: {e}")
            result['skipped'] = 1
            result['errors'].append(str(e))
            return result

        # Read content
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            result['skipped'] = 1
            result['errors'].append(str(e))
            return result

        # Wrap in Agno Document
        agno_doc = AgnoDocument(
            content=content,
            id=None,
            name=file_path.name,
            meta_data={'file_path': str(file_path)},
        )

        # Chunk based on file type
        chunker = get_chunker_for_path(file_path)
        try:
            docs = chunker.chunk(agno_doc)
            if not docs:
                logger.warning(f"No chunks returned for file: {file_path}")
                result['skipped'] = 1
                return result
        except Exception as e:
            err = f"Chunking failed for {file_path}: {e}"
            logger.error(err)
            result['errors'].append(err)
            return result

        records = []
        for d in docs:
            # Deduplication by content hash
            h = hashlib.sha256(d.content.encode()).hexdigest()
            if h in self.seen_hashes:
                logger.info(f"Duplicate chunk in {file_path}, skipping.")
                continue
            self.seen_hashes.add(h)

            # Embed the chunk
            try:
                vec = embed_text(d.content)
            except Exception as e:
                logger.error(f"Embedding failed for chunk {h}: {e}")
                continue

            meta = d.meta_data or {}
            record = {
                'path': str(file_path),
                'chunk_name': meta.get('chunk_name', meta.get('chunk', '')),
                'chunk_type': meta.get('chunk_type', file_path.suffix.lstrip('.')),
                'content': d.content,
                'vector': vec,
                'start_line': meta.get('start_line', -1),  # Default to -1 if missing
                'end_line': meta.get('end_line', -1),      # Default to -1 if missing
                'content_hash': h,
                'language': meta.get('language', file_path.suffix.lstrip('.')),
                # Add missing required fields with defaults
                'lint_errors': meta.get('lint_errors', []),
                'dependencies': meta.get('dependencies', []),
            }
            records.append(record)

        # Write to LanceDB
        if records:
            try:
                # Fix the parameter order to match the function definition
                add_or_update_chunks(
                    self.db,
                    TABLE_CODE_CONTEXT,
                    SCHEMA_CODE_CONTEXT,
                    'path',  # identifier_field
                    str(file_path),  # identifier_value
                    records  # chunks
                )
                result['indexed'] = 1
                result['chunks'] = len(records)
            except Exception as e:
                err = f"DB write failed for {file_path}: {e}"
                logger.error(err)
                result['errors'].append(err)
        return result