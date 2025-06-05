from agno.team import Team
from agno.agent import Message
from i2c.agents.code_orchestration_agent import CodeOrchestrationAgent, OrchestrationResult
from builtins import llm_highest
from typing import Dict, Any, Optional, List

try:
    from i2c.cli.controller import canvas
except ImportError:
    class DummyCanvas:
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def success(self, msg): print(f"[SUCCESS] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
    canvas = DummyCanvas()


def build_orchestration_team(session_state=None) -> Team:
    """
    Build the orchestration team with enhanced architectural and knowledge intelligence.
    """
    
    # Extract knowledge_base from session_state (AGNO pattern)
    extracted_knowledge_base = None
    if session_state and 'knowledge_base' in session_state:
        extracted_knowledge_base = session_state['knowledge_base']
    
    # Use empty dict if no initial state is provided
    if session_state is None:
        session_state = {}
    
    # Extract enhanced objective and architectural context
    enhanced_objective = session_state.get("objective", {})
    architectural_context = enhanced_objective.get("architectural_context", {})

    # Create orchestration agent with session_state
    orchestration_agent = CodeOrchestrationAgent(session_state=session_state)
    
    # === Core Agent Instructions ===
    instructions = [
        "You are the Code Evolution Team, responsible for safely and intelligently evolving code.",
        "Follow the lead of the CodeOrchestrator with full architectural intelligence.",
        "PROCESS THE REQUEST DIRECTLY - Do not delegate, you are the executor.",
        "Analyze the task, architecture, and constraints provided and make code modification decisions.",
        "Your final response **must be strictly valid JSON**.",
        "Do not explain. Do not add text. Do not use Markdown. Do not use function calls.",
        "Do not use <function=...> syntax. Output ONLY the JSON object.",
        "NO function calls, NO tool usage, NO additional formatting.",
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
        "CRITICAL: When reflection context is provided, you MUST:",
        "1. Review the outcomes of previous steps (provided in the reflection summary)",
        "2. Address any incomplete or failed tasks from earlier steps", 
        "3. Ensure continuity with previous modifications",
        "4. Build on successful components without overwriting blindly",
        "5. Reference how your work connects to prior steps in the reasoning_trajectory",
    ]

    # === Retrieve knowledge context if knowledge base is available ===
    knowledge_context = ""
    if extracted_knowledge_base:
        knowledge_context = _retrieve_knowledge_context(
            knowledge_base=extracted_knowledge_base,
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
        instructions = instructions[:25] + knowledge_instructions + instructions[25:]

    # === Architectural-specific rules ===
    if architectural_context:
        system_type = architectural_context.get("system_type", "unknown")
        if system_type == "fullstack_web_app":
            arch_instructions = [
                "",
                "FULLSTACK WEB APP ARCHITECTURAL RULES:",
                "- Backend files (.py) must go in backend/ directory with FastAPI structure",
                "- Frontend files (.jsx/.tsx) must go in frontend/src/ directory with React structure", 
                "- Main backend: backend/main.py",
                "- Main frontend: frontend/src/App.jsx",
                "- Reusable components: frontend/src/components/",
                "- NEVER mix backend and frontend code in a single file",
                "- Maintain clear folder boundaries",
            ]
            instructions.extend(arch_instructions)

    # === Format example comes last ===
    format_instructions = [
        "",
        "CRITICAL OUTPUT FORMAT:",
        "Return ONLY this exact JSON structure with your values:",
        '{',
        '  "decision": "approve",',
        '  "reason": "Clear reason for the decision",',
        '  "modifications": {"backend/file.py": "description"},',
        '  "quality_results": {"lint": "passed"},',
        '  "sre_results": {"health": "passed"},',
        '  "reasoning_trajectory": [{"step": "Analysis", "description": "Analyzed requirements", "success": true}]',
        '}',
        "",
        "CRITICAL: reasoning_trajectory must be array of objects with step, description, success fields.",
        "NO function calls. NO explanations. NO markdown. ONLY the JSON object above."
    ]
    instructions.extend(format_instructions)

    # === Team creation ===
    return Team(
        name="CodeEvolutionTeam",
        members=[orchestration_agent],
        mode="collaborate",
        model=llm_highest,
        session_state=session_state,
        knowledge=extracted_knowledge_base,
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
    Retrieve relevant knowledge context from the knowledge base.
    """
    if not knowledge_base or not hasattr(knowledge_base, 'retrieve_knowledge'):
        canvas.warning("[KNOWLEDGE] No knowledge available for orchestration team")
        return ""
    
    try:
        # Extract task from objective for primary query
        task = objective.get("task", "")
        if not task:
            return ""
            
        # Build comprehensive query
        system_type = architectural_context.get("system_type", "unknown")
        architecture_pattern = architectural_context.get("architecture_pattern", "unknown")
        
        main_query = f"software development best practices for {task}"
        if system_type != "unknown":
            main_query += f" in {system_type} applications"
        if architecture_pattern != "unknown":
            main_query += f" using {architecture_pattern} architecture"
            
        canvas.info(f"[KNOWLEDGE] Retrieving context: {main_query[:100]}...")
        
        # Retrieve comprehensive context
        main_chunks = knowledge_base.retrieve_knowledge(
            query=main_query,
            limit=8
        )
        
        if not main_chunks:
            canvas.warning("[KNOWLEDGE] No relevant knowledge found")
            return ""
        
        # Format the context
        formatted_chunks = []
        for i, chunk in enumerate(main_chunks):
            source = chunk.get("source", "Unknown")
            content = chunk.get("content", "").strip()
            
            if len(content) > 1000:
                content = content[:1000] + "..."
                
            formatted_chunks.append(f"[Knowledge {i+1}] {source}:\n{content}")
        
        combined_context = "\n\n".join(formatted_chunks)
        canvas.success(f"[KNOWLEDGE] Retrieved {len(main_chunks)} chunks for orchestration")
        
        return combined_context
        
    except Exception as e:
        canvas.error(f"[KNOWLEDGE] Error retrieving context: {e}")
        return ""