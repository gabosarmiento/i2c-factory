#!/usr/bin/env python3
"""
Simple Knowledge Base Demo Script - Focuses only on knowledge_base table
"""

import os
import sys
from pathlib import Path
import traceback

# Add project root to path
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))

# Import necessary components
import lancedb
import pyarrow as pa
from sentence_transformers import SentenceTransformer
import pypdf
import numpy as np
import pandas as pd
from datetime import datetime
import hashlib
import json
import argparse

# Configure constants
DB_PATH = "./data/lancedb"
TABLE_KNOWLEDGE_BASE = "knowledge_base"
VECTOR_DIMENSION = 384  # For 'all-MiniLM-L6-v2'

# Define schema for knowledge base
SCHEMA_KNOWLEDGE_BASE_V2 = pa.schema([
    pa.field("source", pa.string()),
    pa.field("content", pa.string()),
    pa.field("vector", pa.list_(pa.float32(), list_size=VECTOR_DIMENSION)),
    pa.field("category", pa.string()),
    pa.field("last_updated", pa.string()),
    pa.field("knowledge_space", pa.string()),
    pa.field("document_type", pa.string()),
    pa.field("framework", pa.string()),
    pa.field("version", pa.string()),
    pa.field("parent_doc_id", pa.string()),
    pa.field("chunk_type", pa.string()),
    pa.field("source_hash", pa.string()),
    pa.field("metadata_json", pa.string()),
])

# Initialize embedding model
embedder = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text):
    """Get embeddings for text"""
    emb = embedder.encode(text)
    if isinstance(emb, np.ndarray):
        return emb.tolist()
    return list(emb)

def get_db_connection():
    """Connect to LanceDB"""
    db_uri = Path(DB_PATH)
    db_uri.mkdir(parents=True, exist_ok=True)
    try:
        return lancedb.connect(str(db_uri))
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def get_or_create_kb_table(db):
    """Get or create the knowledge base table"""
    try:
        if TABLE_KNOWLEDGE_BASE in db.table_names():
            return db.open_table(TABLE_KNOWLEDGE_BASE)
        else:
            print(f"Creating table '{TABLE_KNOWLEDGE_BASE}'")
            return db.create_table(TABLE_KNOWLEDGE_BASE, schema=SCHEMA_KNOWLEDGE_BASE_V2)
    except Exception as e:
        print(f"Error creating/opening table: {e}")
        return None

def process_pdf(file_path, document_type, knowledge_space, metadata=None):
    """Process a PDF file into knowledge chunks"""
    print(f"Processing PDF: {file_path}")
    
    # Calculate file hash
    with open(file_path, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    
    # Read PDF
    pdf_reader = pypdf.PdfReader(open(file_path, 'rb'))
    num_pages = len(pdf_reader.pages)
    
    print(f"PDF has {num_pages} pages")
    
    # Process pages
    chunks = []
    for i in range(num_pages):
        try:
            if i % 10 == 0:
                print(f"Processing page {i+1}/{num_pages}...")
            
            page = pdf_reader.pages[i]
            text = page.extract_text()
            
            # Skip empty pages
            if not text or len(text.strip()) < 10:
                continue
            
            # Create vector
            vector = get_embedding(text)
            
            # Create chunk
            chunk = {
                "source": str(file_path),
                "content": text,
                "vector": vector,
                "category": document_type,
                "last_updated": datetime.now().isoformat(),
                "knowledge_space": knowledge_space,
                "document_type": document_type,
                "framework": metadata.get("framework", "") if metadata else "",
                "version": metadata.get("version", "") if metadata else "",
                "parent_doc_id": "",
                "chunk_type": f"page_{i+1}",
                "source_hash": file_hash,
                "metadata_json": json.dumps(metadata or {}),
            }
            chunks.append(chunk)
        except Exception as e:
            print(f"Error processing page {i+1}: {e}")
    
    return chunks

def add_chunks_to_db(db, chunks, file_path):
    """Add chunks to database"""
    try:
        # Get table
        table = get_or_create_kb_table(db)
        if not table:
            return False
        
        # Delete existing entries for this source
        try:
            escaped_path = str(file_path).replace("'", r"\'")

            # Now safely build your delete call
            table.delete(f"source = '{escaped_path}'")
        except Exception:
            pass
        
        # Add new chunks
        if chunks:
            table.add(chunks)
            print(f"Added {len(chunks)} chunks to knowledge base")
            return True
        return False
    except Exception as e:
        print(f"Error adding chunks to database: {e}")
        return False

def query_knowledge_base(db, knowledge_space, query_text, limit=5):
    """Query the knowledge base"""
    try:
        # Get table
        table = get_or_create_kb_table(db)
        if not table:
            return None
        
        # Generate query vector
        query_vector = get_embedding(query_text)
        
        # Search with filter
        results = table.search(query_vector)\
            .where(f"knowledge_space = '{knowledge_space}'")\
            .select(["source", "content", "document_type", "framework", "version", "chunk_type"])\
            .limit(limit)\
            .to_pandas()
        
        return results
    except Exception as e:
        print(f"Error querying knowledge base: {e}")
        return None

def main():
    """Main function"""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Knowledge Base Demo")
    parser.add_argument("--project", required=True, help="Project name for knowledge space")
    parser.add_argument("--file", help="PDF file to process")
    parser.add_argument("--doc-type", default="documentation", help="Document type")
    parser.add_argument("--framework", default="", help="Framework name")
    parser.add_argument("--version", default="", help="Version")
    parser.add_argument("--query", help="Query to search")
    args = parser.parse_args()
    
    # Connect to database
    db = get_db_connection()
    if not db:
        print("Failed to connect to database")
        return
    
    # Format knowledge space
    knowledge_space = f"project_{args.project}"
    print(f"Using knowledge space: {knowledge_space}")
    
    # Process file if provided
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return
        
        # Prepare metadata
        metadata = {
            "framework": args.framework,
            "version": args.version,
            "project": args.project
        }
        
        # Process PDF
        if file_path.suffix.lower() == '.pdf':
            chunks = process_pdf(file_path, args.doc_type, knowledge_space, metadata)
            success = add_chunks_to_db(db, chunks, file_path)
            if success:
                print(f"Successfully processed {file_path}")
            else:
                print(f"Failed to process {file_path}")
        else:
            print(f"Unsupported file type: {file_path.suffix}")
    
    # Query if requested
    if args.query:
        print(f"\nQuerying knowledge base with: '{args.query}'")
        results = query_knowledge_base(db, knowledge_space, args.query)
        
        if results is None or results.empty:
            print("No relevant results found")
            return
        
        print(f"\nFound {len(results)} relevant results:")
        print("-" * 60)
        
        for idx, row in results.iterrows():
            print(f"\n{idx + 1}. Source: {Path(row['source']).name}")
            
            # Print metadata
            if 'document_type' in row:
                print(f"   Type: {row['document_type']}")
            if 'framework' in row and row['framework']:
                print(f"   Framework: {row['framework']}")
            if 'version' in row and row['version']:
                print(f"   Version: {row['version']}")
            if 'chunk_type' in row:
                print(f"   Chunk: {row['chunk_type']}")
            
            # Print content preview
            content = row['content']
            preview_length = 200
            content_preview = content[:preview_length] + "..." if len(content) > preview_length else content
            print(f"\n   Content Preview:")
            print(f"   {content_preview}")
            print("-" * 60)
        
        # Format for LLM consumption
        print("\n=== Formatted for LLM Consumption ===")
        formatted = ["# Retrieved Knowledge:"]
        for idx, row in results.iterrows():
            formatted.append(f"\n## Knowledge Item {idx+1}")
            formatted.append(f"Source: {Path(row['source']).name}")
            if 'document_type' in row:
                formatted.append(f"Type: {row['document_type']}")
            if 'chunk_type' in row:
                formatted.append(f"Chunk: {row['chunk_type']}")
            
            formatted.append(f"\n{row['content']}\n")
            formatted.append("-" * 40)
        
        print("\n".join(formatted))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        
# try with python simple_kb_demo.py --project idea-to-code-factory --file /Users/caroco/Gabo-Dev/idea_to_code_factory/tests/data/docs/doc-openai.pdf --doc-type tutorial --query "Explain at least two key differences between the o-series 'reasoning' models and GPT series models in terms of their strengths, typical use cases, and cost/latency trade-offs."
