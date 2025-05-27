from agno.team import Team
from i2c.agents.code_orchestration_agent import CodeOrchestrationAgent, OrchestrationResult
from builtins import llm_highest


def build_orchestration_team(initial_session_state=None) -> Team:
    """
    Build the orchestration team with enhanced architectural intelligence.
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
