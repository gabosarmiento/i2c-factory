# workflow/knowledge_management.py
from pathlib import Path
from typing import List, Dict, Any
import asyncio
from agents.knowledge.knowledge_ingestor import KnowledgeIngestorAgent
from cli.controller import canvas
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class KnowledgeUpdateHandler(FileSystemEventHandler):
    """Handles file system events for knowledge updates"""
    
    def __init__(self, knowledge_ingestor: KnowledgeIngestorAgent):
        self.knowledge_ingestor = knowledge_ingestor
        self.pending_updates = asyncio.Queue()
    
    def on_created(self, event):
        if not event.is_directory:
            self.pending_updates.put_nowait(Path(event.src_path))
    
    def on_modified(self, event):
        if not event.is_directory:
            self.pending_updates.put_nowait(Path(event.src_path))

class KnowledgeManagementWorkflow:
    """Manages knowledge base updates and maintenance"""
    
    def __init__(
        self,
        knowledge_ingestor: KnowledgeIngestorAgent,
        watch_paths: List[Path]
    ):
        self.knowledge_ingestor = knowledge_ingestor
        self.watch_paths = watch_paths
        self.observer = Observer()
        self.update_handler = KnowledgeUpdateHandler(knowledge_ingestor)
    
    async def start_monitoring(self):
        """Start monitoring for documentation updates"""
        for path in self.watch_paths:
            self.observer.schedule(self.update_handler, str(path), recursive=True)
        
        self.observer.start()
        
        # Process updates
        while True:
            try:
                file_path = await self.update_handler.pending_updates.get()
                try:
                    await self.process_update(file_path)
                except ModuleNotFoundError as e:
                    canvas.error(
                        f"Documentation update for {file_path} failed: {e}. "
                        "Make sure you’ve run `poetry add protobuf` and restarted your process."
                    )
                except Exception as e:
                    canvas.error(f"Failed to process update for {file_path}: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                canvas.error(f"Unexpected error in monitoring loop: {e}")
                # avoid tight busy‐loop on repeated error
                await asyncio.sleep(1)
    
    async def process_update(self, file_path: Path):
        """Process a documentation update"""
        # Detect document type
        document_type = self._detect_document_type(file_path)
        
        # Extract metadata
        metadata = self._extract_metadata(file_path)
        
        # Ingest document
        success, result = self.knowledge_ingestor.execute(
            document_path=file_path,
            document_type=document_type,
            metadata=metadata
        )
        
        if success:
            print(f"Successfully updated: {file_path}")
        else:
            print(f"Failed to update: {file_path} - {result.get('error')}")