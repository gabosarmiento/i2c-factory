#!/usr/bin/env python
# test_knowledge_management.py
"""
Test script for the Knowledge Management system.
This script tests the functionality of document ingestion, retrieval, and search.

Usage:
    python test_knowledge_management.py

The script will create temporary test files, ingest them into the knowledge base,
and then verify that they can be retrieved and searched properly.
"""

import os
import sys
import tempfile
import shutil
import hashlib
from pathlib import Path
import unittest
from datetime import datetime
import json
from i2c.bootstrap import initialize_environment
initialize_environment()
# Add the project root to the Python path if needed
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent  # Adjust this if needed
sys.path.append(str(project_root))

# Import knowledge management components
try:
    # Import Agno components first
    from agno.document.base import Document
    from agno.document.reader.text_reader import TextReader
    
    # Then import our custom components
    from i2c.scripts.lean_knowledge_ingest import add_document_to_knowledge_base, MyEmbedder
    from i2c.db_utils import get_db_connection, query_context, query_context_filtered
    from sentence_transformers import SentenceTransformer
    
    # Create a fallback canvas if needed
    try:
        from i2c.cli.controller import canvas
    except ImportError:
        class FallbackCanvas:
            def warning(self, msg): print(f"[WARN_TEST] {msg}")
            def error(self, msg): print(f"[ERROR_TEST] {msg}")
            def info(self, msg): print(f"[INFO_TEST] {msg}")
            def success(self, msg): print(f"[SUCCESS_TEST] {msg}")
        canvas = FallbackCanvas()
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please run this script from the project root directory")
    sys.exit(1)

# Create a custom document processor for the test
def process_document(file_path):
    """Simple document processor for tests"""
    text_reader = TextReader()
    try:
        return text_reader.read(file_path)
    except Exception as e:
        print(f"Error using TextReader: {e}")
        # Fallback to direct reading
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return [Document(content=content)]
        except Exception as e2:
            print(f"Error with fallback reading: {e2}")
            return []

class TestKnowledgeManagement(unittest.TestCase):
    """Test cases for knowledge management functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests."""
        # Create a temporary directory for test files
        cls.test_dir = Path(tempfile.mkdtemp())
        print(f"Created temporary test directory: {cls.test_dir}")
        
        # Create a test project name/space
        cls.test_project = "test_knowledge_project"
        cls.knowledge_space = f"project_{cls.test_project}"

        # Initialize embedder
        try:
            cls.embedder = MyEmbedder('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"Error initializing embedder: {e}")
            cls.embedder = None

        # Initialize DB connection
        try:
            cls.db = get_db_connection()
            if not cls.db:
                print("Warning: Could not connect to database.")
        except Exception as e:
            print(f"Error connecting to database: {e}")
            cls.db = None

        # Create test files
        cls._create_test_files()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests have run."""
        # Remove temporary test directory and all its contents
        try:
            shutil.rmtree(cls.test_dir)
            print(f"Removed temporary test directory: {cls.test_dir}")
        except Exception as e:
            print(f"Error removing test directory: {e}")

    @classmethod
    def _create_test_files(cls):
        """Create sample test files with different formats."""
        # Create a markdown file
        md_content = """# Test Documentation
        
## Introduction
This is a test document for the knowledge management system.

## Features
- Feature 1: Test ingestion of markdown files
- Feature 2: Test retrieval of markdown content
- Feature 3: Test searching within markdown content

## API
The API provides endpoints for testing purposes.
"""
        md_file = cls.test_dir / "test_doc.md"
        md_file.write_text(md_content)
        
        # Create a text file
        txt_content = """Test Document
        
This is a simple text file for testing the knowledge management system.
It contains keywords like 'document', 'knowledge', and 'management'.
"""
        txt_file = cls.test_dir / "test_doc.txt"
        txt_file.write_text(txt_content)
        
        # Create a JSON file
        json_content = {
            "title": "Test JSON Document",
            "description": "A JSON document for testing",
            "sections": [
                {"name": "Section 1", "content": "Testing JSON ingestion"},
                {"name": "Section 2", "content": "Testing JSON retrieval"}
            ]
        }
        json_file = cls.test_dir / "test_doc.json"
        json_file.write_text(json.dumps(json_content, indent=2))
        
        # Create a subfolder with another file
        subfolder = cls.test_dir / "subfolder"
        subfolder.mkdir()
        sub_file = subfolder / "nested_doc.md"
        sub_file.write_text("# Nested Document\n\nThis is a document in a subfolder.")

        print(f"Created test files: {list(cls.test_dir.glob('**/*'))}")

    def test_01_ingest_markdown_file(self):
        """Test ingestion of a markdown file."""
        if not self.embedder or not self.db:
            self.skipTest("Embedder or DB not available")
            
        md_file = self.test_dir / "test_doc.md"
        self.assertTrue(md_file.exists(), "Test markdown file not found")
        
        # Create document objects directly
        docs = process_document(md_file)
        self.assertTrue(len(docs) > 0, "Failed to process markdown file")
        
        # Prepare metadata
        metadata = {
            "framework": "test_framework",
            "version": "1.0.0"
        }
        
        # Create chunks for database
        chunks = []
        for doc in docs:
            content = doc.content if hasattr(doc, 'content') else str(doc)
            vector = self.embedder.get_embeddings([content])[0]
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            
            chunk = {
                "source": str(md_file),
                "content": content,
                "vector": vector,
                "category": "test_documentation",
                "last_updated": datetime.now().isoformat(),
                "knowledge_space": self.knowledge_space,
                "document_type": "test_documentation",
                "framework": metadata.get("framework", ""),
                "version": metadata.get("version", ""),
                "parent_doc_id": "",
                "chunk_type": "test",
                "source_hash": file_hash,
                "metadata_json": json.dumps(metadata),
            }
            chunks.append(chunk)
        
        # Add to database directly
        from i2c.db_utils import add_knowledge_chunks
        
        result = add_knowledge_chunks(self.db, chunks, self.knowledge_space)
        
        self.assertTrue(result, "Failed to ingest markdown file")
        print(f"Successfully ingested markdown file: {md_file}")

    def test_02_ingest_multiple_files(self):
        """Test ingestion of multiple files."""
        if not self.embedder or not self.db:
            self.skipTest("Embedder or DB not available")
            
        # Ingest text and JSON files
        txt_file = self.test_dir / "test_doc.txt"
        json_file = self.test_dir / "test_doc.json"
        
        self.assertTrue(txt_file.exists(), "Test text file not found")
        self.assertTrue(json_file.exists(), "Test JSON file not found")
        
        from i2c.db_utils import add_knowledge_chunks
        
        # Process text file
        txt_docs = process_document(txt_file)
        self.assertTrue(len(txt_docs) > 0, "Failed to process text file")
        
        txt_metadata = {"format": "plain_text"}
        txt_chunks = []
        
        for doc in txt_docs:
            content = doc.content if hasattr(doc, 'content') else str(doc)
            vector = self.embedder.get_embeddings([content])[0]
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            
            chunk = {
                "source": str(txt_file),
                "content": content,
                "vector": vector,
                "category": "text_documentation",
                "last_updated": datetime.now().isoformat(),
                "knowledge_space": self.knowledge_space,
                "document_type": "text_documentation",
                "framework": "",
                "version": "",
                "parent_doc_id": "",
                "chunk_type": "text",
                "source_hash": file_hash,
                "metadata_json": json.dumps(txt_metadata),
            }
            txt_chunks.append(chunk)
        
        # Process JSON file
        with open(json_file, 'r') as f:
            json_content = f.read()
        
        vector = self.embedder.get_embeddings([json_content])[0]
        file_hash = hashlib.sha256(json_content.encode()).hexdigest()
        json_metadata = {"format": "json"}
        
        json_chunk = {
            "source": str(json_file),
            "content": json_content,
            "vector": vector,
            "category": "api_documentation",
            "last_updated": datetime.now().isoformat(),
            "knowledge_space": self.knowledge_space,
            "document_type": "api_documentation",
            "framework": "",
            "version": "",
            "parent_doc_id": "",
            "chunk_type": "json",
            "source_hash": file_hash,
            "metadata_json": json.dumps(json_metadata),
        }
        
        # Add to database
        txt_result = add_knowledge_chunks(self.db, txt_chunks, self.knowledge_space)
        json_result = add_knowledge_chunks(self.db, [json_chunk], self.knowledge_space)
        
        self.assertTrue(txt_result, "Failed to ingest text file")
        self.assertTrue(json_result, "Failed to ingest JSON file")
        print(f"Successfully ingested multiple files")

    def test_03_ingest_nested_file(self):
        """Test ingestion of a file in a subfolder."""
        if not self.embedder or not self.db:
            self.skipTest("Embedder or DB not available")
            
        nested_file = self.test_dir / "subfolder" / "nested_doc.md"
        self.assertTrue(nested_file.exists(), "Nested test file not found")
        
        # Create document objects directly
        docs = process_document(nested_file)
        self.assertTrue(len(docs) > 0, "Failed to process nested file")
        
        # Prepare metadata
        metadata = {"location": "subfolder"}
        
        # Create chunks for database
        chunks = []
        for doc in docs:
            content = doc.content if hasattr(doc, 'content') else str(doc)
            vector = self.embedder.get_embeddings([content])[0]
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            
            chunk = {
                "source": str(nested_file),
                "content": content,
                "vector": vector,
                "category": "nested_documentation",
                "last_updated": datetime.now().isoformat(),
                "knowledge_space": self.knowledge_space,
                "document_type": "nested_documentation",
                "framework": "",
                "version": "",
                "parent_doc_id": "",
                "chunk_type": "nested",
                "source_hash": file_hash,
                "metadata_json": json.dumps(metadata),
            }
            chunks.append(chunk)
        
        # Add to database directly
        from i2c.db_utils import add_knowledge_chunks
        
        result = add_knowledge_chunks(self.db, chunks, self.knowledge_space)
        
        self.assertTrue(result, "Failed to ingest nested file")
        print(f"Successfully ingested nested file: {nested_file}")

    def test_04_search_simple(self):
        """Test simple search functionality."""
        if not self.embedder or not self.db:
            self.skipTest("Embedder or DB not available")
        
        # Create a simple query vector
        query_text = "test documentation features"
        query_vector = self.embedder.get_embeddings([query_text])[0]
        
        # Search the knowledge base
        results = query_context(
            self.db,
            "knowledge_base",
            query_vector,
            limit=5
        )
        
        self.assertIsNotNone(results, "Search returned None")
        self.assertFalse(results.empty, "Search returned empty results")
        print(f"Search found {len(results)} results")
        print(f"First result source: {results.iloc[0]['source']}")

    def test_05_search_filtered(self):
        """Test filtered search functionality."""
        if not self.embedder or not self.db:
            self.skipTest("Embedder or DB not available")
        
        # Create a query vector
        query_text = "API documentation"
        query_vector = self.embedder.get_embeddings([query_text])[0]
        
        # Search with filters
        results = query_context_filtered(
            self.db,
            "knowledge_base",
            query_vector,
            filters={"knowledge_space": self.knowledge_space},
            limit=5
        )
        
        self.assertIsNotNone(results, "Filtered search returned None")
        self.assertFalse(results.empty, "Filtered search returned empty results")
        print(f"Filtered search found {len(results)} results")
        
        # Verify all results are from our test knowledge space
        for _, row in results.iterrows():
            if 'knowledge_space' in row:
                self.assertEqual(row['knowledge_space'], self.knowledge_space)

    def test_06_check_metadata(self):
        """Test that metadata is properly stored and retrievable."""
        if not self.embedder or not self.db:
            self.skipTest("Embedder or DB not available")
        
        # Get a generic record to check metadata fields
        query_text = "test"
        query_vector = self.embedder.get_embeddings([query_text])[0]
        
        results = query_context_filtered(
            self.db,
            "knowledge_base",
            query_vector,
            filters={"knowledge_space": self.knowledge_space},
            limit=1
        )
        
        self.assertIsNotNone(results, "Metadata check search returned None")
        self.assertFalse(results.empty, "Metadata check search returned empty results")
        
        row = results.iloc[0]
        
        # Check that essential metadata fields exist
        for field in ['source', 'content', 'document_type']:
            self.assertIn(field, row, f"Missing metadata field: {field}")
        
        # Check for enhanced metadata fields
        metadata_fields = ['knowledge_space', 'framework', 'version', 'category', 'source_hash']
        present_fields = [field for field in metadata_fields if field in row]
        
        print(f"Metadata fields present: {present_fields}")
        self.assertTrue(len(present_fields) > 0, "No enhanced metadata fields found")

    def test_07_verify_content_by_source(self):
        """Test retrieving documents by source file path."""
        if not self.embedder or not self.db:
            self.skipTest("Embedder or DB not available")
        
        # Get table for direct query
        try:
            table = self.db.open_table("knowledge_base")
            df = table.to_pandas()
            
            # Filter to our test knowledge space
            space_docs = df[df['knowledge_space'] == self.knowledge_space]
            self.assertFalse(space_docs.empty, "No documents found in test knowledge space")
            
            # Get sources in our test directory
            test_sources = []
            for _, row in space_docs.iterrows():
                source = row.get('source', '')
                if str(self.test_dir) in source:
                    test_sources.append(source)
            
            print(f"Found {len(test_sources)} sources from our test directory")
            self.assertTrue(len(test_sources) > 0, "No test sources found")
            
        except Exception as e:
            self.fail(f"Error verifying content by source: {e}")

def main():
    """Run the test suite with options."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Knowledge Management System')
    parser.add_argument('--test', '-t', help='Run specific test by name', default=None)
    parser.add_argument('--list', '-l', action='store_true', help='List available tests')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    if args.list:
        # Find all test methods
        test_methods = [m for m in dir(TestKnowledgeManagement) if m.startswith('test_')]
        print("Available tests:")
        for i, method in enumerate(sorted(test_methods), 1):
            # Get the docstring
            doc = getattr(TestKnowledgeManagement, method).__doc__ or "No description"
            print(f"{i}. {method}: {doc.strip()}")
        return
    
    if args.test:
        # Run specific test
        suite = unittest.TestSuite()
        if args.test.isdigit():
            # Find test by number
            test_methods = sorted([m for m in dir(TestKnowledgeManagement) if m.startswith('test_')])
            try:
                test_idx = int(args.test) - 1
                if 0 <= test_idx < len(test_methods):
                    test_name = test_methods[test_idx]
                    suite.addTest(TestKnowledgeManagement(test_name))
                else:
                    print(f"Error: Test number {args.test} is out of range (1-{len(test_methods)})")
                    return
            except (ValueError, IndexError):
                print(f"Error: Invalid test number {args.test}")
                return
        else:
            # Find test by name
            if not args.test.startswith('test_'):
                args.test = f'test_{args.test}'
            if hasattr(TestKnowledgeManagement, args.test):
                suite.addTest(TestKnowledgeManagement(args.test))
            else:
                print(f"Error: Test '{args.test}' not found")
                return
        
        runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
        result = runner.run(suite)
        return
    
    # Run all tests
    unittest.main(verbosity=2 if args.verbose else 1)

if __name__ == "__main__":
    main()
    
# Run all tests
# python tests/test_knowledge_management.py

# List available tests
# python tests/test_knowledge_management.py --list

# Run a specific test by number
# python tests/test_knowledge_management.py --test 1

# Run a specific test by name
# python tests/test_knowledge_management.py --test ingest_markdown_file