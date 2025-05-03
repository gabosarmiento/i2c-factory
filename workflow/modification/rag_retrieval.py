# workflow/modification/rag_retrieval.py
# Handles RAG embedding generation and querying LanceDB for context.

from pathlib import Path
import pandas as pd
from typing import Any, Optional, List, Dict    

# Import DB Utils directly (absolute import)
# from db_utils import query_context
from db_utils import (
    query_context,
    TABLE_CODE_CONTEXT,
    TABLE_KNOWLEDGE_BASE,
) 
from db_utils import get_or_create_table, SCHEMA_CODE_CONTEXT, SCHEMA_KNOWLEDGE_BASE

# Import context utility for embedding generation
try:
    from agents.modification_team.context_utils import generate_embedding
except ImportError:
    generate_embedding = None

# Import CLI controller
try:
    from cli.controller import canvas
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
    Retrieve context from **both** code_context & knowledge_base tables.
    Returns a dict of formatted‑string payloads ready for prompt injection.
    """
    try:
        vector = _generate_request_embedding(query_text, embed_model)
        code_ctx = ""
        kb_ctx   = ""
        if vector is not None:
             # open and query the code_context table
            code_table = get_or_create_table(db, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT)
            res = query_context(
                code_table,
                TABLE_CODE_CONTEXT,
                query_vector=vector,
                
                limit=code_limit
            )
            code_ctx = _format_rag_results(res, "code-context", 500)

            # open and query the knowledge_base table
            kb_table = get_or_create_table(db, TABLE_KNOWLEDGE_BASE, SCHEMA_KNOWLEDGE_BASE)
            res = query_context(
                kb_table,
                TABLE_KNOWLEDGE_BASE,
                query_vector=vector,
                limit=knowledge_limit
            )
            kb_ctx = _format_rag_results(res, "knowledge-base", 500)

        return {"code_context": code_ctx, "knowledge_context": kb_ctx}

    except Exception as e:
        canvas.error(f"Error retrieving combined context: {e}")
        return {"code_context": "", "knowledge_context": ""}
    
def _generate_request_embedding(text: str, embed_model: Any) -> Optional[List[float]]:
    """
    Generates embedding for a user request string using either:
    1. The imported generate_embedding function from context_utils (preferred)
    2. Direct embedding generation using the provided model (fallback)
    
    Args:
        text: The text to embed
        embed_model: SentenceTransformer model instance
        
    Returns:
        List of floats representing the embedding vector, or None on failure
    """
    if not text:
        canvas.warning("   ⚠️ Cannot generate embedding: Input text is empty.")
        return None
        
    # Try using the dedicated function from context_utils first (if available)
    if generate_embedding:
        return generate_embedding(text)
        
    # Fallback to direct embedding if the model is available
    if not embed_model:
        canvas.warning("   ⚠️ Embedding model not available. Cannot generate query vector.")
        return None
        
    try:
        # Generate embedding directly from the model
        vector = embed_model.encode(text, convert_to_numpy=True)
        # Ensure it's a list of floats
        return [float(x) for x in vector.tolist()]
    except Exception as e:
        canvas.warning(f"   ⚠️ Failed to generate embedding for text '{text[:30]}...': {e}")
        return None

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

def retrieve_context_for_planner(user_request: str, db, embed_model: Any) -> str:
    """
    Generates embedding for user request and retrieves context for the planner.
    
    Args:
        user_request: The raw user request (r, f <feature>, etc.)
        db: LanceDBConnection handle
        embed_model: SentenceTransformer model instance
        
    Returns:
        Formatted string with retrieved context
    """
    canvas.step("Analyzing user request for planning context...")
    query_vector = None
    query_text = None

    if user_request.lower() == 'r':
        canvas.info("   Skipping RAG context retrieval for generic 'refine' request.")
    elif user_request.lower().startswith('f '):
        query_text = user_request[len('f '):].strip()
    else:
        query_text = user_request

    if query_text:
        query_vector = _generate_request_embedding(query_text, embed_model)

    retrieved_context_str = "No relevant context could be retrieved for planning (vector or table unavailable)."
    if query_vector:
        table = get_or_create_table(db, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT)
        rag_results = query_context(table,TABLE_CODE_CONTEXT, query_vector=query_vector, limit=MAX_RAG_RESULTS_PLANNER)
        retrieved_context_str = _format_rag_results(rag_results, "planning", max_content_len=500)

    return retrieved_context_str

def retrieve_context_for_step(step: dict, db, embed_model: Any) -> Optional[str]:
    """
    Generates embedding for a modification step and retrieves relevant context.
    
    Args:
        step: single modification step dict
        db: LanceDBConnection handle
        embed_model: SentenceTransformer model instance
        
    Returns:
        Formatted string with retrieved context or None if no relevant context found
    """
    # Extract step information
    file_path = step.get('file', '')
    action = step.get('action', '').lower()
    what_to_do = step.get('what', '')
    how_to_do_it = step.get('how', '')
    
    canvas.info(f"    Retrieving context for step: {what_to_do[:40]}...")
    
    # Create specialized query based on step type
    query_texts = []
    
    # Always include the core step information
    core_query = f"File: {file_path} Action: {action} Task: {what_to_do} Details: {how_to_do_it}"
    query_texts.append(core_query)
    
    # Add file-specific query to find similar code in the same file
    if action == 'modify':
        query_texts.append(f"File path: {file_path}")
    
    # Generate embeddings and run queries
    retrieved_contexts = []
    # open code_context once
    table = get_or_create_table(db, TABLE_CODE_CONTEXT, SCHEMA_CODE_CONTEXT)
    for query_text in query_texts:
        query_vector = _generate_request_embedding(query_text, embed_model)
        if query_vector:
            rag_results = query_context(table, TABLE_CODE_CONTEXT, query_vector=query_vector, limit=MAX_RAG_RESULTS_MODIFIER)
            if rag_results is not None and not rag_results.empty:
                formatted_context = _format_rag_results(
                    rag_results, 
                    f"step '{what_to_do[:30]}...' ({file_path})", 
                    max_content_len=300
                )
                # Only add non-empty context
                if "No relevant context" not in formatted_context:
                    retrieved_contexts.append(formatted_context)
    
    # Combine all retrieved contexts
    if retrieved_contexts:
        return "\n\n".join(retrieved_contexts)
    
    # Return None if no relevant context found
    return None