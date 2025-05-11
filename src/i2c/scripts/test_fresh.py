# test_fresh.py
from i2c.bootstrap import initialize_environment
initialize_environment()
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)

# Create fresh test project
test_dir = Path("./fresh_test")
test_dir.mkdir(exist_ok=True)
test_file = test_dir / "hello.py"
test_file.write_text("def hello():\n    return 'Hello world!'")

# Import reader and test
from i2c.agents.modification_team.context_reader.context_reader_agent import ContextReaderAgent

# Create reader
reader = ContextReaderAgent(test_dir)

# Run indexing
result = reader.index_project_context()
print(f"Indexing result: {result}")

# Verify
from i2c.db_utils import get_db_connection, TABLE_CODE_CONTEXT

db = get_db_connection()
if db and TABLE_CODE_CONTEXT in db.table_names():
    table = db.open_table(TABLE_CODE_CONTEXT)
    print(f"Final table has {table.count_rows()} rows")