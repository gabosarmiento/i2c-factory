# /agents/core_agents.py
# Defines and instantiates the core Agno agents for the factory.

import os
import json
from pathlib import Path
from agno.agent import Agent

# Import prepared LLMs
from llm_providers import llm_middle, llm_highest, llm_small # Use llm_middle or llm_small for analysis

# --- Input Processor Agent ---
input_processor_agent = Agent(
    name="InputProcessor",
    model=llm_middle,
    description="Clarifies raw user software ideas into structured objectives and languages.",
    instructions=[
        "You are a world-class Software Project Clarification Agent.",
        "Transform a raw user idea into a clear, concise project objective and detect the primary programming language.",
        "Respond strictly with a JSON object containing 'objective' and 'language'.",
        "Example: {\"objective\": \"Create a CLI todo list manager.\", \"language\": \"Python\"}",
        "Do NOT include any extra text, greetings, explanations, or markdown formatting.",
    ]
)
print(f"🧠 [InputProcessorAgent] Initialized with model: {getattr(llm_middle, 'id', 'Unknown')}")

# --- Planner Agent ---
planner_agent = Agent(
    name="Planner",
    model=llm_middle,
    description="Plans the minimal viable file structure for the project based on clarified objectives.",
    instructions=[
        "You are a Software Project Planning Agent.",
        "Given a project objective and programming language, output ONLY a minimal JSON array of essential file paths.",
        "Example output: [\"main.py\", \"game.py\", \"player.py\"].",
        "Do NOT include any commentary, folder hierarchies, or markdown formatting.",
    ]
)
print(f"🧠 [PlannerAgent] Initialized with model: {getattr(llm_middle, 'id', 'Unknown')}")


# --- Code Builder Agent ---
code_builder_agent = Agent(
    name="CodeBuilder",
    model=llm_highest,
    description="Generates complete, runnable code for each specified project file.",
    instructions=[
         "You are an AI assistant that writes code for specified files based on a project objective.",
         "You output ONLY the raw code requested, without any explanations or markdown."
    ]
)
print(f"🧠 [CodeBuilderAgent] Initialized with model: {getattr(llm_highest, 'id', 'Unknown')}")

# --- <<< NEW: Project Context Analyzer Agent >>> ---
project_context_analyzer_agent = Agent(
    name="ProjectContextAnalyzer",
    # Use a capable but potentially faster model for analysis
    model=llm_middle, # Or llm_small if sufficient
    description="Analyzes a project's file list to infer its objective, language, and suggest next actions.",
    instructions="""
You are an expert Project Analysis Agent. Given a list of filenames from a software project:
1. Infer the main programming language used (e.g., Python, JavaScript, Java).
2. Infer a concise, one-sentence objective or purpose for the project based on the filenames.
3. Propose 2-3 intelligent next actions (new features 'f' or refactors/improvements 'r') that would logically follow for this type of project. Each suggestion must start with 'f ' or 'r '.

Format your output STRICTLY as a JSON object with these keys: "objective", "language", "suggestions".
Use valid JSON with double quotes for all keys and string values. Do NOT use single quotes.

Example Input (prompt containing file list):
Files:
main.py
board.py
player.py
game.py
test_board.py
test_game.py

Example Output:
{
  "objective": "A console-based Tic Tac Toe game.",
  "language": "Python",
  "suggestions": [
    "f Add a feature to allow players to choose X or O.",
    "r Refactor 'game.py' to separate game loop logic from win-checking.",
    "f Implement a simple AI opponent."
  ]
}

Do NOT include any other text, explanations, or markdown formatting. Output only the JSON object.
"""
)
print(f"🤔 [ProjectContextAnalyzerAgent] Initialized with model: {getattr(project_context_analyzer_agent.model, 'id', 'Unknown')}")
# --- <<< End New Agent >>> ---


# --- File Writer Utility (Moved to workflow/modification/file_operations.py) ---
# def write_files(...): ...

if __name__ == '__main__':
    print("--- ✅ Core Agents Initialized ---")

