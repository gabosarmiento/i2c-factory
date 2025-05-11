# agents/modification_team/context_reader/context_indexer.py

import os
import hashlib
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from i2c.db_utils import (
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

        # State for indexing
        self.seen_hashes = set()
        self.max_file_size = self.config.get('MAX_FILE_SIZE', 100 * 1024)
        self.skip_dirs = set(self.config.get('SKIP_DIRS', []))
        self.workers = self.config.get('WORKERS', os.cpu_count() or 4)
        self.table = None  # Will be set during index_project
        
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
        
        # Skip large files
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
        
        # Create document
        from agno.document.base import Document
        doc = Document(
            content=content,
            id=None,
            name=file_path.name,
            meta_data={'file_path': str(file_path)},
        )
        
        # Get chunker for file type
        try:
            from i2c.agents.modification_team.factory import get_chunker_for_path
            chunker = get_chunker_for_path(file_path)
            chunks = chunker.chunk(doc)
        except Exception as e:
            logger.error(f"Error chunking file: {e}")
            return []
        
        if not chunks:
            logger.warning(f"No chunks returned for {file_path}")
            return []
        
        # Process chunks
        import hashlib
        from i2c.agents.modification_team.utils import embed_text
        
        records = []
        for d in chunks:
            try:
                # Calculate hash
                h = hashlib.sha256(d.content.encode()).hexdigest()
                if h in self.seen_hashes:
                    continue
                self.seen_hashes.add(h)
                
                # Generate embedding
                vec = embed_text(d.content)
                if vec is None:
                    logger.warning(f"Embedding failed for chunk in {file_path}")
                    continue
                
                # Create record
                meta = d.meta_data or {}
                record = {
                    'path': str(file_path.relative_to(self.project_root)),
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

        # Process file to generate chunks...
        # [existing code for creating chunks]
        
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