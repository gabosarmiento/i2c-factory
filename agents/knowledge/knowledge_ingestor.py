# Enhancements to agents/knowledge/knowledge_ingestor.py
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import hashlib
from datetime import datetime

from agno.embedder.sentence_transformer import SentenceTransformerEmbedder
from agents.budget_manager import BudgetManagerAgent
from agents.reflective.context_aware_operator import ContextAwareOperator
from agents.knowledge.base import KnowledgeBaseFactory, EnhancedLanceDb
from cli.controller import canvas

class KnowledgeIngestorAgent(ContextAwareOperator):
    """Enhanced documentation ingestion with file/folder support and deduplication"""
    
    def __init__(
        self,
        budget_manager: BudgetManagerAgent,
        knowledge_space: str = "default",
        embed_model=None,
        **kwargs
    ):
        super().__init__(
            budget_manager=budget_manager,
            operation_type="knowledge_ingestion",
            max_reasoning_steps=3,
            default_model_tier="middle"
        )
        self.knowledge_space = knowledge_space
        # Use SentenceTransformerEmbedder from Agno
        self.embed_model = embed_model or SentenceTransformerEmbedder()
        self._processed_hashes = set()  # Track processed file hashes
        
    def execute(
        self,
        document_path: Path,
        document_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        is_refresh: bool = False,
        recursive: bool = True,
        selected_files: Optional[List[Path]] = None
    ) -> Tuple[bool, Dict]:
        """
        Process and ingest documentation with improved handling for files and folders.
        
        Args:
            document_path: Path to file or directory to process
            document_type: Type of documentation (e.g., 'api_documentation')
            metadata: Additional metadata for the document(s)
            is_refresh: Whether to force refresh/update existing documents
            recursive: For directories, whether to process recursively
            selected_files: For directories, optionally specify only certain files
            
        Returns:
            Tuple of (success, result_dict)
        """
        phase_id = "document_ingestion"
        self.cost_tracker.start_phase(
            phase_id,
            f"Ingest document(s): {document_path.name}",
            model_id="knowledge_ingestor"
        )

        try:
            # Validate the path
            if not document_path.exists():
                raise FileNotFoundError(f"Document not found: {document_path}")
            
            # Initialize result statistics
            result_stats = {
                "processed_files": 0,
                "successful_files": 0,
                "failed_files": 0,
                "skipped_files": 0,
                "chunks_created": 0,
                "errors": []
            }
            
            # Process directory or single file
            if document_path.is_dir():
                self._process_directory(
                    document_path, 
                    document_type, 
                    metadata,
                    result_stats,
                    is_refresh,
                    recursive,
                    selected_files
                )
            else:
                self._process_file(
                    document_path, 
                    document_type, 
                    metadata,
                    result_stats,
                    is_refresh
                )
            
            success = result_stats["failed_files"] == 0
            self.cost_tracker.end_phase(
                success=success,
                result=result_stats
            )
            
            return success, result_stats
            
        except Exception as e:
            canvas.error(f"Error in document ingestion: {e}")
            self.cost_tracker.end_phase(success=False, feedback=str(e))
            return False, {
                "error": str(e),
                "document_path": str(document_path)
            }
            
    def _process_directory(
        self,
        directory_path: Path,
        document_type: str,
        metadata: Optional[Dict[str, Any]],
        result_stats: Dict[str, Any],
        is_refresh: bool,
        recursive: bool,
        selected_files: Optional[List[Path]]
    ) -> None:
        """Process all files in a directory"""
        
        # Get files to process
        if selected_files:
            # Filter to only selected files within this directory
            files_to_process = [
                f for f in selected_files 
                if f.exists() and f.is_file() and directory_path in f.parents
            ]
        else:
            # Get all files in directory
            pattern = "**/*" if recursive else "*"
            files_to_process = [f for f in directory_path.glob(pattern) if f.is_file()]
            
            # Skip hidden files and directories
            files_to_process = [
                f for f in files_to_process 
                if not any(part.startswith('.') for part in f.parts)
            ]
            
            # Skip common directories to ignore
            files_to_process = [
                f for f in files_to_process 
                if not any(ignore in f.parts for ignore in ["__pycache__", "node_modules", ".git", ".venv"])
            ]
        
        canvas.info(f"Processing {len(files_to_process)} files in {directory_path}")
        
        # Process each file
        for file_path in files_to_process:
            try:
                result_stats["processed_files"] += 1
                self._process_file(file_path, document_type, metadata, result_stats, is_refresh)
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
        is_refresh: bool
    ) -> None:
        """Process a single file for knowledge base ingestion."""
        from cli.controller import canvas
        from db_utils import get_db_connection, add_knowledge_chunks
        import json
        import hashlib
        from datetime import datetime

        # Get file hash for deduplication
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            file_hash = hashlib.sha256(content).hexdigest()
        except Exception as e:
            canvas.error(f"Error reading file {file_path}: {e}")
            result_stats["failed_files"] += 1
            result_stats["errors"].append(f"Error reading file: {e}")
            return

        # Budget check
        if (
            self.budget_manager
            and not self.budget_manager.request_approval(
                description=f"Ingest file: {file_path.name}",
                prompt=f"Process {file_path.name} for knowledge base",
                model_id="knowledge_ingestor",
            )
        ):
            canvas.warning(f"Budget approval denied for file: {file_path}")
            result_stats["skipped_files"] += 1
            return

        try:
            # Handle PDFs specially
            if file_path.suffix.lower() == ".pdf":
                from agno.document.reader.pdf_reader import PDFReader

                reader = PDFReader(chunk=True)
                documents = reader.read(str(file_path))
            else:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                from agno.document.base import Document

                documents = [Document(content=content, name=file_path.name)]

            # Turn documents into embedding-ready chunks
            chunks = []
            for i, doc in enumerate(documents):
                text = doc.content if hasattr(doc, "content") else str(doc)
                vector = self.embed_model.get_embedding(text)

                chunk = {
                    "source": str(file_path),
                    "content": text,
                    "vector": vector,
                    "category": document_type,
                    "last_updated": datetime.now().isoformat(),
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

            # Save to database
            db = get_db_connection()
            if not db:
                canvas.error("Database connection failed")
                result_stats["failed_files"] += 1
                result_stats["errors"].append("Database connection failed")
                return

            success = add_knowledge_chunks(db, chunks, self.knowledge_space)
            if success:
                canvas.success(f"Successfully ingested: {file_path}")
                result_stats["successful_files"] += 1
                result_stats["chunks_created"] += len(chunks)
            else:
                canvas.error(f"Failed to ingest: {file_path}")
                result_stats["failed_files"] += 1
                result_stats["errors"].append("Failed to add chunks to database")

        except Exception as e:
            canvas.error(f"Error processing file {file_path}: {e}")
            result_stats["failed_files"] += 1
            result_stats["errors"].append(f"Error processing file: {e}")

    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate hash for file content for deduplication"""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return hasher.hexdigest()