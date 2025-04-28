# /workflow/modification/rag_retrieval.py
# Handles RAG embedding generation and querying LanceDB for context.

from pathlib import Path
import pandas as pd
from typing import Any # For type hinting embedding model

# Import DB Utils directly (absolute import)
from db_utils import query_context

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
MAX_RAG_RESULTS_PLANNER = 5
MAX_RAG_RESULTS_MODIFIER = 3 # Context chunks for modifier (per step)

def _generate_request_embedding(text: str, embed_model: Any) -> list[float] | None:
    """Generates embedding for a user request string."""
    if not embed_model or not text:
        canvas.warning("   ⚠️ Embedding model not available or empty text. Cannot generate query vector.")
        return None
    try:
        vector = embed_model.encode(text, convert_to_numpy=False)
        vector = [float(x) for x in vector]
        canvas.info(f"   Generated query vector for text: '{text[:30]}...'")
        return vector
    except Exception as e:
        canvas.warning(f"   ⚠️ Failed to generate embedding for text '{text[:30]}...': {e}")
        return None

def _format_rag_results(rag_results: pd.DataFrame | None, context_description: str, max_len: int = 500) -> str:
    """Formats LanceDB query results into a string for LLM prompts."""
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
        content_snippet = chunk_content[:max_len] + ('...' if len(chunk_content) > max_len else '')
        context_lines.append(content_snippet)
        context_lines.append(f"--- End Chunk: {chunk_path} ---")

    # Check if only the header was added
    if len(context_lines) == 1:
         return default_message

    return "\n".join(context_lines)

def retrieve_context_for_planner(user_request: str, table: Any, embed_model: Any) -> str:
    """Generates embedding for user request and retrieves context for the planner."""
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
    if table and query_vector:
        rag_results = query_context(table, query_vector, limit=MAX_RAG_RESULTS_PLANNER)
        retrieved_context_str = _format_rag_results(rag_results, "planning", max_len=500)

    return retrieved_context_str


def retrieve_context_for_step(step: dict, table: Any, embed_model: Any) -> str | None:
    """Generates embedding for a modification step and retrieves relevant context."""
    canvas.info(f"    Retrieving context for step: {step.get('what')[:40]}...")
    query_vector = None
    # Create query text based on step details
    step_query_text = f"File: {step.get('file')} Action: {step.get('action')} Task: {step.get('what')} Details: {step.get('how')}"

    query_vector = _generate_request_embedding(step_query_text, embed_model)

    retrieved_context_step_str = None
    if table and query_vector:
        rag_results = query_context(table, query_vector, limit=MAX_RAG_RESULTS_MODIFIER)
        formatted_context = _format_rag_results(rag_results, f"step '{step.get('what')[:30]}...'", max_len=300)
        # Only return the formatted context if it's not the default "No relevant context" message
        if "No relevant context" not in formatted_context:
             retrieved_context_step_str = formatted_context

    return retrieved_context_step_str # Return formatted string or None
