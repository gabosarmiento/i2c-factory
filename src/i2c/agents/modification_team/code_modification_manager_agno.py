# /src/i2c/agents/modification_team/code_modification_manager_agno.py
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from agno.agent import Agent
from agno.team import Team

# Import the Groq-compatible retrieval tools
from .groq_compatible_tools import create_groq_compatible_tools, call_tool_manually
from i2c.utils.json_extraction import extract_json
from i2c.llm_providers import llm_middle, llm_highest, llm_deepseek
from i2c.agents.sre_team.multilang_unit_test import unit_test_generator

# Legacy implementations (for fallback)
from .code_modification_manager_agno_legacy import (
    build_code_modification_team as _create_agno_modification_team_legacy,
    apply_modification as _apply_legacy
)

# === LEAN KNOWLEDGE INTEGRATION ===
def _should_use_knowledge(modification_step: Dict[str, Any]) -> bool:
    """Smart gating - only use knowledge when it actually helps"""
    task = modification_step.get("what", "").lower()
    
    # Only use knowledge for complex tasks that benefit from patterns
    knowledge_worthy = [
        "create", "implement", "build", "design", "architecture", 
        "pattern", "best practice", "optimize", "refactor"
    ]
    
    return any(keyword in task for keyword in knowledge_worthy) and len(task) > 10

def _get_principle_enhanced_context(session_state: Dict[str, Any], 
                                  modification_step: Dict[str, Any]) -> str:
    """Transform knowledge using deep contextual understanding"""
    knowledge_base = session_state.get("knowledge_base")
    if not knowledge_base or not _should_use_knowledge(modification_step):
        return ""
    
    try:
        task = modification_step.get("what", "")
        file_ext = Path(modification_step.get("file", "")).suffix.lower()
        
        # Multi-modal knowledge retrieval (like Claude)
        knowledge_queries = {
            "core_patterns": f"core patterns best practices {task}",
            "error_patterns": f"common mistakes avoid {task}",
            "context_patterns": f"when to use {task}",
            "optimization": f"optimize performance {task}",
            "integration": f"integrate {task} with existing code"
        }
        
        # Add language context
        if file_ext == ".py":
            for key in knowledge_queries:
                knowledge_queries[key] += " python"
        elif file_ext in [".js", ".jsx"]:
            for key in knowledge_queries:
                knowledge_queries[key] += " javascript"
        
        # Retrieve all knowledge types
        all_knowledge = []
        for query_type, query in knowledge_queries.items():
            chunks = knowledge_base.retrieve_knowledge(query=query, limit=2)
            for chunk in chunks:
                chunk["query_type"] = query_type  # Tag the knowledge type
                all_knowledge.append(chunk)
        
        # Use deep principle transformer
        from i2c.agents.knowledge.principle_transformer import DeepPrincipleTransformer
        deep_transformer = DeepPrincipleTransformer()
        
        # Extract contextual patterns
        contextual_patterns = deep_transformer.extract_contextual_patterns(all_knowledge)
        
        # Synthesize into expert-level guidance
        expert_guidance = deep_transformer.synthesize_deep_expertise(contextual_patterns)
        
        if expert_guidance:
            return f"""
As an expert in {task}, you have internalized deep knowledge that guides your professional judgment:

{expert_guidance}

Apply this expertise naturally - reason through the context, consider edge cases, and implement the optimal solution."""
        
    except Exception as e:
        print(f"Error in deep knowledge processing: {e}")
        # Fallback to simple approach
        pass
    
    return ""

def _transform_to_principles(patterns, antipatterns, decisions, task):
    """Convert raw knowledge chunks into internalized expertise"""
    
    principles = []
    
    # Extract core principles from patterns
    for chunk in patterns:
        content = chunk.get("content", "")
        # Extract actionable insights
        if "always" in content.lower() or "must" in content.lower():
            principles.append(f"CORE PRINCIPLE: {content[:200]}")
        elif "pattern" in content.lower():
            principles.append(f"APPLY PATTERN: {content[:200]}")
    
    # Extract warnings from anti-patterns  
    for chunk in antipatterns:
        content = chunk.get("content", "")
        if "avoid" in content.lower() or "don't" in content.lower():
            principles.append(f"AVOID: {content[:150]}")
    
    # Extract decision guidance
    for chunk in decisions:
        content = chunk.get("content", "")
        if "when" in content.lower() or "if" in content.lower():
            principles.append(f"DECIDE: {content[:150]}")
    
    if not principles:
        return ""
    
    # Format as internalized expertise
    expertise = f"""
As an expert in {task}, your internalized knowledge guides you to:

{chr(10).join(f"• {p}" for p in principles[:5])}

Apply this expertise naturally in your implementation."""
    
    return expertise


# === LEAN KNOWLEDGE INTEGRATION END ===

def _inject_knowledge_into_prompt(base_prompt: str, knowledge_context: str) -> str:
    """
    Inject knowledge context into the modification prompt.
    
    Args:
        base_prompt: Original prompt
        knowledge_context: Retrieved knowledge context
        
    Returns:
        Enhanced prompt with knowledge context
    """
    if not knowledge_context:
        return base_prompt
        
    enhanced_prompt = f"""{base_prompt}

=== KNOWLEDGE CONTEXT ===
Use the following relevant knowledge to inform your code modifications:

{knowledge_context}

Apply patterns, best practices, and examples from the knowledge context above.
Ensure your modifications align with the provided knowledge.
=== END KNOWLEDGE CONTEXT ==="""
    
    return enhanced_prompt
# === KNOWLEDGE INTEGRATION END ===

def _build_modular_tool_agents(session_state: Dict[str, Any] = None) -> Dict[str, Agent]:
    """
    Define one lightweight agent per retrieval tool. Each tool agent is only responsible for one tool and returns strict JSON.
    """
    retrieval_tools = create_groq_compatible_tools(session_state)
    vector_retrieve_tool = [t for t in retrieval_tools if t.name == "vector_retrieve"][0]
    get_project_context_tool = [t for t in retrieval_tools if t.name == "get_project_context"][0]
    github_fetch_tool = [t for t in retrieval_tools if t.name == "github_fetch"][0]

    vector_agent = Agent(
        name="VectorRetrieverAgent",
        model=llm_middle,
        tools=[vector_retrieve_tool],
        reasoning=False,  # Disable reasoning to prevent hanging
        instructions="""
You are a vector retrieval specialist.
Use ONLY the vector_retrieve tool to answer queries about code, knowledge, or both. Respond strictly in JSON.
Example:
{"matches": [...], "source": "knowledge", "query": "flask decorator"}
"""
    )
    project_agent = Agent(
        name="ProjectContextAgent",
        model=llm_middle,
        tools=[get_project_context_tool],
        reasoning=False,  # Disable reasoning to prevent hanging
        instructions="""
You are a project structure specialist.
Use ONLY the get_project_context tool. Given a project path and a focus term, return project file info as JSON.
Example:
{"files": [...], "focus": "model", "project_path": "."}
"""
    )
    github_agent = Agent(
        name="GitHubFetcherAgent",
        model=llm_middle,
        tools=[github_fetch_tool],
        reasoning=False,  # Disable reasoning to prevent hanging
        instructions="""
You fetch files from GitHub. Use ONLY the github_fetch tool with repo_path and file_path, return JSON.
Example:
{"file_content": "...", "repo_path": "agno-agi/agno", "file_path": "examples/basic_agent.py"}
"""
    )
    return {
        "vector": vector_agent,
        "project": project_agent,
        "github": github_agent,
    }

def _create_modular_retrieval_team(session_state: Dict[str, Any] = None) -> Team:
    """
    Build a modular team: 1 agent per tool, plus analyzer and implementer (modifier). All members have access to call the tool agents as helpers.
    """
    tool_agents = _build_modular_tool_agents(session_state)
    # Tool agents get exposed to the main agents as callable helpers
    retrieval_helpers = list(tool_agents.values())

    analyzer = Agent(
        name="AnalyzerAgent",
        model=llm_highest,  # Good at reasoning
        tools=retrieval_helpers,
        reasoning=False,  # Disable reasoning to prevent hanging
        instructions="""
You are a senior code analyst with access to three tool specialists: VectorRetrieverAgent, ProjectContextAgent, GitHubFetcherAgent.

- When analyzing a modification request, call the relevant tool agent as needed:
  - Use vector retrieval for concepts, function names, or examples.
  - Use project context for structure, file listings, or focus terms.
  - Use GitHub fetch for external reference code.
- Combine results and produce a concise JSON plan:
{"analysis": "...", "sources_used": [...], "plan": ["step1", ...], "recommend_tools": ["vector", "github"]}
Respond strictly in JSON.
"""
    )

    implementer = Agent(
        name="ImplementerAgent",
        model=llm_highest,  # Focused on quality output
        tools=retrieval_helpers,
        reasoning=False,  # Disable reasoning to prevent hanging
        instructions="""
You are an advanced implementer with access to tool agents and a code analysis plan.

- You may call any tool agent as needed (vector/project/github), but be concise.
- Generate and return the full target code (and unified diff if needed).
- Respond strictly in JSON:
{"file_path": "...", "original": "...", "modified": "..."}
If you are stuck, use the tool agents to gather additional examples.
"""
    )

    return Team(
        name="ModularRetrievalModificationTeam",
        model=llm_middle,
        members=[analyzer, implementer],
        mode="coordinate",
        instructions="""
You are a fast, robust, modular modification team.

- Each agent has independent responsibility.
- Use tool agents as needed, do not call tools directly.
- Respond strictly in JSON for each step.
- The team should work for multi-language and multi-step scenarios.
""",
        share_member_interactions=True,
        enable_agentic_context=False,  # Minimal context window
        session_state=session_state,
    )

def robust_json_parse(content: Union[str, dict, list]) -> dict:
    from i2c.utils.json_extraction import extract_json_with_fallback
    
    if isinstance(content, dict):
        return content
    if isinstance(content, list) and content:
        return content[0] if isinstance(content[0], dict) else {"modified": str(content[0])}
    if isinstance(content, str):
        return extract_json_with_fallback(content, {"modified": str(content)[:1000]})
    
    return {"modified": str(content)[:1000]}

def apply_modification(
    modification_step: Dict[str, Any],
    project_path: Path,
    retrieved_context: str = "",
    session_state: Optional[Dict[str, Any]] = None
) -> Any:
    print("[DEBUG][apply_modification] step:", modification_step)
    print("[DEBUG][apply_modification] project_root:", project_path)
    shared = session_state or {}
    
    # Check for test mode to force legacy path
    if shared.get("test_mode", False):
        print("[DEBUG] Test mode - forcing legacy path")
        return _apply_legacy(modification_step, project_path, retrieved_context, shared)
    
    use_retrieval = shared.get("use_retrieval_tools", False)
    if use_retrieval:
        return _apply_modular_modification(modification_step, project_path, retrieved_context, shared)
    return _apply_legacy(modification_step, project_path, retrieved_context, shared)

def build_code_modification_team(*, session_state: Dict[str, Any] = None, **kwargs) -> Team:
    """Build code modification team - lean approach, no preloading overhead"""
    shared = session_state or {}
    use_retrieval = shared.get("use_retrieval_tools", False)
    if use_retrieval:
        return _create_modular_retrieval_team(session_state)
    return _create_agno_modification_team_legacy()

def _apply_modular_modification(
    step: Dict[str, Any],
    project_path: Path,
    retrieved_context: str,
    session_state: Dict[str, Any]
) -> Any:
    try:
        # === LEAN: Get minimal knowledge context (max 1 API call) ===
        knowledge_context = _get_principle_enhanced_context(session_state, step)
        
        base_context = {
            "task": step.get("what", ""),
            "file": step.get("file", ""),
            "how": step.get("how", ""),
            "context_hint": retrieved_context[:200] if retrieved_context else ""
        }
        
        # Add knowledge only if we got some
        if knowledge_context:
            base_context["knowledge_hint"] = knowledge_context  # Renamed to hint - it's minimal
        
        team = _create_modular_retrieval_team(session_state)
        team_prompt = json.dumps(base_context)
        
        response = team.run(team_prompt)
        content = getattr(response, "content", str(response))
        result = robust_json_parse(content)
        file_rel = result.get("file_path", step.get("file", ""))
        file_path = project_path / file_rel
        original = ""
        if file_path.exists() and step.get("action") != "create":
            try:
                original = file_path.read_text(encoding="utf-8")
            except:
                pass
        modified = result.get("modified", "")
        if not modified or len(modified.strip()) < 10:
            if step.get("action") == "create":
                modified = f"""# {step.get('what', 'New file')}
\n"""
            else:
                modified = original + f"\n\n# TODO: {step.get('what', 'Add functionality')}\n"
        if modified:
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(modified, encoding="utf-8")
                # Auto-generate unit tests using enhanced multi-language generator
                try:
                    # Only for files that aren't already test files
                    if not unit_test_generator._is_test_file(file_rel):
                        print(f"🧪 Generating unit tests for {file_rel}...")
                        
                        # Create temp code map for test generation
                        temp_code_map = {file_rel: modified}
                        
                        # Generate tests using multi-language generator
                        code_map_with_tests = unit_test_generator.generate_tests(temp_code_map)
                        
                        # Write any new test files
                        for test_file_path, test_content in code_map_with_tests.items():
                            if test_file_path != file_rel:  # Skip the original file
                                test_full_path = project_path / test_file_path
                                test_full_path.parent.mkdir(parents=True, exist_ok=True)
                                test_full_path.write_text(test_content, encoding="utf-8")
                                
                                # Track in session state
                                session_state.setdefault("modified_files", {})[test_file_path] = test_content
                                
                                print(f"✅ Auto-generated unit test: {test_file_path}")
                                
                except Exception as e:
                    print(f"⚠️ Unit test generation failed (non-blocking): {e}")
            except Exception as e:
                print(f"Write error: {e}")
        session_state.setdefault("modified_files", {})[file_rel] = modified
        class PatchObject:
            def __init__(self, unified_diff: str):
                self.unified_diff = unified_diff
        return PatchObject(unified_diff=modified)
    except Exception as e:
        print(f"Modular modification error: {e}")
        return _apply_legacy(step, project_path, retrieved_context, session_state)

# Manual tool usage

def quick_search(query: str, search_type: str = "vector") -> str:
    try:
        if search_type == "vector":
            return call_tool_manually("vector_retrieve", query=query, limit=2)
        elif search_type == "files":
            return call_tool_manually("get_project_context", project_path=".", focus=query)
        else:
            return call_tool_manually("vector_retrieve", query=query, source="both", limit=3)
    except:
        return "{}"

def get_knowledge_cache_stats() -> dict:
    """Get simple knowledge usage stats"""
    return {"message": "Lean knowledge integration - minimal overhead"}

def clear_knowledge_cache():
    """No-op for lean implementation"""
    pass

__all__ = [
    "apply_modification",
    "build_code_modification_team", 
    "quick_search"
]