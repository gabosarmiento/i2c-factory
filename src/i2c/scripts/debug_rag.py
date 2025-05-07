#!/usr/bin/env python3
"""
debug_rag.py

1) Bootstraps the i2c environment.
2) Ensures your LanceDB tables (code_context & knowledge_base) exist.
3) Indexes your entire project.
4) Dumps indexing stats and a sample query.
5) Exercises `retrieve_context_for_step` on a real file.
"""

import argparse
import sys
from pathlib import Path
import pandas as pd

# 1) Bootstrap environment & builtins
from i2c.bootstrap import initialize_environment, PROJECT_ROOT as I2C_ROOT
initialize_environment()

# 2) Bring in DB‐utils and RAG indexer + retrieval
from i2c.db_utils import (
    get_db_connection,
    get_or_create_table,
    TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT,
    TABLE_KNOWLEDGE_BASE, SCHEMA_KNOWLEDGE_BASE,
    VECTOR_DIMENSION
)
from i2c.agents.modification_team.context_reader.context_indexer import ContextIndexer
from i2c.workflow.modification.rag_retrieval import retrieve_context_for_step

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Path to codebase root"
    )
    args = parser.parse_args()
    project_root = args.project_root.resolve()

    print(f"\n🔍 Debug RAG on project: {project_root}\n")

    # 3) Ensure DB & tables are initialized up‐front
    db = get_db_connection()
    code_tbl = get_or_create_table(db, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT)
    kb_tbl   = get_or_create_table(db, TABLE_KNOWLEDGE_BASE, SCHEMA_KNOWLEDGE_BASE)
    print(f"✅ LanceDB tables ready: {TABLE_CODE_CONTEXT}, {TABLE_KNOWLEDGE_BASE}")

    # 4) Run indexer
    idx = ContextIndexer(project_root)
    status = idx.index_project()
    print("\n✅ Indexing stats:")
    for k, v in status.items():
        print(f"   • {k}: {v}")
    if status.get("chunks_indexed", 0) == 0:
        print("\n❌ No chunks indexed! Check your chunkers/embedder.")
        sys.exit(1)

    # 5) Sample a zero‐vector search
    print("\n🔎 Sample similarity query (zero‐vector):")
    zero_vec = [0.0] * VECTOR_DIMENSION
    df = code_tbl.search(zero_vec).limit(5).to_pandas()
    if df.empty:
        print("❌ Query returned no rows—table is empty.")
        return
    else:
        print(f"✅ Query returned {len(df)} rows. Sample:")
        pd.set_option("display.max_colwidth", 80)
        print(df.head(5).to_string(index=False))

    # 6) Test per‐step RAG on the first row
    sample_path = df.iloc[0]["path"]
    print(f"\n🔄 retrieve_context_for_step on: {sample_path}")
    dummy_step = {
        "file": sample_path,
        "action": "modify",
        "what": "dummy exercise context"
    }
    ctx = retrieve_context_for_step(
        dummy_step,
        db,
        idx.embed_model if hasattr(idx, "embed_model") else (lambda t: zero_vec)
    )
    if ctx:
        print("\n✅ retrieve_context_for_step returned:")
        print(ctx[:500] + ("…" if len(ctx) > 500 else ""))
    else:
        print("\n⚠️ retrieve_context_for_step returned no context.")

if __name__ == "__main__":
    main()
