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

    # === SIMPLE: Use retrieved_context if available ===
    retrieved_context = session_state.get("retrieved_context", "")
    if retrieved_context:
        # Add concise knowledge context without bloat
        knowledge_instructions = [
            "",
            "=== KNOWLEDGE CONTEXT ===",
            f"Relevant patterns and best practices:",
            retrieved_context[:1000] + "..." if len(retrieved_context) > 1000 else retrieved_context,
            ""
        ]
        
        # Insert after core instructions
        instructions = instructions[:25] + knowledge_instructions + instructions[25:]
        canvas.success(f"✅ Knowledge context added ({len(retrieved_context)} chars, trimmed to 1000)")
    else:
        canvas.warning("⚠️ No retrieved_context available for orchestration team")

    # === Architectural-specific rules ===
    system_type = session_state.get("system_type", "unknown")
    architectural_context = session_state.get("architectural_context", {})
    backend_api_routes = session_state.get("backend_api_routes", {})
    api_route_summary = session_state.get("api_route_summary", "")

    if system_type != "unknown" and architectural_context:
        modules = architectural_context.get("modules", {})
        constraints = architectural_context.get("constraints", [])
        file_org_rules = architectural_context.get("file_organization_rules", {})
        
        arch_instructions = [
            "",
            f"ARCHITECTURAL RULES FOR {system_type.upper().replace('_', ' ')}:",
        ]
        
        # Add API route context if available
        if backend_api_routes and api_route_summary:
            arch_instructions.extend([
                "",
                "EXISTING API ROUTES:",
                api_route_summary,
                "",
                "CRITICAL API INTEGRATION RULES:",
                "- Connect existing API routes to frontend components",
                "- Ensure main entry point imports and includes all API routers",
                "- Do not create duplicate or conflicting endpoints",
                "- Maintain consistency with existing API structure",
            ])
        
        # Add constraints from architectural analysis
        if constraints:
            arch_instructions.append("")
            arch_instructions.append("CONSTRAINTS:")
            for constraint in constraints:
                arch_instructions.append(f"- {constraint}")
        
        # Add module-specific rules from architectural analysis
        if modules:
            arch_instructions.extend(["", "MODULE ORGANIZATION:"])
            for module_name, module_info in modules.items():
                languages = module_info.get("languages", [])
                boundary_type = module_info.get("boundary_type", "unknown")
                responsibilities = module_info.get("responsibilities", [])
                folder_structure = module_info.get("folder_structure", {})
                base_path = folder_structure.get("base_path", module_name.lower())
                
                arch_instructions.append(f"- {module_name} ({boundary_type}):")
                arch_instructions.append(f"  Languages: {', '.join(languages)}")
                arch_instructions.append(f"  Base path: {base_path}")
                arch_instructions.append(f"  Responsibilities: {', '.join(responsibilities)}")
        
        # Add file organization rules from architectural analysis
        if file_org_rules:
            arch_instructions.extend(["", "FILE ORGANIZATION RULES:"])
            for rule_name, rule_path in file_org_rules.items():
                arch_instructions.append(f"- {rule_name}: {rule_path}")
        
        # Add entry point validation
        arch_instructions.extend([
            "",
            "CRITICAL ENTRY POINT VALIDATION:",
            "- Ensure main application files import and connect all modules",
            "- Verify proper configuration for module communication",
            "- If API routes exist but main entry point doesn't use them, this is a critical interconnection issue",
            "- Always connect generated implementations to the main application entry point",
        ])
        
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
    
    # === DEBUG: Show final compound prompt ===
    final_instructions = "\n".join(instructions)
    canvas.info("🔍 DEBUG: Final compound prompt:")
    canvas.info("="*50)
    canvas.info(final_instructions)
    canvas.info("="*50)
    
    # === Team creation ===
    return Team(
        name="CodeEvolutionTeam",
        members=[orchestration_agent],
        mode="collaborate",
        model=llm_highest,
        instructions=instructions,
        response_model=OrchestrationResult,
        show_tool_calls=False,
        debug_mode=False,
        markdown=False,
        tools=[]
    )


def _retrieve_knowledge_context(
    knowledge_base, 
    objective: Dict[str, Any], 
    architectural_context: Dict[str, Any]
) -> str:
    """
    DEPRECATED: This function is deprecated in favor of AGNO-native knowledge access.
    
    The Team's knowledge parameter and enable_agentic_context=True provide
    dynamic knowledge access without content consumption bloat.
    
    Kept for backward compatibility but returns empty string.
    """
    if knowledge_base:
        canvas.info("[KNOWLEDGE] Using AGNO-native access instead of content consumption")
    else:
        canvas.warning("[KNOWLEDGE] No knowledge available for orchestration team")
    
    return ""  # Return empty - let AGNO handle knowledge access dynamically