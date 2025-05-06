#!/usr/bin/env python3
"""
Knowledge Base Integration Demo Script

This script demonstrates the end-to-end flow of:
1. Initializing the database and embedding model
2. Ingesting documentation files into the knowledge base
3. Retrieving knowledge from the KB using semantic search
4. Displaying the retrieved content in a format suitable for LLM consumption
"""

import sys
import json
import argparse
from pathlib import Path
import traceback

from i2c.bootstrap import initialize_environment
initialize_environment()
# Initialize LLM models early

import builtins


# Import database utilities
try:
    from i2c.db_utils import (
        initialize_db,
        get_db_connection,
        query_context_filtered,
        TABLE_KNOWLEDGE_BASE,
        list_knowledge_spaces,
        SCHEMA_KNOWLEDGE_BASE_V2
    )
except ImportError as e:
    print(f"Error importing db_utils: {e}")
    sys.exit(1)

# Import embedding utilities
try:
    from agno.embedder.sentence_transformer import SentenceTransformerEmbedder
    from i2c.agents.modification_team.context_utils import generate_embedding
except ImportError as e:
    print(f"Error importing embedding utilities: {e}")
    sys.exit(1)

# Import knowledge base components if available
try:
    from i2c.agents.knowledge.base import PDFDocumentationKnowledgeBase, EnhancedLanceDb
    KB_BASE_AVAILABLE = True
except ImportError:
    print("agents.knowledge.base not available - using simplified knowledge ingestion")
    KB_BASE_AVAILABLE = False

# Simple logging utilities
class Logger:
    @staticmethod
    def info(msg):
        print(f"ℹ️ INFO: {msg}")
    
    @staticmethod
    def success(msg):
        print(f"✅ SUCCESS: {msg}")
    
    @staticmethod
    def warning(msg):
        print(f"⚠️ WARNING: {msg}")
    
    @staticmethod
    def error(msg):
        print(f"❌ ERROR: {msg}")


def setup_argparse():
    """Set up command line argument parsing"""
    parser = argparse.ArgumentParser(description='Knowledge Base Integration Demo')
    
    parser.add_argument('--file', type=str, help='Path to a documentation file to ingest')
    parser.add_argument('--folder', type=str, help='Path to a folder of documentation to ingest')
    parser.add_argument('--project', type=str, required=True, help='Project name for knowledge space')
    parser.add_argument('--doc-type', type=str, default='documentation', help='Document type')
    parser.add_argument('--framework', type=str, default='', help='Framework or library name (optional)')
    parser.add_argument('--version', type=str, default='', help='Version (optional)')
    parser.add_argument('--query', type=str, help='Query to search after ingestion (optional)')
    parser.add_argument('--recursive', action='store_true', help='Process folder recursively')
    
    return parser.parse_args()


def init_database():
    """Initialize the database connection"""
    Logger.info("Initializing database connection...")
    db = initialize_db()
    if db is None:
        Logger.error("Failed to initialize database. Exiting.")
        sys.exit(1)
    Logger.success("Database initialized successfully")
    return db


def init_embedding_model():
    """Initialize the embedding model"""
    Logger.info("Initializing embedding model...")
    try:
        embed_model = SentenceTransformerEmbedder()
        Logger.success("Embedding model initialized successfully")
        return embed_model
    except Exception as e:
        Logger.error(f"Failed to initialize embedding model: {e}")
        sys.exit(1)


def process_file(file_path, document_type, knowledge_space, embed_model, metadata=None):
    """Process a single file and ingest it into the knowledge base"""
    Logger.info(f"Processing file: {file_path}")
    
    if not file_path.exists():
        Logger.error(f"File not found: {file_path}")
        return False
    
    if not file_path.is_file():
        Logger.error(f"Not a file: {file_path}")
        return False
    
    try:
        # Handle different file types
        if file_path.suffix.lower() == '.pdf':
            success = ingest_pdf_file(file_path, document_type, knowledge_space, embed_model, metadata)
        else:
            # Handle text-based files (markdown, txt, etc)
            success = ingest_text_file(file_path, document_type, knowledge_space, embed_model, metadata)
        
        if success:
            Logger.success(f"Successfully ingested: {file_path}")
            return True
        else:
            Logger.error(f"Failed to ingest: {file_path}")
            return False
            
    except Exception as e:
        Logger.error(f"Error processing file {file_path}: {e}")
        traceback.print_exc()
        return False


def ingest_pdf_file(file_path, document_type, knowledge_space, embed_model, metadata=None):
    """Ingest a PDF file into the knowledge base"""
    from i2c.db_utils import get_db_connection, add_or_update_chunks
    import hashlib
    from datetime import datetime
    
    # Create combined metadata
    metadata = metadata or {}
    
    # Calculate file hash for deduplication
    with open(file_path, 'rb') as f:
        content = f.read()
        file_hash = hashlib.sha256(content).hexdigest()
    
    # Create vector DB connection for the KB class
    db = get_db_connection()
    if not db:
        Logger.error("Failed to connect to database")
        return False
    
    # If we have the PDFDocumentationKnowledgeBase available, use it
    if KB_BASE_AVAILABLE:
        try:
            # Create a vector DB for the knowledge base
            vector_db = EnhancedLanceDb(
                knowledge_space=knowledge_space,
                embedder=embed_model
            )
            
            # Create the PDF knowledge base
            pdf_kb = PDFDocumentationKnowledgeBase(
                knowledge_space=knowledge_space,
                vector_db=vector_db
            )
            
            # Process the PDF document
            success = pdf_kb.load_document(
                path=file_path,
                document_type=document_type,
                metadata=metadata
            )
            
            return success
            
        except Exception as e:
            Logger.error(f"Error using PDFDocumentationKnowledgeBase: {e}")
            # Fall back to manual PDF processing
    
    # Manual PDF processing if KB_BASE_AVAILABLE is False or previous attempt failed
    try:
        # Use Agno's PDFReader to extract text from the PDF
        from agno.document.reader.pdf_reader import PDFReader
        
        reader = PDFReader(chunk=True)
        documents = reader.read(str(file_path))
        
        # Turn documents into embedding-ready chunks
        chunks = []
        for i, doc in enumerate(documents):
            text = doc.content if hasattr(doc, 'content') else str(doc)
            vector = embed_model.get_embedding(text)
            
            # Create chunk
            chunk = {
                "source": str(file_path),
                "content": text,
                "vector": vector,
                "category": document_type,
                "last_updated": datetime.now().isoformat(),
                "knowledge_space": knowledge_space,
                "document_type": document_type,
                "framework": metadata.get("framework", ""),
                "version": metadata.get("version", ""),
                "parent_doc_id": "",
                "chunk_type": f"chunk_{i}",
                "source_hash": file_hash,
                "metadata_json": json.dumps(metadata),
            }
            chunks.append(chunk)
        
        # Add chunks to database
        add_or_update_chunks(
            db=db,
            table_name=TABLE_KNOWLEDGE_BASE,
            schema=SCHEMA_KNOWLEDGE_BASE_V2,
            identifier_field="source",
            identifier_value=str(file_path),
            chunks=chunks
        )
        
        Logger.success(f"Added {len(chunks)} chunks for {file_path}")
        return True
        
    except Exception as e:
        Logger.error(f"Error in manual PDF processing: {e}")
        traceback.print_exc()
        return False


def ingest_text_file(file_path, document_type, knowledge_space, embed_model, metadata=None):
    """Ingest a text file into the knowledge base"""
    from i2c.db_utils import get_db_connection, add_or_update_chunks
    import hashlib
    from datetime import datetime
    
    # Calculate file hash for deduplication
    with open(file_path, 'rb') as f:
        content = f.read()
        file_hash = hashlib.sha256(content).hexdigest()
    
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            file_content = f.read()
        
        # Create vector for the content
        vector = embed_model.get_embedding(file_content)
        
        # Create chunk
        chunks = [{
            "source": str(file_path),
            "content": file_content,
            "vector": vector,
            "category": document_type,
            "last_updated": datetime.now().isoformat(),
            "knowledge_space": knowledge_space,
            "document_type": document_type,
            "framework": metadata.get("framework", ""),
            "version": metadata.get("version", ""),
            "parent_doc_id": "",
            "chunk_type": "text",
            "source_hash": file_hash,
            "metadata_json": json.dumps(metadata or {}),
        }]
        
        # Get database connection
        db = get_db_connection()
        if not db:
            Logger.error("Failed to connect to database")
            return False
        
        # Add to database
        add_or_update_chunks(
            db=db,
            table_name=TABLE_KNOWLEDGE_BASE,
            schema=SCHEMA_KNOWLEDGE_BASE_V2,
            identifier_field="source",
            identifier_value=str(file_path),
            chunks=chunks
        )
        
        Logger.success(f"Added text file {file_path} to knowledge base")
        return True
        
    except Exception as e:
        Logger.error(f"Error ingesting text file: {e}")
        traceback.print_exc()
        return False


def process_folder(folder_path, document_type, knowledge_space, embed_model, metadata=None, recursive=True):
    """Process all files in a folder"""
    Logger.info(f"Processing folder: {folder_path}")
    
    if not folder_path.exists():
        Logger.error(f"Folder not found: {folder_path}")
        return False
    
    if not folder_path.is_dir():
        Logger.error(f"Not a folder: {folder_path}")
        return False
    
    # Get files to process
    pattern = "**/*" if recursive else "*"
    files_to_process = [f for f in folder_path.glob(pattern) if f.is_file()]
    
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
    
    Logger.info(f"Found {len(files_to_process)} files to process")
    
    success_count = 0
    for file_path in files_to_process:
        if process_file(file_path, document_type, knowledge_space, embed_model, metadata):
            success_count += 1
    
    Logger.success(f"Successfully processed {success_count}/{len(files_to_process)} files")
    return success_count > 0


def query_knowledge_base(db, knowledge_space, query_text, embed_model, limit=5):
    """Query the knowledge base for relevant information"""
    Logger.info(f"Querying knowledge base with: '{query_text}'")
    
    # Generate embedding for the query
    query_vector = generate_embedding(query_text)
    if query_vector is None:
        Logger.error("Failed to generate query embedding")
        return None
    
    # Query the database with knowledge space filter
    results = query_context_filtered(
        db=db,
        table_name=TABLE_KNOWLEDGE_BASE,
        query_vector=query_vector,
        filters={'knowledge_space': knowledge_space},
        limit=limit
    )
    
    if results is None or results.empty:
        Logger.warning("No relevant results found")
        return None
    
    # Print results
    Logger.success(f"Found {len(results)} relevant results:")
    print("-" * 60)
    
    formatted_results = []
    for idx, row in results.iterrows():
        print(f"\n{idx + 1}. Source: {Path(row['source']).name}")
        
        # Print metadata if available
        if 'document_type' in row:
            print(f"   Type: {row['document_type']}")
        if 'framework' in row and row['framework']:
            print(f"   Framework: {row['framework']}")
        if 'version' in row and row['version']:
            print(f"   Version: {row['version']}")
        
        # Print content preview
        content = row['content']
        preview_length = 200
        content_preview = content[:preview_length] + "..." if len(content) > preview_length else content
        print(f"\n   Content Preview:")
        print(f"   {content_preview}")
        print("-" * 60)
        
        # Add to formatted results
        formatted_results.append({
            "source": row['source'],
            "content": content,
            "type": row.get('document_type', 'unknown'),
            "framework": row.get('framework', ''),
            "version": row.get('version', '')
        })
    
    return formatted_results


def format_for_llm_consumption(results):
    """Format results in a way that's suitable for LLM consumption"""
    if not results:
        return "No relevant knowledge found."
    
    formatted = ["# Retrieved Knowledge:"]
    for i, result in enumerate(results, 1):
        formatted.append(f"\n## Knowledge Item {i}")
        formatted.append(f"Source: {Path(result['source']).name}")
        
        # Add metadata
        if result.get('framework'):
            formatted.append(f"Framework: {result['framework']}")
        if result.get('version'):
            formatted.append(f"Version: {result['version']}")
        if result.get('type'):
            formatted.append(f"Type: {result['type']}")
        
        # Add content
        formatted.append(f"\n{result['content']}\n")
        formatted.append("-" * 40)
    
    return "\n".join(formatted)


def list_knowledge_spaces(db):
    """List all available knowledge spaces in the database"""
    print("\n--- Knowledge Spaces in Database ---")
    spaces = list_knowledge_spaces(db)
    if not spaces:
        print("No knowledge spaces found.")
    else:
        for i, space in enumerate(spaces, 1):
            print(f"{i}. {space}")
    print()


def run_demo():
    """Main demo function"""
    args = setup_argparse()
    
    # Initialize components
    db = init_database()
    embed_model = init_embedding_model()
    
    # List existing knowledge spaces
    list_knowledge_spaces(db)
    
    # Format knowledge space name
    knowledge_space = f"project_{args.project}"
    Logger.info(f"Using knowledge space: {knowledge_space}")
    
    # Prepare metadata
    metadata = {
        'framework': args.framework if args.framework else None,
        'version': args.version if args.version else None,
        'project': args.project
    }
    
    # Process file or folder if provided
    if args.file:
        file_path = Path(args.file).expanduser().resolve()
        process_file(file_path, args.doc_type, knowledge_space, embed_model, metadata)
    
    if args.folder:
        folder_path = Path(args.folder).expanduser().resolve()
        process_folder(folder_path, args.doc_type, knowledge_space, embed_model, metadata, args.recursive)
    
    # Query if requested
    if args.query:
        results = query_knowledge_base(db, knowledge_space, args.query, embed_model)
        if results:
            print("\n=== Results Formatted for LLM Consumption ===")
            formatted = format_for_llm_consumption(results)
            print(formatted)
    
    Logger.success("Demo completed successfully")


if __name__ == "__main__":
    try:
        run_demo()
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"Error running demo: {e}")
        traceback.print_exc()