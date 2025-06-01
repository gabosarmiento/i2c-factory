# Enhanced repair_db_tables.py
"""Repair database tables for the I2C Factory"""

from i2c.bootstrap import initialize_environment, PROJECT_ROOT
import os
import sys
from pathlib import Path
import traceback
import shutil

# Initialize environment
initialize_environment()

# Import required components
from i2c.db_utils import (
    get_db_connection,
    get_or_create_table,
    TABLE_CODE_CONTEXT,
    SCHEMA_CODE_CONTEXT,
    TABLE_KNOWLEDGE_BASE,
    SCHEMA_KNOWLEDGE_BASE,
    DB_PATH
)
from i2c.cli.controller import canvas

def repair_database_tables(force_reset=True):
    """Ensure all database tables exist and have the correct schema"""
    canvas.info("Repairing database tables...")
    
    if force_reset:
        # Remove entire database directory to start fresh
        db_path = Path(DB_PATH)
        if db_path.exists():
            canvas.info(f"Removing entire database directory: {db_path}")
            try:
                shutil.rmtree(db_path)
                canvas.success(f"Removed database directory successfully")
            except Exception as e:
                canvas.error(f"Error removing database directory: {e}")
                return False
        
        # Ensure the directory exists for new connection
        db_path.mkdir(parents=True, exist_ok=True)
        canvas.info(f"Created fresh database directory: {db_path}")
    
    # Connect to DB (will create new connection)
    try:
        db = get_db_connection()
        if not db:
            canvas.error("Failed to connect to database")
            return False
        
        canvas.info(f"Database connected successfully")
        
    except Exception as e:
        canvas.error(f"Database connection error: {e}")
        canvas.error(traceback.format_exc())
        return False
    
    # Debug enhanced schema
    canvas.info(f"Knowledge base schema fields:")
    for field in SCHEMA_KNOWLEDGE_BASE:
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
        
        # Verify schema
        actual_schema = kb_tbl.schema
        canvas.info(f"Actual knowledge_base schema fields:")
        for field in actual_schema:
            canvas.info(f"  - {field.name}: {field.type}")
        
    except Exception as e:
        canvas.error(f"Failed to create knowledge_base table: {e}")
        canvas.error(traceback.format_exc())
        return False
    
    canvas.success("Database tables repaired successfully with enhanced schema")
    return True

if __name__ == "__main__":
    success = repair_database_tables(force_reset=True)
    if not success:
        canvas.error("Database repair failed")
        sys.exit(1)
    else:
        canvas.success("Database repair completed successfully")
        sys.exit(0)