from i2c.bootstrap import initialize_environment
initialize_environment()

import asyncio
from i2c.agents.knowledge.context_evolution_team import build_context_evolution_team
from agno.agent import Message

async def test_context_evolution_team():
    """Test the context evolution team in isolation"""
    
    print("=== TESTING CONTEXT EVOLUTION TEAM ===")
    
    # Create test contexts
    previous_context = {
        "documentation": {"references": [
            {"source": "agno_guide.pdf", "content": "Previous AGNO patterns and agent setup instructions. " * 100},
            {"source": "old_patterns.md", "content": "Legacy implementation patterns that may be outdated. " * 80}
        ]},
        "project_structure": {"files": ["backend/main.py", "backend/api/routes.py", "frontend/App.jsx"]},
        "code_context": {"context": "Existing FastAPI backend with user authentication endpoints. " * 50},
        "key_decisions": ["Used FastAPI for backend", "React for frontend", "JWT authentication"],
        "context_size": 8500
    }

    new_context = {
        "documentation": {"references": [
            {"source": "agno_guide.pdf", "content": "Previous AGNO patterns and agent setup instructions. " * 100},  # Duplicate
            {"source": "new_advanced.pdf", "content": "Advanced AGNO team coordination and delegation patterns. " * 120},
            {"source": "latest_features.md", "content": "Latest AGNO collaboration features and structured outputs. " * 90}
        ]},
        "project_structure": {"files": ["backend/main.py", "backend/api/routes.py", "frontend/App.jsx", "backend/api/posts.py"]},
        "code_context": {"context": "Extended FastAPI backend with posts endpoints and team collaboration. " * 60},
        "new_decisions": ["Added posts API", "Implemented team collaboration", "Used structured outputs"],
        "context_size": 12000
    }
    
    # Build the team with session state
    test_session_state = {
        "retrieved_context": previous_context,
        "embed_model": None,
        "db_path": "./data/lancedb"
    }

    print(f"\n=== BUILDING TEAM ===")
    team = build_context_evolution_team(session_state=test_session_state)
    print(f"Team created: {team.name}")
    print(f"Team mode: {team.mode}")
    print(f"Team response_model: {team.response_model}")
    print(f"Team members: {[member.name for member in team.members]}")
    print(f"Team session_state keys: {list(test_session_state.keys())}")
    # Test request
    test_request = f"""
    Task: Add new API endpoints using advanced AGNO patterns
    Previous context size: {len(str(previous_context))} chars
    New context size: {len(str(new_context))} chars

    Context summary:
    - Previous: FastAPI backend with auth, React frontend
    - New: Added posts API, team collaboration, structured outputs
    - Files: backend/main.py, backend/api/routes.py, backend/api/posts.py, frontend/App.jsx

    Team: evolve context intelligently, return JSON only.
    """

    print(f"Input previous context size: {len(str(previous_context))}")
    print(f"Input new context size: {len(str(new_context))}")

    # ADD DETAILED LOGGING HERE:
    print(f"\n=== FULL REQUEST TO TEAM ===")
    print(f"Request content: {test_request[:500]}...")
    print(f"Request length: {len(test_request)}")

    # Run the team
    message = Message(role="user", content=test_request)
    print(f"\n=== SENDING MESSAGE TO TEAM ===")
    print(f"Message type: {type(message)}")
    print(f"Message role: {message.role}")
    print(f"Message content length: {len(message.content)}")

    result = await team.arun(message)

    print(f"\n=== TEAM RESULT ===")
    print(f"Result type: {type(result)}")
    print(f"Content: {result.content if hasattr(result, 'content') else result}")
    if hasattr(result, 'content'):
        content = result.content
        print(f"Content type: {type(content)}")
        
        if hasattr(content, 'evolved_context'):
            print(f"Project summary: {content.conversation_summary[:100]}...")
            print(f"Current state keys: {list(content.current_state.keys())}")
            print(f"Decisions made: {len(content.decisions_made)}")
            print(f"Patterns established: {len(content.patterns_established)}")
            print(f"Context size before: {content.context_size_before}")
            print(f"Context size after: {content.context_size_after}")
            print(f"Evolution reasoning: {content.evolution_reasoning[:200]}...")
            print(f"Evolved context size: {len(str(content.evolved_context))}")
        else:
            print(f"Content: {content}")
    else:
        print(f"Raw result: {result}")

if __name__ == "__main__":
    asyncio.run(test_context_evolution_team())