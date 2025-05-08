# Enhanced repair_db_tables.py
"""Repair database tables for the I2C Factory"""

from i2c.bootstrap import initialize_environment, PROJECT_ROOT
import os
import sys
from pathlib import Path
import traceback

# Initialize environment
initialize_environment()

# Import required components
from i2c.db_utils import (
    get_db_connection,
    get_or_create_table,
    TABLE_CODE_CONTEXT,
    SCHEMA_CODE_CONTEXT,
    TABLE_KNOWLEDGE_BASE,
    SCHEMA_KNOWLEDGE_BASE
)
from i2c.cli.controller import canvas

def repair_database_tables():
    """Ensure all database tables exist and have the correct schema"""
    canvas.info("Repairing database tables...")
    
    # Connect to DB
    db = get_db_connection()
    if not db:
        canvas.error("Failed to connect to database")
        return False
    
    canvas.info(f"Database connected at: {db.uri}")
    
    # Check if tables exist
    tables = db.table_names()
    canvas.info(f"Existing tables: {tables}")
    
    has_code_context = TABLE_CODE_CONTEXT in tables
    has_knowledge_base = TABLE_KNOWLEDGE_BASE in tables
    
    canvas.info(f"Tables found: code_context={has_code_context}, knowledge_base={has_knowledge_base}")
    
    # If tables exist but are causing issues, drop and recreate them
    if has_code_context:
        canvas.info(f"Dropping existing code_context table")
        try:
            db.drop_table(TABLE_CODE_CONTEXT)
            canvas.success(f"Dropped code_context table successfully")
        except Exception as e:
            canvas.error(f"Error dropping code_context table: {e}")
            return False
    
    if has_knowledge_base:
        canvas.info(f"Dropping existing knowledge_base table")
        try:
            db.drop_table(TABLE_KNOWLEDGE_BASE)
            canvas.success(f"Dropped knowledge_base table successfully")
        except Exception as e:
            canvas.error(f"Error dropping knowledge_base table: {e}")
            return False
    
    # Debug schema
    canvas.info(f"Code context schema fields:")
    for field in SCHEMA_CODE_CONTEXT:
        canvas.info(f"  - {field.name}: {field.type}")
    
    # Create tables with fresh schemas
    try:
        canvas.info(f"Creating code_context table...")
        code_tbl = db.create_table(TABLE_CODE_CONTEXT, schema=SCHEMA_CODE_CONTEXT)
        canvas.success(f"Created code_context table successfully")
    except Exception as e:
        canvas.error(f"Failed to create code_context table: {e}")
        canvas.error(traceback.format_exc())
        return False
    
    try:
        canvas.info(f"Creating knowledge_base table...")
        kb_tbl = db.create_table(TABLE_KNOWLEDGE_BASE, schema=SCHEMA_KNOWLEDGE_BASE)
        canvas.success(f"Created knowledge_base table successfully")
    except Exception as e:
        canvas.error(f"Failed to create knowledge_base table: {e}")
        canvas.error(traceback.format_exc())
        return False
    
    canvas.success("Database tables repaired successfully")
    return True

if __name__ == "__main__":
    success = repair_database_tables()
    if not success:
        sys.exit(1)