# Enhanced Knowledge Ingestion System
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
import hashlib
import datetime as _dt
import json
import pickle
from dataclasses import dataclass, asdict
from agno.embedder.sentence_transformer import SentenceTransformerEmbedder
from i2c.agents.budget_manager import BudgetManagerAgent
from i2c.cli.controller import canvas
from i2c.db_utils import get_db_connection, add_knowledge_chunks, query_context, TABLE_KNOWLEDGE_BASE

# Add this right after the existing imports in enhanced_knowledge_ingestor.py

class ContextAwareOperator:
    """Simplified base class for context-aware operations"""
    
    def __init__(self, budget_manager, operation_type, max_reasoning_steps=3, default_model_tier="middle"):
        self.budget_manager = budget_manager
        self.operation_type = operation_type
        self.max_reasoning_steps = max_reasoning_steps
        self.default_model_tier = default_model_tier
        
        # Simple cost tracker
        self.cost_tracker = SimpleCostTracker()

class SimpleCostTracker:
    """Simple cost tracking"""
    
    def __init__(self):
        self.trajectory = []
    
    def start_phase(self, phase_id, description, model_id):
        self.trajectory.append({
            "phase": phase_id,
            "description": description,
            "model": model_id,
            "status": "started"
        })
    
    def end_phase(self, success=True, result=None, feedback=None):
        if self.trajectory:
            self.trajectory[-1].update({
                "status": "completed",
                "success": success,
                "result": result,
                "feedback": feedback
            })
    
    def complete_operation(self, success=True, final_result=None):
        pass  # Simplified
    
@dataclass
class DocumentMetadata:
    """Enhanced metadata tracking for documents"""
    source_path: str
    file_hash: str
    file_size: int
    last_modified: float
    document_type: str
    framework: str = ""
    version: str = ""
    chunk_count: int = 0
    ingested_at: str = ""
    knowledge_space: str = "default"

class IntelligentKnowledgeCache:
    """Smart caching system for knowledge ingestion"""
    
    def __init__(self, cache_file: Path = Path(".knowledge_cache.json")):
        self.cache_file = cache_file
        self._cache: Dict[str, DocumentMetadata] = {}
        self._load_cache()
    
    def _load_cache(self):
        """Load existing cache from disk"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    self._cache = {
                        key: DocumentMetadata(**value) 
                        for key, value in cache_data.items()
                    }
                canvas.info(f"Loaded cache with {len(self._cache)} entries")
            except Exception as e:
                canvas.warning(f"Failed to load cache: {e}")
                self._cache = {}
    
    def _save_cache(self):
        """Save cache to disk"""
        try:
            cache_data = {
                key: asdict(value) 
                for key, value in self._cache.items()
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            canvas.error(f"Failed to save cache: {e}")
    
    def should_process_file(self, file_path: Path) -> bool:
        """Check if file needs processing based on metadata"""
        try:
            stat = file_path.stat()
            file_hash = self._compute_file_hash(file_path)
            cache_key = str(file_path)
            
            if cache_key not in self._cache:
                return True
            
            cached_meta = self._cache[cache_key]
            
            # Check if file has changed
            if (cached_meta.file_hash != file_hash or 
                cached_meta.last_modified != stat.st_mtime or
                cached_meta.file_size != stat.st_size):
                return True
                
            return False
            
        except Exception as e:
            canvas.warning(f"Error checking file {file_path}: {e}")
            return True  # Process if we can't determine
    
    def mark_processed(self, file_path: Path, metadata: DocumentMetadata):
        """Mark file as processed in cache"""
        self._cache[str(file_path)] = metadata
        self._save_cache()
    
    def get_cached_metadata(self, file_path: Path) -> Optional[DocumentMetadata]:
        """Get cached metadata for a file"""
        return self._cache.get(str(file_path))
    
    def invalidate_file(self, file_path: Path):
        """Remove file from cache (force reprocessing)"""
        cache_key = str(file_path)
        if cache_key in self._cache:
            del self._cache[cache_key]
            self._save_cache()
    
    def cleanup_cache(self, valid_files: Set[Path]):
        """Remove cache entries for files that no longer exist"""
        valid_paths = {str(p) for p in valid_files}
        to_remove = [key for key in self._cache.keys() if key not in valid_paths]
        
        for key in to_remove:
            del self._cache[key]
        
        if to_remove:
            canvas.info(f"Cleaned up {len(to_remove)} stale cache entries")
            self._save_cache()
    
    @staticmethod
    def _compute_file_hash(file_path: Path) -> str:
        """Compute SHA-256 hash of file content"""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

class EnhancedKnowledgeIngestorAgent(ContextAwareOperator):
    """Enhanced documentation ingestion with intelligent caching and deduplication"""
    
    def __init__(
        self,
        budget_manager: BudgetManagerAgent,
        knowledge_space: str = "default",
        embed_model=None,
        cache_file: Optional[Path] = None,
        **kwargs
    ):
        super().__init__(
            budget_manager=budget_manager,
            operation_type="knowledge_ingestion",
            max_reasoning_steps=3,
            default_model_tier="middle"
        )
        self.knowledge_space = knowledge_space
        self.embed_model = embed_model or SentenceTransformerEmbedder()
        
        # Initialize intelligent cache
        cache_path = cache_file or Path(f".knowledge_cache_{knowledge_space}.json")
        self.cache = IntelligentKnowledgeCache(cache_path)
        
        # Supported file types
        self.supported_extensions = {
            '.pdf', '.txt', '.md', '.markdown', '.rst', '.docx',
            '.html', '.htm', '.json', '.csv', '.py', '.js', '.ts',
            '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.go', '.rs'
        }
    
    def execute(
        self,
        document_path: Path,
        document_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        force_refresh: bool = False,
        recursive: bool = True,
        selected_files: Optional[List[Path]] = None
    ) -> Tuple[bool, Dict]:
        """
        Process and ingest documentation with intelligent caching.
        
        Args:
            document_path: Path to file or directory
            document_type: Type of documentation
            metadata: Additional metadata
            force_refresh: Force reprocessing even if cached
            recursive: Process directories recursively
            selected_files: Specific files to process (for directories)
        """
        phase_id = "document_ingestion"
        self.cost_tracker.start_phase(
            phase_id,
            f"Ingest document(s): {document_path.name}",
            model_id="knowledge_ingestor"
        )

        try:
            if not document_path.exists():
                raise FileNotFoundError(f"Document not found: {document_path}")
            
            result_stats = {
                "processed_files": 0,
                "successful_files": 0,
                "failed_files": 0,
                "skipped_files": 0,
                "chunks_created": 0,
                "cache_hits": 0,
                "errors": []
            }
            
            if document_path.is_dir():
                self._process_directory(
                    document_path, document_type, metadata or {},
                    result_stats, force_refresh, recursive, selected_files
                )
            else:
                self._process_file(
                    document_path, document_type, metadata or {},
                    result_stats, force_refresh
                )
            
            success = result_stats["failed_files"] == 0
            self.cost_tracker.end_phase(success=success, result=result_stats)
            
            # Print summary
            self._print_processing_summary(result_stats)
            
            return success, result_stats

        except Exception as e:
            canvas.error(f"Error in document ingestion: {e}")
            self.cost_tracker.end_phase(success=False, feedback=str(e))
            return False, {"error": str(e), "document_path": str(document_path)}
    
    def _process_directory(
        self,
        directory_path: Path,
        document_type: str,
        metadata: Dict[str, Any],
        result_stats: Dict[str, Any],
        force_refresh: bool,
        recursive: bool,
        selected_files: Optional[List[Path]]
    ) -> None:
        """Process all supported files in a directory"""
        
        if selected_files:
            files_to_process = [
                f for f in selected_files
                if f.exists() and f.is_file() and directory_path in f.parents
            ]
        else:
            pattern = "**/*" if recursive else "*"
            all_files = list(directory_path.glob(pattern))
            
            # Filter to supported file types and exclude system directories
            files_to_process = [
                f for f in all_files
                if (f.is_file() and 
                    f.suffix.lower() in self.supported_extensions and
                    not any(part.startswith('.') for part in f.parts) and
                    not any(ignore in f.parts for ignore in [
                        "__pycache__", "node_modules", ".git", ".venv", 
                        ".pytest_cache", "dist", "build"
                    ]))
            ]
        
        canvas.info(f"Found {len(files_to_process)} supported files in {directory_path}")
        
        # Cleanup cache for files that no longer exist
        if not selected_files:  # Only cleanup when processing entire directory
            valid_files = set(files_to_process)
            self.cache.cleanup_cache(valid_files)
        
        # Process each file
        for file_path in files_to_process:
            try:
                result_stats["processed_files"] += 1
                self._process_file(file_path, document_type, metadata, result_stats, force_refresh)
            except Exception as e:
                result_stats["failed_files"] += 1
                result_stats["errors"].append(f"Error processing {file_path}: {e}")
                canvas.error(f"Error processing {file_path}: {e}")
    
    def _process_file(
        self,
        file_path: Path,
        document_type: str,
        metadata: Dict[str, Any],
        result_stats: Dict[str, Any],
        force_refresh: bool
    ) -> None:
        """Process a single file with intelligent caching"""
        
        # Check cache first (unless force refresh)
        if not force_refresh and not self.cache.should_process_file(file_path):
            canvas.info(f"Skipping {file_path.name} (cached, unchanged)")
            result_stats["skipped_files"] += 1
            result_stats["cache_hits"] += 1
            return
        
        # Additional database check for hash-based deduplication
        if not force_refresh:
            try:
                file_hash = self.cache._compute_file_hash(file_path)
                db = get_db_connection()
                if db:
                    try:
                        table = db.open_table(TABLE_KNOWLEDGE_BASE)
                        existing = table.search().where(
                            f"source_hash = '{file_hash}' AND knowledge_space = '{self.knowledge_space}'"
                        ).limit(1).to_pandas()
                    except:
                        existing = None
                    if existing is not None and not existing.empty:
                        canvas.info(f"Skipping {file_path.name} (already in database)")
                        result_stats["skipped_files"] += 1
                        
                        # Update cache with database info
                        stat = file_path.stat()
                        cached_meta = DocumentMetadata(
                            source_path=str(file_path),
                            file_hash=file_hash,
                            file_size=stat.st_size,
                            last_modified=stat.st_mtime,
                            document_type=document_type,
                            knowledge_space=self.knowledge_space
                        )
                        self.cache.mark_processed(file_path, cached_meta)
                        return
            except Exception as e:
                canvas.warning(f"Database check failed for {file_path}: {e}")
        
        # Budget approval
        if self.budget_manager and not self.budget_manager.request_approval(
            description=f"Ingest file: {file_path.name}",
            prompt=f"Process {file_path.name} for knowledge base",
            model_id="knowledge_ingestor"
        ):
            canvas.warning(f"Budget denied for file: {file_path}")
            result_stats["skipped_files"] += 1
            return

        try:
            # Process the file
            chunks = self._extract_and_embed_chunks(file_path, document_type, metadata)
            
            if not chunks:
                canvas.warning(f"No content extracted from {file_path}")
                result_stats["failed_files"] += 1
                return
            
            # Save to database
            db = get_db_connection()
            if not db:
                raise RuntimeError("Database connection failed")

            success = add_knowledge_chunks(db, chunks, self.knowledge_space)
            
            if success:
                canvas.success(f"Successfully ingested: {file_path.name} ({len(chunks)} chunks)")
                result_stats["successful_files"] += 1
                result_stats["chunks_created"] += len(chunks)
                
                # Update cache
                stat = file_path.stat()
                file_hash = self.cache._compute_file_hash(file_path)
                cached_meta = DocumentMetadata(
                    source_path=str(file_path),
                    file_hash=file_hash,
                    file_size=stat.st_size,
                    last_modified=stat.st_mtime,
                    document_type=document_type,
                    framework=metadata.get("framework", ""),
                    version=metadata.get("version", ""),
                    chunk_count=len(chunks),
                    ingested_at=_dt.datetime.now().isoformat(),
                    knowledge_space=self.knowledge_space
                )
                self.cache.mark_processed(file_path, cached_meta)
            else:
                raise RuntimeError("Failed to add chunks to database")

        except Exception as e:
            canvas.error(f"Error processing file {file_path}: {e}")
            result_stats["failed_files"] += 1
            result_stats["errors"].append(f"Error processing file: {e}")
    
    def _extract_and_embed_chunks(
        self, 
        file_path: Path, 
        document_type: str, 
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract content and create embedding chunks"""
        
        # Handle different file types
        if file_path.suffix.lower() == ".pdf":
            documents = self._process_pdf(file_path)
        elif file_path.suffix.lower() in ['.md', '.markdown']:
            documents = self._process_markdown(file_path)
        elif file_path.suffix.lower() in ['.html', '.htm']:
            documents = self._process_html(file_path)
        elif file_path.suffix.lower() == '.json':
            documents = self._process_json(file_path)
        else:
            documents = self._process_text(file_path)
        
        if not documents:
            return []
        
        # Create chunks with embeddings
        chunks = []
        file_hash = self.cache._compute_file_hash(file_path)
        
        for i, doc in enumerate(documents):
            text = getattr(doc, 'content', str(doc))
            if not text.strip():
                continue
                
            vector = self.embed_model.get_embedding(text)
            
            chunk = {
                "source": str(file_path),
                "content": text,
                "vector": vector,
                "category": document_type,
                "last_updated": _dt.datetime.now().isoformat(),
                "knowledge_space": self.knowledge_space,
                "document_type": document_type,
                "framework": metadata.get("framework", ""),
                "version": metadata.get("version", ""),
                "parent_doc_id": "",
                "chunk_type": f"chunk_{i}",
                "source_hash": file_hash,
                "metadata_json": json.dumps(metadata),
            }
            chunks.append(chunk)
        
        return chunks
    
    def _process_pdf(self, file_path: Path):
        """Process PDF files"""
        try:
            from agno.document.reader.pdf_reader import PDFReader
            reader = PDFReader(chunk=True)
            return reader.read(str(file_path))
        except ImportError:
            canvas.warning(f"PDF processing not available for {file_path}")
            return []
    
    def _process_markdown(self, file_path: Path):
        """Process Markdown files with section splitting"""
        from agno.document.base import Document
        
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            
            # Split by headers for better chunking
            sections = self._split_markdown_by_headers(content)
            
            documents = []
            for i, section in enumerate(sections):
                if section.strip():
                    documents.append(Document(
                        content=section,
                        name=f"{file_path.stem}_section_{i}"
                    ))
            
            return documents
        except Exception as e:
            canvas.error(f"Error processing markdown {file_path}: {e}")
            return []
    
    def _process_html(self, file_path: Path):
        """Process HTML files"""
        from agno.document.base import Document
        
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            
            # Basic HTML text extraction (you might want to use BeautifulSoup)
            import re
            # Remove script and style content
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
            # Remove HTML tags
            content = re.sub(r'<[^>]+>', '', content)
            # Clean up whitespace
            content = re.sub(r'\s+', ' ', content).strip()
            
            if content:
                return [Document(content=content, name=file_path.stem)]
            return []
        except Exception as e:
            canvas.error(f"Error processing HTML {file_path}: {e}")
            return []
    
    def _process_json(self, file_path: Path):
        """Process JSON files"""
        from agno.document.base import Document
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert JSON to readable text
            content = json.dumps(data, indent=2, ensure_ascii=False)
            return [Document(content=content, name=file_path.stem)]
        except Exception as e:
            canvas.error(f"Error processing JSON {file_path}: {e}")
            return []
    
    def _process_text(self, file_path: Path):
        """Process plain text files"""
        from agno.document.base import Document
        
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if content.strip():
                return [Document(content=content, name=file_path.stem)]
            return []
        except Exception as e:
            canvas.error(f"Error processing text {file_path}: {e}")
            return []
    
    def _split_markdown_by_headers(self, content: str) -> List[str]:
        """Split markdown content by headers for better chunking"""
        lines = content.split('\n')
        sections = []
        current_section = []
        
        for line in lines:
            if line.startswith('#') and current_section:
                sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)
        
        if current_section:
            sections.append('\n'.join(current_section))
        
        return sections
    
    def _print_processing_summary(self, stats: Dict[str, Any]):
        """Print a summary of processing results"""
        canvas.info("=" * 50)
        canvas.info("KNOWLEDGE INGESTION SUMMARY")
        canvas.info("=" * 50)
        canvas.info(f"📁 Processed files: {stats['processed_files']}")
        canvas.info(f"✅ Successful: {stats['successful_files']}")
        canvas.info(f"❌ Failed: {stats['failed_files']}")
        canvas.info(f"⏭️ Skipped: {stats['skipped_files']}")
        canvas.info(f"🎯 Cache hits: {stats['cache_hits']}")
        canvas.info(f"📦 Chunks created: {stats['chunks_created']}")
        
        if stats['errors']:
            canvas.info(f"⚠️ Errors encountered: {len(stats['errors'])}")
            for error in stats['errors'][:5]:  # Show first 5 errors
                canvas.warning(f"  - {error}")
        
        canvas.info("=" * 50)
    
    def invalidate_cache(self, file_path: Optional[Path] = None):
        """Invalidate cache entries to force reprocessing"""
        if file_path:
            self.cache.invalidate_file(file_path)
            canvas.info(f"Cache invalidated for {file_path}")
        else:
            self.cache._cache.clear()
            self.cache._save_cache()
            canvas.info("All cache entries invalidated")

# Utility functions for easy usage
def create_knowledge_ingestor(
    knowledge_space: str = "default",
    budget_manager: Optional[BudgetManagerAgent] = None
) -> EnhancedKnowledgeIngestorAgent:
    """Create a configured knowledge ingestor"""
    return EnhancedKnowledgeIngestorAgent(
        budget_manager=budget_manager or BudgetManagerAgent(),
        knowledge_space=knowledge_space
    )

def batch_ingest_documentation(
    docs_path: Path,
    knowledge_space: str = "default",
    document_type: str = "documentation",
    force_refresh: bool = False
) -> Tuple[bool, Dict]:
    """Convenience function for batch ingestion"""
    ingestor = create_knowledge_ingestor(knowledge_space)
    
    return ingestor.execute(
        document_path=docs_path,
        document_type=document_type,
        force_refresh=force_refresh,
        recursive=True
    )