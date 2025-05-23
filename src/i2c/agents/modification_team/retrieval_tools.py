import json
from pathlib import Path
from typing import Any, Dict, Optional, List
from textwrap import dedent
from agno.tools.function import Function
from i2c.db_utils import get_db_connection, query_context, TABLE_CODE_CONTEXT, TABLE_KNOWLEDGE_BASE
from i2c.workflow.modification.rag_config import get_embed_model


def vector_retrieve(query: str, source: str = "both", limit: int = 5) -> str:
    """
    Retrieve relevant context from vector database
    Args:
        query: Search query (e.g., "Agno Agent patterns", "LLM provider usage")  
        source: "code", "knowledge", or "both"
        limit: Max results to return
    """
    try:
        db = get_db_connection()
        embed_model = get_embed_model()
        if not db or not embed_model:
            return "Vector retrieval unavailable"

        # compute vector
        if hasattr(embed_model, 'encode'):
            vector = embed_model.encode(query)
        elif hasattr(embed_model, 'get_embedding_and_usage'):
            vector, _ = embed_model.get_embedding_and_usage(query)
        else:
            return f"Unknown embedding model: {type(embed_model)}"

        results = []
        # code context
        if source in ("code", "both"):
            try:
                code_df = query_context(db, TABLE_CODE_CONTEXT, query_vector=vector, limit=limit)
                if code_df is not None and not code_df.empty:
                    for _, row in code_df.iterrows():
                        results.append({
                            "source": "code",
                            "file": row.get('path', ''),
                            "content": row.get('content', '')[:800]
                        })
            except Exception as e:
                results.append({"error": f"Code context error: {e}"})
        # knowledge base
        if source in ("knowledge", "both"):
            try:
                kb_df = query_context(db, TABLE_KNOWLEDGE_BASE, query_vector=vector, limit=limit)
                if kb_df is not None and not kb_df.empty:
                    for _, row in kb_df.iterrows():
                        results.append({
                            "source": "knowledge",
                            "file": row.get('source', ''),
                            "content": row.get('content', '')[:800]
                        })
            except Exception as e:
                results.append({"error": f"Knowledge base error: {e}"})

        if not results:
            return f"No context found for '{query}'"

        # format for LLM
        out = [f"--- Result {i+1} [{r.get('source')}] {r.get('file')}" for i, r in enumerate(results)]
        for line in out:
            pass
        return json.dumps(results)
    except Exception as e:
        return f"vector_retrieve error: {e}"


def github_fetch(repo_path: str, file_path: str = "") -> str:
    """
    Fetch content from GitHub repository via API
    
    Args:
        repo_path: Repository path (e.g., "agno-agi/agno")
        file_path: Specific file path (optional)
    """
    import os
    try:
        from github import Github, GithubException  # PyGithub library
    except ImportError:
        return "GitHub fetch unavailable: PyGithub library not installed"

    token = os.environ.get("GITHUB_ACCESS_TOKEN")
    if not token:
        return "GitHub fetch unavailable: GITHUB_ACCESS_TOKEN not set"

    try:
        gh = Github(token)
        repo = gh.get_repo(repo_path)
        # Fetch a specific file
        if file_path:
            content_file = repo.get_contents(file_path)
            try:
                return content_file.decoded_content.decode('utf-8')
            except AttributeError:
                return content_file.decoded_content.decode()
        # List repository root contents if no file specified
        contents = repo.get_contents("")
        paths = [item.path for item in contents]
        return "\n".join(paths)
    except GithubException as e:
        msg = getattr(e.data, 'message', None) or str(e)
        return f"GitHub API error: {msg}"
    except Exception as e:
        return f"GitHub fetch error: {str(e)}"  


def get_project_context(project_path: str, focus: str = "") -> str:
    """
    List project files and extract focused lines
    """
    base = Path(project_path)
    if not base.exists():
        return f"Project path not found: {project_path}"
    files = [str(p.relative_to(base)) for p in base.rglob('*.py')]
    summary = {'files': files}
    if focus:
        matches = []
        for p in base.rglob('*.py'):
            try:
                text = p.read_text(encoding='utf-8', errors='ignore')
                if focus.lower() in text.lower():
                    matches.append(str(p.relative_to(base)))
            except:
                continue
        summary['matches'] = matches
    return json.dumps(summary)


def create_retrieval_tools(session_state: dict = None) -> List[Function]:
    """Return Function tool wrappers"""
    return [
        Function(
            name="vector_retrieve",
            description="Retrieve context snippets from vector DB",
            parameters={"type": "object", "properties": {"query": {"type": "string"}, "source": {"type": "string", "enum": ["code","knowledge","both"]}, "limit": {"type": "integer"}}, "required": ["query"]},
            function=vector_retrieve
        ),
        Function(
            name="github_fetch",
            description="Fetch a file from GitHub repo",
            parameters={"type": "object", "properties": {"repo_path": {"type": "string"}, "file_path": {"type": "string"}}, "required": ["repo_path"]},
            function=github_fetch
        ),
        Function(
            name="get_project_context",
            description="List project files and focused matches",
            parameters={"type": "object", "properties": {"project_path": {"type": "string"}, "focus": {"type": "string"}}, "required": ["project_path"]},
            function=get_project_context
        )
    ]
