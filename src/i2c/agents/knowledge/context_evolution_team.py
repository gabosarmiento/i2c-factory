from typing import Dict, Any, Optional, List
from builtins import llm_middle, llm_highest
from agno.team import Team
from agno.agent import Agent
from textwrap import dedent
from i2c.cli.controller import canvas
from pydantic import BaseModel

class ContextEvolution(BaseModel):
    evolved_context: Dict[str, Any]
    conversation_summary: str  # Like Claude Code's structured summary
    current_state: Dict[str, Any]  # What agents need to know NOW
    decisions_made: List[str]  # Key decisions to preserve
    patterns_established: List[str]  # Reusable patterns
    evolution_reasoning: str
    context_size_before: Optional[int] = 0
    context_size_after: Optional[int] = 0

class ContextSummarizerAgent(Agent):
    """Agent specialized in summarizing completed work while preserving lessons learned"""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="ContextSummarizer",
            model=llm_middle,
            role="Summarizes completed work and extracts key lessons",
            instructions=[
                "You specialize in intelligent context summarization like Claude Code.",
                "CRITICAL: Analyze the provided previous_context and new_context data.",
                "Calculate actual context sizes using len(str(context)) of the provided data.",
                "Extract real patterns from documentation references and project structure.",
                "Count preserved_patterns by analyzing what you keep vs discard.",
                "Your job is to compress completed work while preserving actionable insights.",
                "Focus on what future agents need to know, not historical details.",
                "RETURN REAL CALCULATED VALUES, not defaults."
            ],
            **kwargs
        )

class PatternPreservationAgent(Agent):
    """Agent focused on identifying and preserving actionable patterns"""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="PatternPreserver", 
            model=llm_middle,
            role="Identifies and preserves actionable patterns from context",
            instructions=[
                "You identify actionable patterns that should be preserved across context evolution.",
                "Focus on API patterns, architectural decisions, and successful implementations.",
                "Distinguish between temporary context and permanent knowledge.",
                "Extract patterns that help agents make consistent decisions.",
                "Prioritize patterns that prevent code conflicts and maintain consistency."
            ],
            **kwargs
        )

class ContextSizeManagerAgent(Agent):
    """Agent that manages context window size and decides what to keep/discard"""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="ContextSizeManager",
            model=llm_middle, 
            role="Manages context window size and evolution strategy",
            instructions=[
                "You manage context window size to prevent agent confusion and performance issues.",
                "Decide what context to keep, summarize, or discard based on current relevance.",
                "Maintain context under reasonable limits (8000-10000 chars) while preserving functionality.",
                "Consider current task relevance when making evolution decisions.",
                "Prioritize: current project state > recent decisions > historical information.",
                "Balance completeness with efficiency in context management.",
                "Remove redundant or outdated information that might confuse agents."
            ],
            **kwargs
        )

def build_context_evolution_team(session_state: Optional[Dict[str, Any]] = None) -> Team:
    """
    Build collaborative team for intelligent context evolution.
    
    Args:
        session_state: Optional shared session state
        
    Returns:
        Team configured for context evolution collaboration
    """
    
    # Create specialized agents
    summarizer = ContextSummarizerAgent()
    pattern_preserver = PatternPreservationAgent()
    size_manager = ContextSizeManagerAgent()
    
    return Team(
        name="ContextEvolutionTeam",
        mode="collaborate", 
        model=llm_highest,
        members=[summarizer, pattern_preserver, size_manager],
        instructions=[
            "You are the Context Evolution Team.",
            "Work together to analyze context growth and decide how to manage it.",
            "Each member should contribute their expertise.",
            "ContextSummarizer: analyze what can be summarized",
            "PatternPreserver: identify what patterns must be kept", 
            "ContextSizeManager: decide on size management strategy",
            "Collaborate and reach consensus on the best approach."
        ],
        success_criteria="Team reaches consensus on optimal context evolution strategy",
        session_state=session_state or {},
        show_tool_calls=False,
        markdown=False
    )