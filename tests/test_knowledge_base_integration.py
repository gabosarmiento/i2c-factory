# tests/test_knowledge_base_integration.py
import unittest
import tempfile
from pathlib import Path
import numpy as np
from db_utils import (
    initialize_db, 
    migrate_knowledge_base,
    add_knowledge_chunks,
    query_context_filtered,
    SCHEMA_KNOWLEDGE_BASE_V2, 
    DB_PATH
)

class TestKnowledgeBaseIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test database"""
        self.test_db_path = tempfile.mkdtemp()
        self.old_db_path = DB_PATH
        # Override DB_PATH for testing
        import db_utils
        db_utils.DB_PATH = self.test_db_path
        
        self.db = initialize_db()
        
    def tearDown(self):
        """Clean up test database"""
        import shutil
        shutil.rmtree(self.test_db_path)
        # Restore original DB_PATH
        import db_utils
        db_utils.DB_PATH = self.old_db_path
    
    def test_schema_migration(self):
        """Test migration from old to new schema"""
        # Create old table with sample data
        old_data = [{
            "source": "test.pdf",
            "content": "Sample content",
            "vector": np.random.rand(384).tolist(),
            "category": "documentation",
            "last_updated": "2024-01-01"
        }]
        
        # Add data with old schema
        table = self.db.create_table("knowledge_base_test", data=old_data, schema=SCHEMA_KNOWLEDGE_BASE)
        
        # Migrate to new schema
        success = migrate_knowledge_base(self.db)
        self.assertTrue(success)
        
        # Verify data preserved and new fields added
        migrated_table = self.db.open_table("knowledge_base_test")
        df = migrated_table.to_df()
        
        self.assertEqual(len(df), 1)
        self.assertIn("knowledge_space", df.columns)
        self.assertEqual(df.iloc[0]["knowledge_space"], "default")
    
    def test_filtered_queries(self):
        """Test filtered vector search"""
        # Add test chunks with different metadata
        chunks = [
            {
                "source": "react_docs.md",
                "content": "React hooks documentation",
                "vector": np.random.rand(384).tolist(),
                "knowledge_space": "react_project",
                "framework": "react",
                "version": "18.0.0",
                "document_type": "api_doc"
            },
            {
                "source": "django_docs.md",
                "content": "Django views documentation",
                "vector": np.random.rand(384).tolist(),
                "knowledge_space": "django_project",
                "framework": "django",
                "version": "4.0.0",
                "document_type": "api_doc"
            }
        ]
        
        success = add_knowledge_chunks(self.db, chunks, "test_space")
        self.assertTrue(success)
        
        # Test filtered query
        query_vector = np.random.rand(384).tolist()
        results = query_context_filtered(
            self.db,
            "knowledge_base",
            query_vector,
            filters={"framework": "react"},
            limit=5
        )
        
        self.assertIsNotNone(results)
        self.assertEqual(len(results), 1)
        self.assertEqual(results.iloc[0]["framework"], "react")