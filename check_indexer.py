#!/usr/bin/env python3
# check_indexer.py

import logging
from pathlib import Path

from i2c.agents.modification_team.context_reader.context_indexer import ContextIndexer
from i2c.db_utils import VECTOR_DIMENSION, TABLE_CODE_CONTEXT

# Enable debug logging for the indexer
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("agents.modification_team.context_reader.context_indexer").setLevel(logging.DEBUG)

def main():
    # Point at our tiny fixture
    root = Path("tests/fixtures/sample_project")
    print(f"\nIndexing folder: {root.resolve()}\n")

    # Initialize and index
    ci = ContextIndexer(root)
    status = ci.index_project()

    print("\n=== INDEX STATUS ===")
    print(status)

    # If we have a table, do a quick zero-vector search to get some rows
    if ci.table:
        import pandas as pd

        zero_vec = [0.0] * VECTOR_DIMENSION
        try:
            df = (
                ci.table
                  .search(zero_vec)          # use a dummy vector to scan
                  .select(["path","chunk_name","chunk_type"])
                  .limit(5)
                  .to_pandas()
            )
            print("\n=== TABLE CONTENTS (up to 5) ===")
            print(df.to_string(index=False))
        except Exception as e:
            print(f"\nError fetching rows from table '{TABLE_CODE_CONTEXT}': {e}")
    else:
        print("\nNo table available—indexer disabled or not initialized.")

if __name__ == "__main__":
    main()
