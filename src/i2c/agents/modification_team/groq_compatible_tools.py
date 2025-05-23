# src/i2c/agents/modification_team/groq_compatible_tools.py

"""
Groq-compatible tool wrappers that ensure proper response formatting.
This addresses the 'content property missing' error by ensuring all tool responses
follow the correct format expected by Groq's API.
"""

import json
from typing import Any, Dict, List, Optional
from agno.tools.function import Function

# Import our working tool functions
from .retrieval_tools import vector_retrieve, github_fetch, get_project_context

class GroqToolResponse:
    """Wrapper to ensure tool responses are compatible with Groq's expected format."""
    
    def __init__(self, content: Any):
        self.content = str(content) if not isinstance(content, str) else content
    
    def __str__(self):
        return self.content

def groq_vector_retrieve(query: str, source: str = "knowledge", limit: int = 5) -> GroqToolResponse:
    """Groq-compatible vector retrieve function."""
    try:
        result = vector_retrieve(query, source, limit)
        return GroqToolResponse(result)
    except Exception as e:
        error_response = json.dumps({"error": f"Vector search failed: {str(e)}"})
        return GroqToolResponse(error_response)

def groq_github_fetch(repo_path: str, file_path: str = "README.md") -> GroqToolResponse:
    """Groq-compatible GitHub fetch function."""
    try:
        result = github_fetch(repo_path, file_path)
        return GroqToolResponse(result)
    except Exception as e:
        error_response = json.dumps({"error": f"GitHub fetch failed: {str(e)}"})
        return GroqToolResponse(error_response)

def groq_get_project_context(project_path: str = ".", focus: str = "") -> GroqToolResponse:
    """Groq-compatible project context function."""
    try:
        result = get_project_context(project_path, focus)
        return GroqToolResponse(result)
    except Exception as e:
        error_response = json.dumps({"error": f"Project context failed: {str(e)}"})
        return GroqToolResponse(error_response)

def create_groq_compatible_tools(session_state: Optional[Dict[str, Any]] = None) -> List[Function]:
    """
    Create Groq-compatible retrieval tools.
    
    Returns:
        List of Function objects that work properly with Groq
    """
    tools = []
    
    # Vector search tool with Groq compatibility
    vector_tool = Function(
        name="vector_retrieve",
        description="Retrieve context snippets from vector database using semantic search",
        entrypoint=groq_vector_retrieve,
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query text to find relevant information"
                },
                "source": {
                    "type": "string",
                    "enum": ["code", "knowledge", "both"],
                    "description": "Source to search in - 'code' for code context, 'knowledge' for documentation, 'both' for all sources",
                    "default": "knowledge"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20
                }
            },
            "required": ["query"]
        }
    )
    tools.append(vector_tool)
    
    # GitHub fetch tool with Groq compatibility
    github_tool = Function(
        name="github_fetch",
        description="Fetch a file from a GitHub repository for reference or examples",
        entrypoint=groq_github_fetch,
        parameters={
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Repository path in 'owner/repo' format (e.g., 'microsoft/vscode')"
                },
                "file_path": {
                    "type": "string",
                    "description": "Path to the file within the repository",
                    "default": "README.md"
                }
            },
            "required": ["repo_path"]
        }
    )
    tools.append(github_tool)
    
    # Project context tool with Groq compatibility
    project_tool = Function(
        name="get_project_context",
        description="Get information about files in the current project directory",
        entrypoint=groq_get_project_context,
        parameters={
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "Path to the project directory to analyze",
                    "default": "."
                },
                "focus": {
                    "type": "string",
                    "description": "Keyword to filter files (e.g., 'test', 'config', 'model')",
                    "default": ""
                }
            },
            "required": ["project_path"]
        }
    )
    tools.append(project_tool)
    
    return tools

# Alternative approach using OpenAI-style tool format
def create_openai_style_tools() -> List[Dict[str, Any]]:
    """
    Create tools in OpenAI format that might be more compatible with Groq.
    This is an alternative approach if the Function objects still don't work.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "vector_retrieve",
                "description": "Retrieve context snippets from vector database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "source": {"type": "string", "enum": ["code", "knowledge", "both"], "default": "knowledge"},
                        "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function", 
            "function": {
                "name": "github_fetch",
                "description": "Fetch a file from GitHub repository",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_path": {"type": "string", "description": "Repository path (owner/repo)"},
                        "file_path": {"type": "string", "default": "README.md", "description": "File path in repo"}
                    },
                    "required": ["repo_path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_project_context", 
                "description": "Get project file information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "default": ".", "description": "Project directory"},
                        "focus": {"type": "string", "default": "", "description": "Filter keyword"}
                    },
                    "required": ["project_path"]
                }
            }
        }
    ]

# Function registry for manual tool calling
TOOL_REGISTRY = {
    "vector_retrieve": groq_vector_retrieve,
    "github_fetch": groq_github_fetch,
    "get_project_context": groq_get_project_context
}

def call_tool_manually(tool_name: str, **kwargs) -> str:
    """
    Manually call a tool function with the given parameters.
    This can be used as a fallback if Agno's tool calling doesn't work.
    """
    if tool_name not in TOOL_REGISTRY:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    
    try:
        result = TOOL_REGISTRY[tool_name](**kwargs)
        return str(result)
    except Exception as e:
        return json.dumps({"error": f"Tool execution failed: {str(e)}"})

# Export functions
__all__ = [
    "create_groq_compatible_tools",
    "create_openai_style_tools", 
    "call_tool_manually",
    "TOOL_REGISTRY",
    "GroqToolResponse"
]