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
config = load_config()

# Logger setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class ContextIndexer:
    """
    Scans a codebase, chunks files, embeds each chunk,
    deduplicates, and writes to LanceDB.
    """
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config = config

        # Connect to LanceDB and open/create table
        self.db = get_db_connection()
        logger.info(f"DB connection object: {self.db}")

        if self.db:
            try:
                # Ensure storage directory exists
                db_uri = getattr(self.db, 'uri', None)
                if db_uri:
                    Path(db_uri).parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

            # Open or create the embeddings table
            self.table = get_or_create_table(
                self.db,
                TABLE_CODE_CONTEXT,
                SCHEMA_CODE_CONTEXT,
            )
            if self.table:
                logger.info(f"RAG table ready: {TABLE_CODE_CONTEXT}")
            else:
                logger.warning(f"Table '{TABLE_CODE_CONTEXT}' unavailable; indexing may fail.")
        else:
            logger.error("No DB connection: disabling RAG indexer.")
            self.table = None

        # State for indexing
        self.seen_hashes = set()
        self.max_file_size = self.config.get('MAX_FILE_SIZE', 100 * 1024)
        self.skip_dirs = set(self.config.get('SKIP_DIRS', []))
        self.workers = self.config.get('WORKERS', os.cpu_count() or 4)

    def index_project(self) -> dict:
        status = {'files_indexed': 0, 'files_skipped': 0, 'chunks_indexed': 0, 'errors': []}

        # Ensure DB and table are available
        if not self.db:
            err = 'DB not initialized.'
            logger.error(err)
            status['errors'].append(err)
            return status
        if not self.table:
            # Try once more to open/create the table
            self.table = get_or_create_table(
                self.db,
                TABLE_CODE_CONTEXT,
                SCHEMA_CODE_CONTEXT,
            )
            if self.table:
                logger.info(f"Initialized table '{TABLE_CODE_CONTEXT}' in index_project.")
            else:
                err = 'RAG table unavailable, cannot index.'
                logger.error(err)
                status['errors'].append(err)
                return status

        # Discover files
        files = [
            p for p in self.project_root.rglob('*')
            if p.is_file() and not any(part in self.skip_dirs for part in p.parts)
        ]
        logger.info(f"Found {len(files)} files to index at {self.project_root}.")

        # Process files in parallel
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

        # Skip large files
        try:
            if file_path.stat().st_size > self.max_file_size:
                logger.warning(f"Skipping {file_path}: too large.")
                result['skipped'] = 1
                return result
        except Exception as e:
            logger.error(f"Error accessing {file_path}: {e}")
            result['errors'].append(str(e))
            return result

        # Read content
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            result['errors'].append(str(e))
            return result

        # Wrap into Agno document
        doc = AgnoDocument(
            content=content,
            id=None,
            name=file_path.name,
            meta_data={'file_path': str(file_path)},
        )

        # Chunk document
        try:
            chunks = get_chunker_for_path(file_path).chunk(doc)
        except Exception as e:
            logger.error(f"Chunking failed for {file_path}: {e}")
            result['errors'].append(str(e))
            return result
        if not chunks:
            logger.warning(f"No chunks returned for {file_path}.")
            result['skipped'] = 1
            return result

        # Build records
        records = []
        for d in chunks:
            h = hashlib.sha256(d.content.encode()).hexdigest()
            if h in self.seen_hashes:
                continue
            self.seen_hashes.add(h)
            try:
                vec = embed_text(d.content)
            except Exception as e:
                logger.error(f"Embedding failed for chunk {h}: {e}")
                continue
            meta = d.meta_data or {}
            records.append({
                'path': str(file_path),
                'chunk_name': meta.get('chunk_name', ''),
                'chunk_type': meta.get('chunk_type', ''),
                'content': d.content,
                'vector': vec,
                'start_line': meta.get('start_line', -1),
                'end_line': meta.get('end_line', -1),
                'content_hash': h,
                'language': meta.get('language', ''),
                'lint_errors': meta.get('lint_errors', []),
                'dependencies': meta.get('dependencies', []),
            })

        # Write to LanceDB
        if records:
            try:
                add_or_update_chunks(
                    self.db,
                    TABLE_CODE_CONTEXT,
                    SCHEMA_CODE_CONTEXT,
                    'path',
                    str(file_path),
                    records,
                )
                result['indexed'] = 1
                result['chunks'] = len(records)
            except Exception as e:
                logger.error(f"DB write failed for {file_path}: {e}")
                result['errors'].append(str(e))
        return result
