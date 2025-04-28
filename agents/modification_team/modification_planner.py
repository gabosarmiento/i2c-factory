# /agents/modification_team/modification_planner.py
# Agent responsible for planning code modifications based on user requests and context.

import os
import json
from agno.agent import Agent
from llm_providers import llm_highest

class ModificationPlannerAgent(Agent):
    """Plans detailed code modifications based on context and user requests."""
    def __init__(self, **kwargs):
        super().__init__(
            name="ModificationPlanner",
            model=llm_highest,
            description="Plans specific code changes (modify, create, delete) for features/refinements.",
            instructions=[
                "You are a world-class Feature Ideation and Modification Planner Agent.",
                "Your mission is to ingest the current state of a codebase folder (provided as context) and, given a high-level refinement or feature request, propose a detailed, actionable plan of modifications.",
                "Analyze the user request in the context of the existing code summary.",
                "Determine which existing files/classes/functions must be updated, removed, or extended.",
                "Identify any new files or modules that should be created.",
                "For each planned step, specify the file path (relative to project root), action (modify, create, delete), a description of 'what' needs to change, and a high-level sketch of 'how'.",
                # --- <<< Explicit JSON Formatting Instructions >>> ---
                "Output ONLY a valid JSON list of modification steps.",
                "Each step MUST be a JSON object with keys: 'file', 'action', 'what', 'how'.",
                "Use valid JSON syntax: double quotes ONLY for all keys and string values. Do NOT use single quotes or Python dictionary syntax.",
                "Example of the required JSON format:\n"
                "[\n"
                "  {\"file\": \"game.py\", \"action\": \"modify\", \"what\": \"add reset() method\", \"how\": \"implement reset() to clear board state\"},\n"
                "  {\"file\": \"main.py\", \"action\": \"modify\", \"what\": \"call game.reset() when play again is chosen\", \"how\": \"add call after game loop ends based on user input\"}\n"
                "]",
                # --- <<< End Explicit JSON Instructions >>> ---
                "Do NOT include context summaries or any other text in the final output, only the JSON list.",
            ],
            # **RETRY_CONFIG, # <<< REMOVED >>>
            **kwargs
        )
        print("📝 [ModificationPlannerAgent] Initialized.")

    
# Instantiate the agent for easy import
modification_planner_agent = ModificationPlannerAgent()




                
           

