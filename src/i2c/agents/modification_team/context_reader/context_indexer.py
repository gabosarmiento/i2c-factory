# agents/modification_team/context_reader/context_indexer.py

import os
import hashlib
import logging
from typing import List
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from i2c.db_utils import (
    get_db_connection,
    get_or_create_table,
    add_or_update_chunks,
    TABLE_CODE_CONTEXT,
    SCHEMA_CODE_CONTEXT,
)
from agno.document.base import Document

# Plug-and-play chunker factory and embedding utility
from ..factory import get_chunker_for_path
from ..utils import embed_text
from ..config import load_config
from ..chunkers.jsx_code import JSXCodeChunkingStrategy
from ..chunkers.js_code  import JSCodeChunkingStrategy
from ..chunkers.generic  import GenericTextChunkingStrategy
from i2c.cli.controller import canvas
import esprima

def get_js_chunks(document: Document) -> List[Document]:
    """
    1) Check if file contains JSX syntax (< and > patterns in JS context)
    2) If JSX detected, use JSX chunker regardless of chunk count
    3) Otherwise try the normal JS parser (Esprima).
    4) If that fails, fallback to generic text chunking.
    """
    content = document.content
    
    # 1) Detect JSX syntax - look for JSX patterns
    jsx_indicators = [
        '<div', '<span', '<button', '<input', '<form', '<img', '<a',
        'className=', 'onClick=', 'onChange=', 'onSubmit=', 
        '={', 'React.', 'useState', 'useEffect', 'jsx', 'tsx'
    ]
    
    has_jsx = any(indicator in content for indicator in jsx_indicators)
    
    if has_jsx:
        # Force JSX chunking for any file with JSX patterns
        canvas.info(f"JSX syntax detected, using JSX chunker")
        jsx_chunks = JSXCodeChunkingStrategy().chunk(document)
        canvas.info(f"JSX chunked into {len(jsx_chunks)} blocks")
        return jsx_chunks

    # 2) No JSX detected? Try pure-JS parser
    try:
        js_chunks = JSCodeChunkingStrategy().chunk(document)
        canvas.info(f"Esprima JS parsed into {len(js_chunks)} chunks")
        return js_chunks
    except Exception as e:
        canvas.warning(f"Esprima parse failed ({e}); falling back to generic text")

    # 3) Last resort: generic text splitter
    return GenericTextChunkingStrategy().chunk(document)
 
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
        from i2c.config.config import load_config
        self.config = load_config()
        
        # State for indexing
        self.min_threshold    = self.config.get('MIN_THRESHOLD', 0)
        self.max_file_size    = self.config.get('MAX_FILE_SIZE', 100 * 1024)
        self.max_lines_coarse = self.config.get('MAX_LINES_COARSE', 5000)
        self.skip_dirs        = self.config.get('SKIP_DIRS', [])
        self.workers          = self.config.get('WORKERS', os.cpu_count() or 4)
        
        # Connect to LanceDB and open/create table
        self.db = get_db_connection()
        self.table            = None  # Will be set during index_project
        self.seen_hashes      = set()
        
        logger.info(f"ContextIndexer initialized with max_file_size={self.max_file_size}, "
                    f"max_lines_coarse={self.max_lines_coarse}, skip_dirs={self.skip_dirs}, "
                    f"workers={self.workers}")
    
    def index_project(self) -> dict:
        """
        Index the project, creating the database table if needed.

        Returns:
            Dict with indexing statistics
        """
        status = {'files_indexed': 0, 'files_skipped': 0, 'chunks_indexed': 0, 'errors': []}

        # Step 1: Ensure database connection
        from i2c.db_utils import get_db_connection, get_or_create_table, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT
        self.db = get_db_connection()
        if not self.db:
            err = 'Database connection failed'
            logger.error(err)
            status['errors'].append(err)
            return status

        # Step 2: Get or create the table 
        try:
            logger.info(f"Getting table {TABLE_CODE_CONTEXT}...")
            table = get_or_create_table(self.db, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT)
            if table is None:
                raise RuntimeError(f"Failed to get/create table {TABLE_CODE_CONTEXT}")
            self.table = table
            logger.info(f"Successfully got table: {TABLE_CODE_CONTEXT}")
        except Exception as e:
            err = f"Error getting/creating table: {e}"
            logger.error(err)
            status['errors'].append(err)
            return status

        # Step 3: Find files to index (skip based on SKIP_DIRS)
        try:
            all_files = [
                p for p in self.project_root.rglob('*')
                if p.is_file() and not any(skip in str(p) for skip in self.skip_dirs)
            ]
            logger.info(f"Found {len(all_files)} files to index in {self.project_root}")

            # Warn on unhandled extensions
            from collections import Counter
            from i2c.agents.modification_team.factory import _EXTENSION_MAP
            exts = [p.suffix for p in all_files if p.suffix]
            for ext, count in sorted(Counter(exts).items(), key=lambda x: -x[1]):
                if ext not in _EXTENSION_MAP:
                    logger.warning(f"[Chunker] No handler for extension {ext} ({count} files)")

            # (Temporary) Limit number of files for quick iteration
            if len(all_files) > 100:
                logger.info("Limiting to 100 files for this run")
                all_files = all_files[:100]
        except Exception as e:
            err = f"Error finding files: {e}"
            logger.error(err)
            status['errors'].append(err)
            return status

        # Helper to process a single file (for parallel execution)
        def process_single_file(file_path: Path) -> dict:
            result = {'indexed': 0, 'skipped': 0, 'chunks': 0, 'errors': []}

            try:
                # Read content
                content = file_path.read_text(encoding='utf-8', errors='ignore')
            except Exception as e:
                result['errors'].append(f"Read error: {e}")
                result['skipped'] = 1
                return result

            import hashlib
            file_hash = hashlib.md5(content.encode()).hexdigest()

            try:
                existing = self.db.table(TABLE_CODE_CONTEXT).scan(
                    {'path': str(file_path.relative_to(self.project_root)), 'content_hash': file_hash}
                )
                if any(True for _ in existing):
                    result['skipped'] = 1
                    return result
            except Exception:
                pass

            chunks = self.chunk_and_embed_and_get_chunk_properties(file_path)
            if not chunks:
                result['skipped'] = 1
                return result

            try:
                self.table.add(chunks)
                result['indexed'] = 1
                result['chunks'] = len(chunks)
            except Exception as e:
                result['errors'].append(f"DB add error: {e}")
                result['skipped'] = 1

            return result

        # Step 5: Parallel file processing
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {pool.submit(process_single_file, fp): fp for fp in all_files}
            for fut in as_completed(futures):
                res = fut.result()
                if res.get('indexed'):
                    status['files_indexed'] += 1
                    status['chunks_indexed'] += res.get('chunks', 0)
                    logger.info(f"Indexed {res.get('chunks',0)} chunks from {futures[fut]}")
                else:
                    status['files_skipped'] += 1
                if res.get('errors'):
                    status['errors'].extend(res['errors'])

        logger.info(
            f"Indexing complete: {status['files_indexed']} files, "
            f"{status['chunks_indexed']} chunks, {status['files_skipped']} skipped."
        )
        return status

    def __str__(self):
        return f"ContextIndexer(project_root={self.project_root}, db={self.db is not None})"

    def __repr__(self):
        return self.__str__()

    def chunk_and_embed_and_get_chunk_properties(self, file_path: Path) -> list:
        """Process a file into chunks with embeddings and properties.

        Args:
            file_path: Path to the file to process

        Returns:
            List of dictionaries with chunk data
        """
        logger.info(f"Processing file: {file_path}")

        # Skip large files by byte size
        try:
            if file_path.stat().st_size > self.max_file_size:
                logger.warning(f"Skipping {file_path}: too large")
                return []
        except Exception as e:
            logger.error(f"Error accessing file: {e}")
            return []

        # Read content
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return []

        # Create AGNO document
        from agno.document.base import Document as AgnoDocument
        doc = AgnoDocument(
            content=content,
            id=None,
            name=file_path.name,
            meta_data={'file_path': str(file_path)},
        )

        # COARSE vs FINE chunking based on line count
        lines = content.splitlines()
        if len(lines) > self.max_lines_coarse:
            from agno.document.chunking.fixed import FixedSizeChunking
            logger.info(
                f"{file_path.name} has {len(lines)} lines (>{self.max_lines_coarse}); using FixedSizeChunking"
            )
            chunks = FixedSizeChunking(chunk_size=500, overlap=50).chunk(doc)
        else:
            # Fine-grained chunking: route .js through get_js_chunks, everything else via factory
            try:
                # for .js files, first attempt JSX-regex then Esprima then generic
                if file_path.suffix.lower() == '.js':
                    from ..chunkers.jsx_code import JSXCodeChunkingStrategy
                    from ..chunkers.js_code   import JSCodeChunkingStrategy
                    from ..chunkers.generic   import GenericTextChunkingStrategy
                    chunks = get_js_chunks(doc)   
                else:
                    from i2c.agents.modification_team.factory import get_chunker_for_path
                    chunker = get_chunker_for_path(file_path)
                    chunks  = chunker.chunk(doc)
            except Exception as e:
                logger.error(f"Failed to chunk {file_path}: {e}")
                return []
        if not chunks:
            logger.warning(f"No chunks returned for {file_path}")
            return []

        # Deduplicate, embed, and prepare records
        import hashlib
        from i2c.agents.modification_team.context_utils import generate_embedding as embed_text

        records = []
        for d in chunks:
            try:
                content_hash = hashlib.sha256(d.content.encode()).hexdigest()
                if content_hash in self.seen_hashes:
                    continue
                self.seen_hashes.add(content_hash)

                vec = embed_text(d.content)
                if vec is None:
                    logger.warning(f"Embedding failed for chunk in {file_path}")
                    continue

                meta = d.meta_data or {}
                chunk_name = meta.get('chunk_name', '')
                chunk_type = meta.get('chunk_type', '')
                chunk_id = hashlib.sha256(
                    f"{file_path}::{chunk_name}::{d.content}".encode()
                ).hexdigest()

                record = {
                    'chunk_id': chunk_id,
                    'path': str(file_path.relative_to(self.project_root)),
                    'chunk_name': chunk_name,
                    'chunk_type': chunk_type,
                    'content': d.content,
                    'vector': vec,
                    'start_line': meta.get('start_line', -1),
                    'end_line': meta.get('end_line', -1),
                    'content_hash': content_hash,
                    'language': meta.get('language', ''),
                    'lint_errors': meta.get('lint_errors', []),
                    'dependencies': meta.get('dependencies', []),
                }
                records.append(record)
            except Exception as e:
                logger.error(f"Error processing chunk: {e}")

        logger.info(f"Processed {len(records)} chunks from {file_path}")
        return records

    def index_project(self) -> dict:
        """
        Index the project, creating the database table if needed.
        
        Returns:
            Dict with indexing statistics
        """
        status = {'files_indexed': 0, 'files_skipped': 0, 'chunks_indexed': 0, 'errors': []}
        
        # Step 1: Ensure database connection
        from i2c.db_utils import get_db_connection, get_or_create_table, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT
        
        # Get a fresh connection
        self.db = get_db_connection()
        if not self.db:
            err = 'Database connection failed'
            logger.error(err)
            status['errors'].append(err)
            return status
        
        # Step 2: Get or create the table 
        try:
            logger.info(f"Getting table {TABLE_CODE_CONTEXT}...")
            # Directly open/create table without using self.table attribute
            table = get_or_create_table(self.db, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT)
            if table is None:
                err = f"Failed to get/create table {TABLE_CODE_CONTEXT}"
                logger.error(err)
                status['errors'].append(err)
                return status
            
            # Store the table reference
            self.table = table
            logger.info(f"Successfully got table: {TABLE_CODE_CONTEXT}")
        except Exception as e:
            err = f"Error getting/creating table: {e}"
            logger.error(err)
            status['errors'].append(err)
            return status
        
        # Step 3: Find files to index
        try:
            files = [
                p for p in self.project_root.rglob('*')
                if p.is_file() and not any(skip_dir in str(p) for skip_dir in self.skip_dirs)
            ]
            logger.info(f"Found {len(files)} files to index in {self.project_root}")
            from collections import Counter
            from i2c.agents.modification_team.factory import _EXTENSION_MAP

            exts = [p.suffix for p in files if p.suffix]
            ext_counter = Counter(exts)
            for ext, count in sorted(ext_counter.items(), key=lambda x: -x[1]):
                if ext not in _EXTENSION_MAP:
                    logger.warning(f"[Chunker] No handler for extension {ext} ({count} files)")
            # Limit number of files for testing
            if len(files) > 100:
                logger.info(f"Limiting to 100 files for processing")
                files = files[:100]
        except Exception as e:
            err = f"Error finding files: {e}"
            logger.error(err)
            status['errors'].append(err)
            return status
        
        # Step 4: Process each file
        total_chunks = 0
        for file_path in files:
            try:
                # Process file into chunks
                chunks = self.chunk_and_embed_and_get_chunk_properties(file_path)
                if not chunks:
                    status['files_skipped'] += 1
                    continue
                
                # Add chunks to database
                try:
                    # Add directly to the table
                    self.table.add(chunks)
                    status['files_indexed'] += 1
                    status['chunks_indexed'] += len(chunks)
                    total_chunks += len(chunks)
                    logger.info(f"Added {len(chunks)} chunks from {file_path}")
                except Exception as e:
                    logger.error(f"Error adding chunks to database: {e}")
                    status['errors'].append(f"Database error for {file_path}: {e}")
                    status['files_skipped'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                status['errors'].append(f"File processing error: {e}")
                status['files_skipped'] += 1
        
        logger.info(
            f"Indexing complete: {status['files_indexed']} files, "
            f"{status['chunks_indexed']} chunks, {status['files_skipped']} skipped."
        )
        return status
  
    def _process_file(self, file_path: Path) -> dict:
        """Process a single file into chunks and add to database."""
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

        records = self.chunk_and_embed_and_get_chunk_properties(file_path)
        if not records:
            result['skipped'] = 1
            return result

        
        # Add records to database
        if records:
            try:
                # Try to add directly to self.table
                if self.table is not None:
                    try:
                        self.table.add(records)
                        result['indexed'] = 1
                        result['chunks'] = len(records)
                        logger.info(f"Added {len(records)} chunks from {file_path}")
                        return result
                    except Exception as e:
                        logger.error(f"Error adding chunks to table: {e}")
                
                # Fallback to using add_or_update_chunks
                from i2c.db_utils import add_or_update_chunks, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT
                success = add_or_update_chunks(
                    self.db,
                    TABLE_CODE_CONTEXT,
                    SCHEMA_CODE_CONTEXT,
                    'path',
                    str(file_path.relative_to(self.project_root)),
                    records,
                )
                if success:
                    result['indexed'] = 1
                    result['chunks'] = len(records)
                    logger.info(f"Added {len(records)} chunks via add_or_update_chunks")
                else:
                    result['errors'].append("Failed to add chunks via add_or_update_chunks")
            except Exception as e:
                logger.error(f"Error adding chunks to database for {file_path}: {e}")
                result['errors'].append(str(e))
        
        return result