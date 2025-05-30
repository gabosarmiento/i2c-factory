# test_indexing.py
from i2c.bootstrap import initialize_environment
initialize_environment()
from pathlib import Path
from i2c.agents.modification_team.context_reader.context_reader_agent import ContextReaderAgent
from i2c.db_utils import get_db_connection, TABLE_CODE_CONTEXT

# Print database info
db = get_db_connection()
print(f"Database connection: {db is not None}")
print(f"Tables: {db.table_names() if db else []}")

# Create test directory and file
test_dir = Path("./indexing_test")
test_dir.mkdir(exist_ok=True)
test_file = test_dir / "sample.py"
test_file.write_text("""
# Sample Python code for testing RAG indexing
def sample_function():
    \"\"\"
    This is a sample function that does nothing.
    It's used to test the RAG indexing system.
    \"\"\"
    return "Hello, world!"

class SampleClass:
    def __init__(self):
        self.value = 42
        
    def get_value(self):
        return self.value
""")

print(f"Created test file at {test_file}")

# Create reader agent and index project
reader = ContextReaderAgent(test_dir)
print(f"Created reader agent for {test_dir}")

# Index project
print("Indexing project...")
result = reader.index_project_context()
print(f"Indexing result: {result}")

# Verify chunks were added
if db and TABLE_CODE_CONTEXT in db.table_names():
    table = db.open_table(TABLE_CODE_CONTEXT)
    row_count = table.count_rows()
    print(f"After indexing, table has {row_count} rows")
    
    if row_count > 0:
        # Try to query the table
        print("Querying first row...")
        df = table.to_pandas()
        df = df.head(1)
        if not df.empty:
            print(f"Columns: {list(df.columns)}")
            print(f"Content snippet: {df['content'].iloc[0][:50]}...")