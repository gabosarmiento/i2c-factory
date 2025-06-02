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
from i2c.utils import deprecated

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

@deprecated("Use direct agent approach instead")
def _create_modular_retrieval_team(session_state: Dict[str, Any] = None) -> Team:
    """
    Build a modular team: 1 agent per tool, plus analyzer and implementer (modifier). All members have access to call the tool agents as helpers.
    """
    print(f"[DEBUG] _create_modular_retrieval_team ENTRY")
    print(f"[DEBUG] session_state keys: {list(session_state.keys()) if session_state else 'None'}")
    
    try:
        print(f"[DEBUG] Building tool agents...")
        tool_agents = _build_modular_tool_agents(session_state)
        print(f"[DEBUG] Tool agents created: {list(tool_agents.keys())}")
        
        # Tool agents get exposed to the main agents as callable helpers
        retrieval_helpers = list(tool_agents.values())
        print(f"[DEBUG] Retrieval helpers: {len(retrieval_helpers)}")

        print(f"[DEBUG] Creating analyzer agent...")
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
        print(f"[DEBUG] Analyzer agent created")

        print(f"[DEBUG] Creating implementer agent...")
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
        print(f"[DEBUG] Implementer agent created")

        print(f"[DEBUG] Creating team...")
        team = Team(
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
        print(f"[DEBUG] Team created successfully")
        print(f"[DEBUG] Team members: {[m.name for m in team.members]}")
        
        return team
        
    except Exception as e:
        print(f"[DEBUG] Error in _create_modular_retrieval_team: {e}")
        import traceback
        traceback.print_exc()
        raise

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
    
    # ADD DEBUG INFO:
    use_retrieval = shared.get("use_retrieval_tools", False)
    test_mode = shared.get("test_mode", False)
    print(f"[DEBUG] use_retrieval_tools: {use_retrieval}")
    print(f"[DEBUG] test_mode: {test_mode}")
    
    # REMOVE the test_mode check - let it use modern path
    if use_retrieval:
        print("[DEBUG] Using modular modification path")
        return _apply_modular_modification(modification_step, project_path, retrieved_context, shared)
    
    print("[DEBUG] Using legacy modification path")
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
    print(f"[DEBUG] _apply_modular_modification ENTRY")
    print(f"[DEBUG] step: {step}")
    print(f"[DEBUG] project_path: {project_path}")
    
    try:
        print(f"[DEBUG] Building base context...")
        
        # === Enhanced: Get knowledge context and enhance agents ===
        knowledge_context = _get_principle_enhanced_context(session_state, step)
        
        base_context = {
            "task": step.get("what", ""),
            "file": step.get("file", ""),
            "how": step.get("how", ""),
            "context_hint": retrieved_context[:200] if retrieved_context else ""
        }
        
        # Add knowledge context if available
        if knowledge_context:
            base_context["knowledge_hint"] = knowledge_context
        
        print(f"[DEBUG] Base context built: {len(str(base_context))} chars")
        
        print(f"[DEBUG] Creating modular retrieval team...")
        # NEW: Create team with knowledge enhancement
        team = _create_modular_retrieval_team(session_state)
        print(f"[DEBUG] Team created: {type(team)}")
        print(f"[DEBUG] Team members: {len(team.members) if hasattr(team, 'members') else 'unknown'}")
        
        print(f"[DEBUG] Checking team enhancement...")
        # NEW: Enhance team agents with knowledge
        if hasattr(team, 'members') and session_state.get("retrieved_context"):
            from i2c.agents.core_team.enhancer import AgentKnowledgeEnhancer
            enhancer = AgentKnowledgeEnhancer()
            
            for member in team.members:
                if hasattr(member, 'name'):
                    agent_type = "analyzer" if "analyzer" in member.name.lower() else "implementer"
                    enhancer.enhance_agent_with_knowledge(
                        member, session_state["retrieved_context"], agent_type, step.get("what", "")
                    )
                    print(f"🧠 Enhanced {member.name} with knowledge patterns")
        
        print(f"[DEBUG] Converting to JSON...")
        team_prompt = json.dumps(base_context)
        print(f"[DEBUG] Team prompt length: {len(team_prompt)} chars")
        print(f"[DEBUG] Team prompt preview: {team_prompt[:100]}...")
        
        print(f"[DEBUG] About to call team.run()...")
        # BYPASS hanging team - use direct agent instead
        try:
            print(f"[DEBUG] Using direct agent instead of team...")
            from i2c.agents.core_agents import get_rag_enabled_agent
            direct_agent = get_rag_enabled_agent("code_builder", session_state=session_state)
            
            simple_prompt = f"Modify the file {step.get('file')} to {step.get('what')}. {step.get('how')}. Return the complete modified file content."
            response = direct_agent.run(simple_prompt)
            print(f"[DEBUG] Direct agent completed!")
            
        except Exception as direct_error:
            print(f"[DEBUG] Direct agent failed: {direct_error}")
            # Fallback to legacy
            return _apply_legacy(step, project_path, retrieved_context, session_state)

        print(f"[DEBUG] Response type: {type(response)}")
        
        content = getattr(response, "content", str(response))
        print(f"[DEBUG] Response content type: {type(content)}")
        print(f"[DEBUG] Response content preview: {str(content)[:200]}...")
        
        print(f"[DEBUG] Parsing response...")
        result = robust_json_parse(content)
        print(f"[DEBUG] Parsed result: {type(result)}")
        
        file_rel = result.get("file_path", step.get("file", ""))
        file_path = project_path / file_rel
        
        print(f"[DEBUG] Target file: {file_path}")
        
        original = ""
        if file_path.exists() and step.get("action") != "create":
            try:
                original = file_path.read_text(encoding="utf-8")
                print(f"[DEBUG] Read original file: {len(original)} chars")
            except Exception as read_error:
                print(f"[DEBUG] Error reading original file: {read_error}")
                pass
        
        modified = result.get("modified", "")
        print(f"[DEBUG] Modified content length: {len(modified)} chars")
        
        if not modified or len(modified.strip()) < 10:
            print(f"[DEBUG] Modified content too short, creating fallback...")
            if step.get("action") == "create":
                modified = f"""# {step.get('what', 'New file')}
\n"""
            else:
                modified = original + f"\n\n# TODO: {step.get('what', 'Add functionality')}\n"
        
        if modified:
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                print(f"[DEBUG] About to write file: {file_path}")
                print(f"[DEBUG] Modified content preview: {modified[:100]}...")
                
                file_path.write_text(modified, encoding="utf-8")
                
                # Verify write
                if file_path.exists():
                    written_content = file_path.read_text()
                    print(f"[DEBUG] Actually written: {written_content[:100]}...")
                    print(f"[DEBUG] Write successful: {len(written_content)} chars")
                else:
                    print(f"[DEBUG] ERROR: File not found after write")
                
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
                    
            except Exception as write_error:
                print(f"[DEBUG] Write error: {write_error}")
        
        session_state.setdefault("modified_files", {})[file_rel] = modified
        
        class PatchObject:
            def __init__(self, unified_diff: str):
                self.unified_diff = unified_diff
        
        print(f"[DEBUG] Returning PatchObject with {len(modified)} chars")
        return PatchObject(unified_diff=modified)
        
    except Exception as e:
        print(f"[DEBUG] Modular modification error: {e}")
        import traceback
        traceback.print_exc()
        print(f"[DEBUG] Falling back to legacy...")
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