# agents/knowledge/base.py
from agno.agent import AgentKnowledge
from agno.document.base import Document
from agno.vectordb.lancedb import LanceDb
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.knowledge.website import WebsiteKnowledgeBase
from agno.knowledge.combined import CombinedKnowledgeBase
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import hashlib
import json


class EnhancedLanceDb(LanceDb):
    """Extended LanceDB with version filtering and knowledge spaces"""
    
    def __init__(self, knowledge_space: str = "default", **kwargs):
        # LanceDb requires a table_name
        if 'table_name' not in kwargs:
            kwargs['table_name'] = f"knowledge_{knowledge_space}"
        
        super().__init__(**kwargs)
        self.knowledge_space = knowledge_space
    
    def search(self, query: str, limit: int = 5, where: Optional[str] = None, **kwargs) -> Any:
        """Enhanced search with knowledge space filtering"""
        # build the filter string only once, using the instance var
    
        space_filter = f"knowledge_space = '{self.knowledge_space}'"

        if where:
            combined_filter = f"{space_filter} AND ({where})"
        else:
            combined_filter = space_filter
        
        # Use parent class search with combined filter
        return super().search(query=query, limit=limit, where=combined_filter, **kwargs)

class DocumentationKnowledgeBase(AgentKnowledge):
    """Base class for documentation knowledge bases with enhanced metadata"""
    class Config:
        extra = "allow"
        
    def __init__(
        self,
        knowledge_space: str,
        vector_db: EnhancedLanceDb,
        budget_manager=None,
        **kwargs
    ):
        super().__init__(vector_db=vector_db, **kwargs)
        self.knowledge_space = knowledge_space
        self.budget_manager = budget_manager
        self._loaded_documents = {}
        
        
        
    def load_document(
        self,
        path: Path,
        document_type: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Load a document with version tracking and deduplication"""
        if not path.exists():
            return False
            
        # Check budget before processing
        if self.budget_manager:
            description  = f"Document ingestion: {path.name}"
            prompt_text  = f"Ingest and chunk {path.name} into KB"
            model_id     = "knowledge_ingestor"           
            
            if not self.budget_manager.request_approval(
                description,
                prompt_text,
                model_id
            ):
                return False
        
        # Calculate document hash for deduplication
        with open(path, 'rb') as f:
            content = f.read()
            doc_hash = hashlib.sha256(content).hexdigest()
        
        # Process document based on type
        documents = self._process_document(path, document_type, metadata or {})
        
        # Ensure we have valid documents
        if not documents:
            return False
        
        # Convert documents to data format expected by LanceDB
        lance_data = []
        for doc in documents:
            if not hasattr(doc, 'content'):
                continue
                
            # Generate embedding for content
            vector = self.vector_db.embedder.get_embedding(doc.content)
            
            # Create record for LanceDB
            # Create record matching the EXACT field names in SCHEMA_KNOWLEDGE_BASE
            record = {
                "source": str(path),  # This must match the schema field name exactly
                "content": doc.content,
                "vector": vector,
                "category": metadata.get('category', 'document'),
                "last_updated": datetime.now().isoformat(),
                "knowledge_space": self.knowledge_space,
                "document_type": document_type,
                "framework": metadata.get('framework', ''),
                "version": metadata.get('version', ''),
                "parent_doc_id": metadata.get('parent_doc_id', ''),
                "chunk_type": metadata.get('chunk_type', 'content'),
                "source_hash": doc_hash,
                # Convert any additional metadata to JSON string
                "metadata_json": json.dumps(metadata or {})
            }
                            
            lance_data.append(record)
        
      
        # Add records to LanceDB
        try:
            # Use db_utils directly to get a fresh DB connection
            from i2c.db_utils import get_db_connection, add_or_update_chunks, TABLE_KNOWLEDGE_BASE, SCHEMA_KNOWLEDGE_BASE            
            
            db = get_db_connection()
            if not db:
                print("Error: Failed to get database connection")
                return False
                
            success = add_or_update_chunks(
                db=db,  # Use the new connection
                table_name=TABLE_KNOWLEDGE_BASE,
                schema=SCHEMA_KNOWLEDGE_BASE,
                identifier_field="source",
                identifier_value=str(path),
                chunks=lance_data
            )
            
            return success
        except Exception as e:
            print(f"Error adding documents to vector DB: {e}")
            return False
    
    def _process_document(
        self,
        path: Path,
        document_type: str,
        metadata: Dict[str, Any]
    ) -> List[Document]:
        """Process document based on type - to be overridden by subclasses"""
        raise NotImplementedError
    
    def _estimate_ingestion_cost(self, path: Path) -> float:
        """Estimate cost for document ingestion"""
        file_size = path.stat().st_size
        estimated_tokens = file_size / 4  # Rough estimate
        return estimated_tokens * 0.0001  # Rough cost estimate

class PDFDocumentationKnowledgeBase(DocumentationKnowledgeBase):
    """PDF Documentation knowledge base with enhanced features"""

    # Update in agents/knowledge/base.py - load_document method for PDFDocumentationKnowledgeBase
    def _process_document(
        self,
        path: Path,  # chemin vers le fichier
        document_type: str,
        metadata: Dict[str, Any]
    ) -> List[Document]:
        """Process PDF document"""
        # Use PDFKnowledgeBase for processing
        from agno.knowledge.pdf import PDFKnowledgeBase, PDFReader

        # Create temporary knowledge base for PDF processing
        temp_kb = PDFKnowledgeBase(
            path=str(path.parent),
            vector_db=self.vector_db,
            reader=PDFReader(chunk=True)
        )

        # Let PDFKnowledgeBase process the file
        temp_kb.load(recreate=False)

        # Get the documents and enhance them with our metadata
        documents = temp_kb.document_lists

        # Ensure we're working with Document objects, not just a list
        enhanced_docs = []
        for doc in documents:
            # Check if this is already a Document object
            if hasattr(doc, 'meta_data'):
                # Update existing metadata
                if doc.meta_data is None:
                    doc.meta_data = {}
                doc.meta_data.update(metadata or {})
                enhanced_docs.append(doc)
            else:
                # Create a new Document with the content and metadata
                from agno.document.base import Document
                enhanced_docs.append(Document(
                    content=str(doc),
                    meta_data=metadata or {}
                ))

        return enhanced_docs


class MarkdownDocumentationKnowledgeBase(DocumentationKnowledgeBase):
    """Markdown documentation knowledge base"""
    
    def _process_document(
        self,
        path: Path,
        document_type: str,
        metadata: Dict[str, Any]
    ) -> List[Document]:
        """Process markdown document"""
        if not path.exists() or path.suffix.lower() not in ['.md', '.markdown']:
            return []
            
        # Read markdown content
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split markdown by headers for better chunking
        chunks = self._split_markdown_by_headers(content)
        
        documents = []
        for i, chunk in enumerate(chunks):
            # Extract header if present
            lines = chunk.split('\n')
            header = ''
            content_start = 0
            
            if lines and lines[0].startswith('#'):
                header = lines[0]
                content_start = 1
            
            chunk_content = '\n'.join(lines[content_start:])
            
            doc = Document(
                name=f"{path.stem}_{i}",
                content=chunk_content,
                meta_data={
                    "source": str(path),
                    "chunk_index": i,
                    "header": header,
                    "file_type": "markdown"
                }
            )
            documents.append(doc)
        
        return documents
    
    def _split_markdown_by_headers(self, content: str) -> List[str]:
        """Split markdown content by headers"""
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        
        for line in lines:
            if line.startswith('#') and current_chunk:
                # Start new chunk at header
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
            else:
                current_chunk.append(line)
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks

class HTMLDocumentationKnowledgeBase(DocumentationKnowledgeBase):
    """HTML documentation knowledge base"""
    
    def _process_document(
        self,
        path: Path,
        document_type: str,
        metadata: Dict[str, Any]
    ) -> List[Document]:
        """Process HTML document"""
        if not path.exists() or path.suffix.lower() not in ['.html', '.htm']:
            return []
            
        # Read HTML content
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract text from HTML (basic implementation)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Create document
        doc = Document(
            name=path.stem,
            content=text,
            meta_data={
                "source": str(path),
                "file_type": "html"
            }
        )
        
        return [doc]

class WebDocumentationKnowledgeBase(DocumentationKnowledgeBase):
    """Web-based documentation knowledge base"""
    
    def __init__(
        self,
        knowledge_space: str,
        vector_db: EnhancedLanceDb,
        budget_manager=None,
        max_depth: int = 3,
        max_links: int = 10,
        **kwargs
    ):
        super().__init__(
            knowledge_space=knowledge_space,
            vector_db=vector_db,
            budget_manager=budget_manager,
            **kwargs
        )
        self.max_depth = max_depth
        self.max_links = max_links
        self._loaded_urls = {}
    
    def load_url(
        self,
        url: str,
        document_type: str = "web_documentation",
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Load documentation from a URL"""
        
        # Check budget before processing
        if self.budget_manager:
            estimated_cost = 0.05  # Estimate for web crawling
            if not self.budget_manager.request_approval(
                f"Web documentation ingestion: {url}",
                url,
                estimated_cost
            ):
                return False
        
        # Calculate URL hash for deduplication
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        
        # Check if URL already loaded
        if url_hash in self._loaded_urls:
            return True
        
        try:
            # Create temporary WebsiteKnowledgeBase for processing
            temp_kb = WebsiteKnowledgeBase(
                urls=[url],
                max_depth=self.max_depth,
                max_links=self.max_links,
                vector_db=self.vector_db
            )
            
            # Load the website content
            temp_kb.load(recreate=False)
            
            # Get the documents and enhance metadata
            documents = temp_kb.document_lists
            
            for doc in documents:
                enhanced_metadata = {
                    "knowledge_space": self.knowledge_space,
                    "document_type": document_type,
                    "source_url": url,
                    "url_hash": url_hash,
                    "ingested_at": datetime.now().isoformat(),
                    **(metadata or {})
                }
                
                if hasattr(doc, 'meta_data') and doc.meta_data:
                    doc.meta_data.update(enhanced_metadata)
                else:
                    doc.meta_data = enhanced_metadata
            
            # Load documents using parent class method
            self.load_documents(documents, upsert=True)
            self._loaded_urls[url_hash] = True
            
            return True
            
        except Exception as e:
            print(f"Error loading URL {url}: {e}")
            return False

class APIDocumentationKnowledgeBase(WebDocumentationKnowledgeBase):
    """Specialized knowledge base for API documentation"""
    
    def load_api_docs(
        self,
        base_url: str,
        version: str,
        endpoints: Optional[List[str]] = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Load API documentation with version tracking"""
        
        # Prepare URLs to crawl
        urls_to_load = []
        
        if endpoints:
            # Load specific endpoints
            for endpoint in endpoints:
                url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
                urls_to_load.append(url)
        else:
            # Load from base URL
            urls_to_load.append(base_url)
        
        # Enhanced metadata for API docs
        api_metadata = {
            "api_version": version,
            "api_base_url": base_url,
            "document_type": "api_documentation",
            **(metadata or {})
        }
        
        success = True
        for url in urls_to_load:
            if not self.load_url(url, "api_documentation", api_metadata):
                success = False
        
        return success

class FrameworkDocumentationKnowledgeBase(WebDocumentationKnowledgeBase):
    """Knowledge base for framework documentation (React, Django, etc.)"""
    
    def load_framework_docs(
        self,
        framework: str,
        version: str,
        docs_url: str,
        sections: Optional[List[str]] = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Load framework documentation with version tracking"""
        
        # Framework-specific metadata
        framework_metadata = {
            "framework": framework.lower(),
            "framework_version": version,
            "document_type": "framework_documentation",
            **(metadata or {})
        }
        
        if sections:
            # Load specific sections
            success = True
            for section in sections:
                section_url = f"{docs_url.rstrip('/')}/{section.lstrip('/')}"
                if not self.load_url(section_url, "framework_documentation", framework_metadata):
                    success = False
            return success
        else:
            # Load entire documentation site
            return self.load_url(docs_url, "framework_documentation", framework_metadata)

class MultiSourceKnowledgeBase(CombinedKnowledgeBase):
    """Knowledge base that combines multiple sources (files, URLs, etc.)"""
    
    def __init__(
        self,
        knowledge_space: str,
        vector_db: EnhancedLanceDb,
        budget_manager=None,
        **kwargs
    ):
        super().__init__(vector_db=vector_db, **kwargs)
        self.knowledge_space = knowledge_space
        self.budget_manager = budget_manager
        
        # Initialize different knowledge bases
        self.file_kb = DocumentationKnowledgeBase(
            knowledge_space=knowledge_space,
            vector_db=vector_db,
            budget_manager=budget_manager
        )
        
        self.web_kb = WebDocumentationKnowledgeBase(
            knowledge_space=knowledge_space,
            vector_db=vector_db,
            budget_manager=budget_manager
        )
        
        self.api_kb = APIDocumentationKnowledgeBase(
            knowledge_space=knowledge_space,
            vector_db=vector_db,
            budget_manager=budget_manager
        )
        
        # Add to combined sources
        self.knowledge_bases = [self.file_kb, self.web_kb, self.api_kb]

# Update the factory to include URL-based knowledge bases
class KnowledgeBaseFactory:
    """Factory for creating appropriate knowledge base types"""
    
    @staticmethod
    def create_from_source(
        source: Union[Path, str],
        knowledge_space: str,
        vector_db: EnhancedLanceDb,
        budget_manager=None,
        source_type: Optional[str] = None
    ) -> Optional[DocumentationKnowledgeBase]:
        """Create knowledge base from file path or URL"""
        
        if isinstance(source, Path) or (isinstance(source, str) and not source.startswith(('http://', 'https://'))):
            # File-based knowledge base
            file_path = Path(source)
            return KnowledgeBaseFactory.create_from_file(
                file_path, knowledge_space, vector_db, budget_manager
            )
        elif isinstance(source, str) and source.startswith(('http://', 'https://')):
            # URL-based knowledge base
            if source_type == "api":
                return APIDocumentationKnowledgeBase(
                    knowledge_space=knowledge_space,
                    vector_db=vector_db,
                    budget_manager=budget_manager
                )
            elif source_type == "framework":
                return FrameworkDocumentationKnowledgeBase(
                    knowledge_space=knowledge_space,
                    vector_db=vector_db,
                    budget_manager=budget_manager
                )
            else:
                return WebDocumentationKnowledgeBase(
                    knowledge_space=knowledge_space,
                    vector_db=vector_db,
                    budget_manager=budget_manager
                )
        
        return None
    
    @staticmethod
    def create_from_file(
        file_path: Path,
        knowledge_space: str,
        vector_db: EnhancedLanceDb,
        budget_manager=None
    ) -> Optional[DocumentationKnowledgeBase]:
        """Create knowledge base from file type"""
        
        suffix = file_path.suffix.lower()
        
        if suffix == '.pdf':
            return PDFDocumentationKnowledgeBase(
                knowledge_space=knowledge_space,
                vector_db=vector_db,
                budget_manager=budget_manager
            )
        elif suffix in ['.md', '.markdown']:
            return MarkdownDocumentationKnowledgeBase(
                knowledge_space=knowledge_space,
                vector_db=vector_db,
                budget_manager=budget_manager
            )
        elif suffix in ['.html', '.htm']:
            return HTMLDocumentationKnowledgeBase(
                knowledge_space=knowledge_space,
                vector_db=vector_db,
                budget_manager=budget_manager
            )
        else:
            return None

# Enhanced usage examples
def load_react_documentation(project_name: str):
    """Example: Load React documentation for a project"""
    
    vector_db = EnhancedLanceDb(
        knowledge_space=f"project_{project_name}",
        table_name=f"knowledge_{project_name}",
        uri="./data/lancedb"
    )
    
    framework_kb = FrameworkDocumentationKnowledgeBase(
        knowledge_space=f"project_{project_name}",
        vector_db=vector_db
    )
    
    # Load React documentation
    success = framework_kb.load_framework_docs(
        framework="react",
        version="18.2.0",
        docs_url="https://react.dev/reference/react",
        sections=["hooks", "components", "apis"],
        metadata={"project": project_name}
    )
    
    return framework_kb if success else None

def load_api_documentation(project_name: str, api_url: str, version: str):
    """Example: Load API documentation for a project"""
    
    vector_db = EnhancedLanceDb(
        knowledge_space=f"project_{project_name}",
        table_name=f"knowledge_{project_name}",
        uri="./data/lancedb"
    )
    
    api_kb = APIDocumentationKnowledgeBase(
        knowledge_space=f"project_{project_name}",
        vector_db=vector_db
    )
    
    # Load API documentation
    success = api_kb.load_api_docs(
        base_url=api_url,
        version=version,
        metadata={"project": project_name}
    )
    
    return api_kb if success else None

def create_multi_source_kb(project_name: str):
    """Example: Create a knowledge base that combines multiple sources"""
    
    vector_db = EnhancedLanceDb(
        knowledge_space=f"project_{project_name}",
        table_name=f"knowledge_{project_name}",
        uri="./data/lancedb"
    )
    
    multi_kb = MultiSourceKnowledgeBase(
        knowledge_space=f"project_{project_name}",
        vector_db=vector_db
    )
    
    # Load from various sources
    # 1. Local PDF file
    multi_kb.file_kb.load_document(
        Path("docs/architecture.pdf"),
        "pdf",
        {"category": "architecture"}
    )
    
    # 2. Web documentation
    multi_kb.web_kb.load_url(
        "https://docs.example.com/getting-started",
        metadata={"category": "tutorial"}
    )
    
    # 3. API documentation
    multi_kb.api_kb.load_api_docs(
        base_url="https://api.example.com/docs",
        version="v1",
        metadata={"category": "api"}
    )
    
    return multi_kb