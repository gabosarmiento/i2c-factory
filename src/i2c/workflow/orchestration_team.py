# src/i2c/workflow/orchestration_team.py

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
    
    # Extract enhanced objective if available
    enhanced_objective = initial_session_state.get("objective", {})
    architectural_context = enhanced_objective.get("architectural_context", {})

    # print(f"🔍 DEBUG: Creating orchestration agent with session_state type: {type(initial_session_state)}")
    # print(f"🔍 DEBUG: Architectural context present: {bool(architectural_context)}")
        
    # Create the orchestration agent WITHOUT architectural_context parameter
    orchestration_agent = CodeOrchestrationAgent(
        session_state=initial_session_state
        # Remove this line: architectural_context=architectural_context
    )
    
    # Store architectural context in session state instead
    if architectural_context and orchestration_agent.session_state:
        orchestration_agent.session_state["architectural_context"] = architectural_context
    
    # Enhanced instructions with architectural awareness
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
        "ONLY return the JSON object above with your actual values."
    ]
    
    # Add architectural-specific instructions
    if architectural_context:
        system_type = architectural_context.get("system_type", "unknown")
        
        if system_type == "fullstack_web_app":
            instructions.extend([
                "",
                "FULLSTACK WEB APP ARCHITECTURAL RULES:",
                "- Backend files (.py) must go in backend/ directory with FastAPI structure",
                "- Frontend files (.jsx) must go in frontend/src/ directory with React structure", 
                "- Main backend: backend/main.py with proper FastAPI app",
                "- Main frontend: frontend/src/App.jsx with proper React component",
                "- Components: frontend/src/components/ as separate .jsx files",
                "- NO mixing of .jsx and .py code in same files",
                "- Ensure proper file extensions and directory structure",
            ])
    
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
        "```",
    ])
    
    # Create the team with enhanced context
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