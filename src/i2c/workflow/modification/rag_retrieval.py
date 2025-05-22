# workflow/modification/rag_retrieval.py
# Handles RAG embedding generation and querying LanceDB for context.

from pathlib import Path
import pandas as pd
from typing import Any, Optional, List, Dict    

# Import DB Utils directly (absolute import)

from i2c.db_utils import (
    query_context,
    TABLE_CODE_CONTEXT,
    TABLE_KNOWLEDGE_BASE,
)

# Use AGNO's embedder (has .dimensions & get_embedding_and_usage)
from agno.embedder.sentence_transformer import SentenceTransformerEmbedder

# Import CLI controller
try:
    from i2c.cli.controller import canvas
except ImportError:
    # Basic fallback logger if canvas isn't available
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_RAG] {msg}")
        def error(self, msg): print(f"[ERROR_RAG] {msg}")
        def info(self, msg): print(f"[INFO_RAG] {msg}")
    canvas = FallbackCanvas()

# --- RAG Configuration ---
MAX_RAG_RESULTS_PLANNER = 5  # Context chunks for planner
MAX_RAG_RESULTS_MODIFIER = 3  # Context chunks for modifier (per step)

# Let's add the following function to workflow/modification/rag_retrieval.py

def retrieve_combined_context(
    query_text: str,
    db: Any,
    embed_model: Any,
    code_limit: int = MAX_RAG_RESULTS_PLANNER,
    knowledge_limit: int = MAX_RAG_RESULTS_MODIFIER,
) -> Dict[str, str]:
    """
    Retrieve context from both code_context & knowledge_base tables.
    """
    try:
        import hashlib

        def deduplicate_chunks(chunks):
            seen_hashes = set()
            deduped = []
            for r in chunks:
                h = hashlib.sha256(r["content"].encode()).hexdigest()
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    deduped.append(r)
            return deduped

        def boost_relevance(chunks, query_text: str):
            query = query_text.lower()
            for r in chunks:
                boost = 0
                if "title" in query and "title" in r.get("content", "").lower():
                    boost += 2
                if "title" in query and "title" in r.get("chunk_name", "").lower():
                    boost += 3
                if "test" in r.get("chunk_name", "").lower():
                    boost -= 1
                r["score"] = r.get("score", 0) + boost * 0.05
            return sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)

        # 1) Embed the query
        try:
            if hasattr(embed_model, 'encode'):
                vector = embed_model.encode(query_text)
            elif hasattr(embed_model, 'get_embedding_and_usage'):
                vector, _ = embed_model.get_embedding_and_usage(query_text)
            else:
                canvas.error(f"Unknown embedding model type: {type(embed_model)}")
                return {"code_context": "", "knowledge_context": ""}
            if vector is None:
                return {"code_context": "", "knowledge_context": ""}
        except Exception as e:
            canvas.error(f"Error generating embedding: {str(e)}")
            return {"code_context": "", "knowledge_context": ""}

        # 2) Retrieve and process from code_context
        res = query_context(db, TABLE_CODE_CONTEXT, query_vector=vector, limit=code_limit)
        res = deduplicate_chunks(res)
        res = boost_relevance(res, query_text)
        for i, r in enumerate(res):
            canvas.info(f"[RAG:code] {i+1:02d} | chunk={r.get('chunk_name')} | file={r.get('path')} | score={r.get('score'):.2f}")
        code_ctx = _format_rag_results(res, "code-context", 500)

        # 3) Retrieve and process from knowledge_base
        res = query_context(db, TABLE_KNOWLEDGE_BASE, query_vector=vector, limit=knowledge_limit)
        res = deduplicate_chunks(res)
        res = boost_relevance(res, query_text)
        for i, r in enumerate(res):
            canvas.info(f"[RAG:kb]   {i+1:02d} | chunk={r.get('chunk_name')} | file={r.get('path')} | score={r.get('score'):.2f}")
        kb_ctx = _format_rag_results(res, "knowledge-base", 500)

        return {"code_context": code_ctx, "knowledge_context": kb_ctx}

    except Exception as e:
        canvas.error(f"Error retrieving combined context: {e}")
        return {"code_context": "", "knowledge_context": ""}

def _format_rag_results(rag_results: pd.DataFrame, context_description: str, max_content_len: int = 500) -> str:
    """
    Formats LanceDB query results into a string for LLM prompts.
    
    Args:
        rag_results: DataFrame from LanceDB containing retrieval results
        context_description: Description of what this context is for (planner, step, etc.)
        max_content_len: Maximum length to include from each chunk
        
    Returns:
        Formatted string with all relevant context
    """
    default_message = f"No relevant context chunks found via vector search for {context_description}."
    if rag_results is None or rag_results.empty:
        return default_message

    canvas.info(f"   Retrieved {len(rag_results)} relevant context chunks for {context_description}.")
    context_lines = [f"[Retrieved Context for {context_description}:]"]
    
    for _, row in rag_results.iterrows():
        # Safely get values with defaults
        chunk_path = row.get('path', 'N/A')
        chunk_type = row.get('chunk_type', 'N/A')
        chunk_name = row.get('chunk_name', 'N/A')
        chunk_content = row.get('content', '')

        context_lines.append(f"--- Start Chunk: {chunk_path} ({chunk_type}: {chunk_name}) ---")
        content_snippet = chunk_content[:max_content_len] + ('...' if len(chunk_content) > max_content_len else '')
        context_lines.append(content_snippet)
        context_lines.append(f"--- End Chunk: {chunk_path} ---")

    # Check if only the header was added
    if len(context_lines) == 1:
         return default_message

    return "\n".join(context_lines)

def retrieve_context_for_planner(
    user_request: str,
    db: Any,                         # LanceDBConnection
    embed_model: Any                # Could be SentenceTransformerEmbedder or other type
) -> str:
    """
    Generates embedding for user request and retrieves context for the planner.
    """
    canvas.step("Analyzing user request for planning context...")

    # Decide what to embed:
    if user_request.lower() == 'r':
        canvas.info("   Skipping RAG context retrieval for generic 'refine' request.")
        return "No context needed for generic refine request."
    elif user_request.lower().startswith('f '):
        query_text = user_request[2:].strip()
    else:
        query_text = user_request.strip()

    if not query_text:
        return "No relevant context could be retrieved for planning."

    # 1) Embed - handle different embedding model types
    try:
        # Check if it has encode method (standard for SentenceTransformer)
        if hasattr(embed_model, 'encode'):
            vector = embed_model.encode(query_text)
        # Check if the model has get_embedding_and_usage method (Agno custom)
        elif hasattr(embed_model, 'get_embedding_and_usage'):
            vector, _ = embed_model.get_embedding_and_usage(query_text)
        else:
            canvas.error(f"Unknown embedding model type: {type(embed_model)}")
            return "No relevant context could be retrieved for planning."
            
        # Skip only if embedding actually failed
        if vector is None:
            return "No relevant context could be retrieved for planning."
    except Exception as e:
        canvas.error(f"Error generating embedding: {str(e)}")
        return "No relevant context could be retrieved for planning."

    # 2) Query LanceDB for planner context
    res = query_context(
        db,
        TABLE_CODE_CONTEXT,
        query_vector=vector,
        limit=MAX_RAG_RESULTS_PLANNER
    )

    # 3) Format and return
    return _format_rag_results(res, "planning", max_content_len=500)

def retrieve_context_for_step(step: dict, db, embed_model: Any) -> Optional[str]:
    """
    Generates embedding for a modification step and retrieves relevant context.
    """
    # Extract step information
    file_path   = step.get('file', '')
    action      = step.get('action', '').lower()
    what_to_do  = step.get('what', '')
    how_to_do_it = step.get('how', '')

    canvas.info(f"    Retrieving context for step: {what_to_do[:40]}...")

    # Build one or two query texts
    query_texts = [f"File: {file_path} Action: {action} Task: {what_to_do} Details: {how_to_do_it}"]
    if action == 'modify':
        query_texts.append(f"File path: {file_path}")

    retrieved_contexts: List[str] = []

    for query_text in query_texts:
        # 1) Embed
        try:
            # Check if it has encode method (standard for SentenceTransformer)
            if hasattr(embed_model, 'encode'):
                vector = embed_model.encode(query_text)
            # Check if the model has get_embedding_and_usage method (Agno custom)
            elif hasattr(embed_model, 'get_embedding_and_usage'):
                vector, _ = embed_model.get_embedding_and_usage(query_text)
            else:
                canvas.error(f"Unknown embedding model type: {type(embed_model)}")
                continue
                
            if vector is None:
                continue
        except Exception as e:
            canvas.error(f"Error generating embedding: {str(e)}")
            continue

        # 2) Query LanceDB
        rag_results = query_context(
            db,
            TABLE_CODE_CONTEXT,
            query_vector=vector,
            limit=MAX_RAG_RESULTS_MODIFIER
        )
        # explicitly guard against None *and* empty DataFrame
        if rag_results is None or rag_results.empty:
            continue

        # 3) Format
        formatted = _format_rag_results(
            rag_results,
            f"step '{what_to_do[:30]}...' ({file_path})",
            max_content_len=300
        )
        # Skip the “no context” message
        if "No relevant context" not in formatted:
            retrieved_contexts.append(formatted)

    # Return combined contexts or None
    return "\n\n".join(retrieved_contexts) if retrieved_contexts else None

def debug_retrieved_chunks(chunks, query_text, log_file="rag_debug.log"):
    with open(log_file, "a") as f:
        f.write(f"==== Query: {query_text} ====\n")
        for i, chunk in enumerate(chunks):
            f.write(f"Chunk {i}: {chunk['path']}\n")
            f.write(f"Content: {chunk['content'][:300]}...\n")
            f.write(f"Score: {chunk['_distance']}\n\n")