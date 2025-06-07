# agents/modification_team/context_reader/incremental_indexer.py

import os
import hashlib
import logging
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from datetime import datetime

from i2c.db_utils import (
    get_db_connection,
    get_or_create_table,
    add_or_update_chunks,
    TABLE_CODE_CONTEXT,
    SCHEMA_CODE_CONTEXT,
)
from agno.document.base import Document

# Import existing components
from ..factory import get_chunker_for_path
from ..utils import embed_text
from ..config import load_config
from .context_indexer import get_js_chunks
from i2c.cli.controller import canvas

logger = logging.getLogger(__name__)

# Schema for file metadata tracking
import pyarrow as pa

SCHEMA_FILE_METADATA = pa.schema([
    ("file_path", pa.string()),
    ("file_size", pa.int64()), 
    ("mtime", pa.float64()),
    ("content_hash", pa.string()),
    ("last_indexed", pa.string()),
    ("chunk_count", pa.int64()),
])

TABLE_FILE_METADATA = "file_metadata"

class IncrementalContextIndexer:
    """
    Intelligent context indexer that only processes changed files.
    
    Features:
    - Tracks file metadata (size, mtime, hash) to detect changes
    - Only reindexes files that have actually changed
    - Handles file deletions and updates
    - Significantly faster than full reindexing
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        from i2c.config.config import load_config
        self.config = load_config()
        
        # Configuration
        self.max_file_size = self.config.get('MAX_FILE_SIZE', 100 * 1024)
        self.skip_dirs = self.config.get('SKIP_DIRS', [
            '.git', '__pycache__', '.venv', 'venv', 'node_modules', 
            'build', 'dist', 'target', '.pytest_cache', '.mypy_cache',
            '.idea', '.vscode', 'coverage', 'logs', 'tmp'
        ])
        self.workers = self.config.get('WORKERS', os.cpu_count() or 4)
        
        # Database connections
        self.db = get_db_connection()
        self.code_table = None
        self.metadata_table = None
        
        logger.info(f"IncrementalContextIndexer initialized for {project_root}")
    
    def _get_file_metadata(self, file_path: Path) -> Dict:
        """Get current file metadata for change detection"""
        try:
            stat = file_path.stat()
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            return {
                'file_path': str(file_path.relative_to(self.project_root)),
                'file_size': stat.st_size,
                'mtime': stat.st_mtime,
                'content_hash': content_hash,
                'content': content
            }
        except Exception as e:
            logger.warning(f"Failed to get metadata for {file_path}: {e}")
            return None
    
    def _load_stored_metadata(self) -> Dict[str, Dict]:
        """Load stored file metadata from database"""
        stored_metadata = {}
        
        try:
            if self.metadata_table is not None:
                df = self.metadata_table.to_pandas()
                for _, row in df.iterrows():
                    stored_metadata[row['file_path']] = {
                        'file_size': row['file_size'],
                        'mtime': row['mtime'],
                        'content_hash': row['content_hash'],
                        'last_indexed': row['last_indexed'],
                        'chunk_count': row['chunk_count']
                    }
        except Exception as e:
            logger.debug(f"No stored metadata found: {e}")
        
        return stored_metadata
    
    def _file_needs_reindexing(self, file_path: str, current_meta: Dict, stored_meta: Dict) -> bool:
        """Determine if file needs reindexing"""
        if file_path not in stored_meta:
            canvas.info(f"📄 New file: {file_path}")
            return True
        
        stored = stored_meta[file_path]
        
        # Check if file has changed
        if (current_meta['file_size'] != stored['file_size'] or
            current_meta['mtime'] != stored['mtime'] or
            current_meta['content_hash'] != stored['content_hash']):
            canvas.info(f"📝 Changed: {file_path}")
            return True
        
        return False
    
    def _update_file_metadata(self, file_path: str, metadata: Dict, chunk_count: int):
        """Update stored metadata for a file"""
        try:
            metadata_record = {
                'file_path': file_path,
                'file_size': metadata['file_size'],
                'mtime': metadata['mtime'],
                'content_hash': metadata['content_hash'],
                'last_indexed': datetime.now().isoformat(),
                'chunk_count': chunk_count
            }
            
            # Store metadata in the file_metadata table
            if self.metadata_table is not None:
                try:
                    # First, try to remove existing record for this file
                    try:
                        # Delete any existing records for this file_path
                        self.metadata_table.delete(f"file_path = '{file_path}'")
                    except Exception:
                        # If delete fails, that's okay - might not exist
                        pass
                    
                    # Add the new metadata record
                    self.metadata_table.add([metadata_record])
                    canvas.info(f"Updated metadata for {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to store metadata in table for {file_path}: {e}")
            else:
                logger.warning(f"No metadata table available for {file_path}")
            
        except Exception as e:
            logger.warning(f"Failed to update metadata for {file_path}: {e}")
    
    def _find_files_to_process(self) -> List[Path]:
        """Find all eligible files in the project"""
        files_to_check = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip directories in skip_dirs
            dirs[:] = [d for d in dirs if d not in self.skip_dirs]
            
            for file in files:
                file_path = Path(root) / file
                
                # Skip files that are too large
                try:
                    if file_path.stat().st_size > self.max_file_size:
                        continue
                except:
                    continue
                
                # Only process text files
                if file_path.suffix.lower() in [
                    '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', 
                    '.h', '.hpp', '.cs', '.rb', '.go', '.rs', '.php', '.html', 
                    '.css', '.scss', '.sass', '.less', '.vue', '.svelte', '.md',
                    '.txt', '.json', '.yaml', '.yml', '.xml', '.sql', '.sh'
                ]:
                    files_to_check.append(file_path)
        
        return files_to_check
    
    def _process_file(self, file_path: Path) -> Tuple[str, int, List[str]]:
        """Process a single file and return chunks"""
        errors = []
        chunk_count = 0
        
        try:
            # Get current file metadata
            metadata = self._get_file_metadata(file_path)
            if not metadata:
                return str(file_path.relative_to(self.project_root)), 0, ["Failed to get metadata"]
            
            # Create document and chunk it
            document = Document(content=metadata['content'], 
                              meta_data={'file_path': str(file_path.relative_to(self.project_root))})
            
            # Get appropriate chunker
            try:
                if file_path.suffix.lower() in ['.js', '.jsx']:
                    # Use improved JSX detection
                    chunks = get_js_chunks(document)
                else:
                    chunker = get_chunker_for_path(file_path)
                    chunks = chunker.chunk(document)
            except Exception as e:
                logger.warning(f"Chunking failed for {file_path}: {e}")
                from ..chunkers.generic import GenericTextChunkingStrategy
                chunks = GenericTextChunkingStrategy().chunk(document)
            
            # Process chunks for database insertion
            chunk_data = []
            for i, chunk in enumerate(chunks):
                try:
                    embedding = embed_text(chunk.content)
                    if embedding is None:
                        continue
                    
                    chunk_id = hashlib.sha256(
                        f"{metadata['file_path']}:{i}:{chunk.content[:100]}".encode()
                    ).hexdigest()
                    
                    chunk_record = {
                        'chunk_id': chunk_id,
                        'path': metadata['file_path'],
                        'content': chunk.content,
                        'chunk_name': '',
                        'chunk_type': '',
                        'vector': embedding,
                        'start_line': -1,
                        'end_line': -1,
                        'content_hash': hashlib.sha256(chunk.content.encode()).hexdigest(),
                        'language': '',
                        'lint_errors': [],
                        'dependencies': []
                    }
                    
                    chunk_data.append(chunk_record)
                    chunk_count += 1
                
                except Exception as e:
                    errors.append(f"Chunk {i} error: {str(e)}")
            
            # Add chunks to database
            if chunk_data and self.code_table is not None:
                try:
                    # Use the table's add method directly instead of add_or_update_chunks
                    self.code_table.add(chunk_data)
                except Exception as e:
                    errors.append(f"Database insertion error: {str(e)}")
            
            # Update file metadata
            self._update_file_metadata(metadata['file_path'], metadata, chunk_count)
            
            return metadata['file_path'], chunk_count, errors
            
        except Exception as e:
            errors.append(f"File processing error: {str(e)}")
            return str(file_path.relative_to(self.project_root)), 0, errors
    
    def index_project_incrementally(self) -> Dict:
        """
        Intelligently index only changed files in the project.
        """
        status = {
            'files_checked': 0,
            'files_indexed': 0, 
            'files_skipped': 0,
            'files_unchanged': 0,
            'chunks_indexed': 0,
            'errors': []
        }
        
        canvas.step("🔍 Starting incremental indexing...")
        
        # Initialize database tables
        try:
            self.db = get_db_connection()
            if not self.db:
                status['errors'].append('Database connection failed')
                return status
            
            # Handle code_context table
            try:
                self.code_table = get_or_create_table(self.db, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT)
                if self.code_table is None:
                    status['errors'].append(f'Failed to create/get {TABLE_CODE_CONTEXT} table')
                    return status
                canvas.info(f"Successfully got {TABLE_CODE_CONTEXT} table")
            except Exception as e:
                status['errors'].append(f'Error with {TABLE_CODE_CONTEXT} table: {str(e)}')
                return status
            
            # Handle metadata table
            try:
                self.metadata_table = get_or_create_table(self.db, TABLE_FILE_METADATA, SCHEMA_FILE_METADATA)
                if self.metadata_table is None:
                    status['errors'].append(f'Failed to create/get {TABLE_FILE_METADATA} table')
                    return status
                canvas.info(f"Successfully got {TABLE_FILE_METADATA} table")
            except Exception as e:
                status['errors'].append(f'Error with {TABLE_FILE_METADATA} table: {str(e)}')
                return status
                
        except Exception as e:
            status['errors'].append(f'Database initialization error: {str(e)}')
            return status
        
        # Load stored metadata
        stored_metadata = self._load_stored_metadata()
        canvas.info(f"📋 Found {len(stored_metadata)} previously indexed files")
        
        # Find files to check
        files_to_check = self._find_files_to_process()
        status['files_checked'] = len(files_to_check)
        
        # Determine which files need reindexing
        files_to_index = []
        for file_path in files_to_check:
            current_metadata = self._get_file_metadata(file_path)
            if not current_metadata:
                status['files_skipped'] += 1
                continue
            
            if self._file_needs_reindexing(current_metadata['file_path'], current_metadata, stored_metadata):
                files_to_index.append(file_path)
            else:
                status['files_unchanged'] += 1
        
        canvas.info(f"📝 {len(files_to_index)} files need indexing, {status['files_unchanged']} unchanged")
        
        if not files_to_index:
            canvas.success("✅ All files up to date!")
            return status
        
        # Process files that need indexing
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_file = {
                executor.submit(self._process_file, file_path): file_path 
                for file_path in files_to_index
            }
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    file_rel_path, chunk_count, errors = future.result()
                    
                    if errors:
                        status['errors'].extend([f"{file_rel_path}: {err}" for err in errors])
                        status['files_skipped'] += 1
                    else:
                        status['files_indexed'] += 1
                        status['chunks_indexed'] += chunk_count
                        
                except Exception as e:
                    rel_path = str(file_path.relative_to(self.project_root))
                    status['errors'].append(f"{rel_path}: {str(e)}")
                    status['files_skipped'] += 1
        
        canvas.success(f"✅ Incremental indexing complete!")
        canvas.info(f"📊 {status['files_indexed']} indexed, {status['files_unchanged']} unchanged")
        
        return status

# Factory function
def create_incremental_indexer(project_root: Path) -> IncrementalContextIndexer:
    """Create an incremental context indexer"""
    return IncrementalContextIndexer(project_root)