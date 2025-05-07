# src/i2c/scripts/safe_indexing.py

# First, initialize the environment
from i2c.bootstrap import initialize_environment
initialize_environment()

# Import necessary modules
import os
import time
import signal
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from i2c.db_utils import get_db_connection, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT
from i2c.agents.modification_team.context_reader.context_indexer import ContextIndexer

# Get the project path
project_path = Path(os.getcwd())
print(f"Project path: {project_path}")

# Create database connection and reset table
db = get_db_connection()
if db:
    print(f"Database connection successful: {db}")
    
    # Drop the existing table if it exists
    if TABLE_CODE_CONTEXT in db.table_names():
        print(f"Dropping existing table: {TABLE_CODE_CONTEXT}")
        db.drop_table(TABLE_CODE_CONTEXT)
        print(f"Table dropped successfully")
    
    # Recreate the table
    table = db.create_table(TABLE_CODE_CONTEXT, schema=SCHEMA_CODE_CONTEXT)
    print(f"Table recreated: {table}")
else:
    print("Failed to connect to database")
    exit(1)

# Create indexer
indexer = ContextIndexer(project_path)
print(f"Indexer created: {indexer}")

# Define a function to process files with timeout
def process_file_with_timeout(file_path, timeout=30):
    """Process a single file with timeout."""
    print(f"Processing {file_path}...")
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Processing {file_path} timed out after {timeout} seconds")
    
    # Set timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    
    try:
        result = indexer._process_file(file_path)
        signal.alarm(0)  # Cancel timeout
        return result
    except TimeoutError as e:
        print(f"WARNING: {e}")
        return {'skipped': 1, 'indexed': 0, 'chunks': 0, 'errors': [str(e)]}
    except Exception as e:
        print(f"ERROR: Processing {file_path} failed: {e}")
        return {'skipped': 0, 'indexed': 0, 'chunks': 0, 'errors': [str(e)]}
    finally:
        signal.alarm(0)  # Ensure timeout is canceled

# Find files to process
files = [
    p for p in project_path.rglob('*')
    if p.is_file() and not any(part in p.parts for part in indexer.skip_dirs)
]

# Skip large files
files_to_process = []
for file_path in files:
    try:
        if file_path.stat().st_size > indexer.max_file_size:
            print(f"Skipping {file_path}: too large.")
            continue
        files_to_process.append(file_path)
    except Exception as e:
        print(f"Error accessing {file_path}: {e}")

print(f"Found {len(files_to_process)} files to process")

# Process files sequentially with timeout
results = {
    'files_indexed': 0,
    'files_skipped': 0,
    'chunks_indexed': 0,
    'errors': []
}

for file_path in files_to_process:
    try:
        result = process_file_with_timeout(file_path)
        results['files_indexed'] += result.get('indexed', 0)
        results['files_skipped'] += result.get('skipped', 0)
        results['chunks_indexed'] += result.get('chunks', 0)
        results['errors'].extend(result.get('errors', []))
    except Exception as e:
        print(f"Unexpected error processing {file_path}: {e}")
        results['errors'].append(str(e))

print("\nIndexing summary:")
print(f"Files indexed: {results['files_indexed']}")
print(f"Files skipped: {results['files_skipped']}")
print(f"Chunks indexed: {results['chunks_indexed']}")
print(f"Errors: {len(results['errors'])}")

# Verify the indexed data
try:
    df = table.to_pandas()
    print(f"\nTotal chunks in database: {len(df)}")
    if len(df) > 0:
        print(f"Unique file paths: {df['path'].nunique()}")
        print(f"Sample paths: {df['path'].unique()[:5]}")
        print(f"Chunk types: {df['chunk_type'].unique()}")
        
        # Check if there are any JS files indexed
        js_files = df[df['path'].str.endswith('.js')]
        print(f"JavaScript files indexed: {js_files['path'].nunique()}")
        if len(js_files) > 0:
            print(f"Sample JS files: {js_files['path'].unique()[:5]}")
except Exception as e:
    print(f"Error checking indexed data: {e}")

print("\nIndexing script completed")