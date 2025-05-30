from agno.team import Team
from agno.agent import Message
from i2c.agents.code_orchestration_agent import CodeOrchestrationAgent, OrchestrationResult
from builtins import llm_highest
from typing import Dict, Any, Optional, List


def build_orchestration_team(initial_session_state=None, knowledge_base=None) -> Team:
    """
    Build the orchestration team with enhanced architectural and knowledge intelligence.
    
    Args:
        initial_session_state: Optional shared session state dict
        knowledge_base: Optional knowledge base for retrieving relevant context
            Should implement Agno's knowledge base interface with retrieve_knowledge method
        
    Returns:
        Team: Configured orchestration team with knowledge capabilities
    """
    # Use empty dict if no initial state is provided
    if initial_session_state is None:
        initial_session_state = {}
    
    # Extract enhanced objective and architectural context
    enhanced_objective = initial_session_state.get("objective", {})
    architectural_context = enhanced_objective.get("architectural_context", {})

    # Create orchestration agent with session_state only (architecture will be injected into session_state)
    orchestration_agent = CodeOrchestrationAgent(
        session_state=initial_session_state
    )
    
    # Ensure architectural context is preserved in session state
    if architectural_context and orchestration_agent.session_state:
        orchestration_agent.session_state["architectural_context"] = architectural_context
        
    # Track knowledge base in session state if available
    if knowledge_base and orchestration_agent.session_state:
        orchestration_agent.session_state["knowledge_base"] = knowledge_base
    
    # === Core Agent Instructions ===
    instructions = [
        "You are the Code Evolution Team, responsible for safely and intelligently evolving code.",
        "Follow the lead of the CodeOrchestrator with full architectural intelligence.",
        "Your final response **must be strictly valid JSON**.",
        "Do not explain. Do not add text. Do not use Markdown. Output only JSON.",
        "",
        "CRITICAL: Your response must be valid JSON that matches this exact format:",
        "{",
        '  "decision": "approve",',
        '  "reason": "Clear reason for the decision",',
        '  "modifications": {},',
        '  "quality_results": {},',
        '  "sre_results": {},',
        '  "reasoning_trajectory": []',
        "}",
        "",
        "Do NOT include:",
        "- Function calls or function references",
        "- Markdown code blocks",
        "- Any text before or after the JSON",
        "- Comments or explanations",
        "",
        "ONLY return the JSON object above with your actual values.",
        "",
        # === NEW: Reflection awareness instructions ===
        "CRITICAL: When reflection context is provided, you MUST:",
        "1. Review the outcomes of previous steps (provided in the reflection summary)",
        "2. Address any incomplete or failed tasks from earlier steps",
        "3. Ensure continuity with previous modifications",
        "4. Build on successful components without overwriting blindly",
        "5. Reference how your work connects to prior steps in the reasoning_trajectory",
    ]

    # === Retrieve knowledge context if knowledge base is available ===
    knowledge_context = _retrieve_knowledge_context(
        knowledge_base=knowledge_base,
        objective=enhanced_objective,
        architectural_context=architectural_context
    )
    
    if knowledge_context:
        # Insert knowledge context into instructions
        knowledge_instructions = [
            "",
            "=== KNOWLEDGE CONTEXT ===",
            "Use the following knowledge context to inform your decisions:",
            knowledge_context,
            "",
            "When making decisions, prioritize this knowledge context alongside the architectural context.",
            "Ensure modifications align with patterns, best practices, and constraints from the knowledge context.",
            ""
        ]
        
        # Insert knowledge instructions after the core instructions but before architecture-specific rules
        instructions = instructions[:17] + knowledge_instructions + instructions[17:]

    # === Architectural-specific rules (optional) ===
    if architectural_context:
        system_type = architectural_context.get("system_type", "unknown")
        if system_type == "fullstack_web_app":
            instructions.extend([
                "",
                "FULLSTACK WEB APP ARCHITECTURAL RULES:",
                "- Backend files (.py) must go in backend/ directory with FastAPI structure",
                "- Frontend files (.jsx/.tsx) must go in frontend/src/ directory with React structure", 
                "- Main backend: backend/main.py",
                "- Main frontend: frontend/src/App.jsx",
                "- Reusable components: frontend/src/components/",
                "- NEVER mix backend and frontend code in a single file",
                "- Maintain clear folder boundaries",
            ])

    # === Format example comes last to guide correct output ===
    instructions.extend([
        "",
        "Expected JSON format:",
        "```json",
        '{',
        '  "decision": "approve",',
        '  "reason": "All quality and operational checks passed with architectural compliance",',
        '  "modifications": { "backend/main.py": "Created FastAPI app", "frontend/src/App.jsx": "Created React component" },',
        '  "quality_results": { "lint": "passed", "types": "passed", "security": "passed" },',
        '  "sre_results": { "uptime_check": "passed" },',
        '  "reasoning_trajectory": [ { "step": "Final Decision", "description": "All gates passed with architectural validation", "success": true } ]',
        '}',
        "```"
    ])

    # === Team creation with all configurations ===
    return Team(
        name="CodeEvolutionTeam",
        members=[orchestration_agent],
        mode="coordinate",
        model=llm_highest,
        session_state=initial_session_state,
        instructions=instructions,
        response_model=OrchestrationResult,
        show_tool_calls=False,
        debug_mode=False,
        markdown=False,
        enable_agentic_context=False,
        tools=[]
    )


def _retrieve_knowledge_context(
    knowledge_base, 
    objective: Dict[str, Any], 
    architectural_context: Dict[str, Any]
) -> str:
    """
    Retrieve relevant knowledge context from the knowledge base following Agno patterns.
    
    This function performs multi-step retrieval using Agno's knowledge retrieval patterns:
    1. Primary task-based retrieval (comprehensive context)
    2. Architectural pattern-specific retrieval (specialized context)
    3. Implementation-specific retrieval (detailed context)
    
    Args:
        knowledge_base: Knowledge base object with retrieve_knowledge method
        objective: The current objective dictionary
        architectural_context: The architectural context dictionary
        
    Returns:
        str: Synthesized knowledge context, or empty string if unavailable
    """
    if not knowledge_base or not hasattr(knowledge_base, 'retrieve_knowledge'):
        return ""
    
    # Import canvas for logging if available (following Agno patterns)
    try:
        from i2c.cli.controller import canvas
    except ImportError:
        # Fallback canvas for graceful degradation
        class DummyCanvas:
            def info(self, msg): print(f"[INFO] {msg}")
            def warning(self, msg): print(f"[WARNING] {msg}")
            def success(self, msg): print(f"[SUCCESS] {msg}")
            def error(self, msg): print(f"[ERROR] {msg}")
        canvas = DummyCanvas()
    
    try:
        # Extract task from objective for primary query
        task = objective.get("task", "")
        if not task:
            return ""
            
        # Following Agno's multi-query pattern for comprehensive context
        system_type = architectural_context.get("system_type", "unknown")
        architecture_pattern = architectural_context.get("architecture_pattern", "unknown")
        
        # Build composite query for main task (primary context)
        main_query = f"software development best practices for {task}"
        if system_type != "unknown":
            main_query += f" in {system_type} applications"
        if architecture_pattern != "unknown":
            main_query += f" using {architecture_pattern} architecture"
            
        # Log the retrieval attempt
        canvas.info(f"[KNOWLEDGE] Retrieving context for orchestration: {main_query[:100]}...")
        
        # Primary retrieval - comprehensive context
        # Using higher limit to maximize token usage (Agno pattern for comprehensive context)
        main_chunks = knowledge_base.retrieve_knowledge(
            query=main_query,
            limit=8  # Retrieve more chunks for comprehensive context
        )
        
        if not main_chunks:
            canvas.warning("[KNOWLEDGE] No relevant knowledge found for main query")
            return ""
            
        # Secondary retrieval - architectural patterns (specialized context)
        pattern_query = f"{architecture_pattern} architecture patterns and best practices"
        pattern_chunks = knowledge_base.retrieve_knowledge(
            query=pattern_query,
            limit=3
        )
        
        # Tertiary retrieval - implementation details (detailed context)
        implementation_query = f"implementation tips for {task}"
        implementation_chunks = knowledge_base.retrieve_knowledge(
            query=implementation_query,
            limit=3
        )
        
        # Following Agno's deduplication pattern for knowledge integration
        all_chunks = []
        seen_content = set()
        
        # Process main chunks first (highest priority)
        for chunk in main_chunks:
            content = chunk.get("content", "")
            if content and content not in seen_content:
                all_chunks.append(chunk)
                seen_content.add(content)
                
        # Add architecture chunks next
        for chunk in pattern_chunks or []:
            content = chunk.get("content", "")
            if content and content not in seen_content:
                all_chunks.append(chunk)
                seen_content.add(content)
                
        # Add implementation chunks last
        for chunk in implementation_chunks or []:
            content = chunk.get("content", "")
            if content and content not in seen_content:
                all_chunks.append(chunk)
                seen_content.add(content)
        
        # Format the context for insertion (Agno's structured knowledge pattern)
        formatted_chunks = []
        for i, chunk in enumerate(all_chunks):
            source = chunk.get("source", "Unknown")
            content = chunk.get("content", "").strip()
            
            # Keep chunks relatively short to avoid context overflow
            # Following Agno's adaptive chunking pattern
            if len(content) > 1000:
                content = content[:1000] + "..."
                
            formatted_chunks.append(f"[Knowledge {i+1}] {source}:\n{content}")
        
        # Combine all chunks into a single context
        combined_context = "\n\n".join(formatted_chunks)
        
        # Log stats about retrieved knowledge (Agno logging pattern)
        token_estimate = len(combined_context.split()) * 1.3  # Rough token estimate
        canvas.success(f"[KNOWLEDGE] Retrieved {len(all_chunks)} chunks " +
                      f"(~{int(token_estimate)} tokens) for orchestration context")
        
        return combined_context
        
    except Exception as e:
        # Following Agno's graceful error handling pattern
        canvas.error(f"[KNOWLEDGE] Error retrieving knowledge context: {e}")
        return ""