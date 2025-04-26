# /agents/core_agents.py
# AGNO Pro Agents: Corrected with stronger instructions to avoid markdown fences

from agno.agent import Agent
from pathlib import Path
import json

# Import prepared LLMs
from llm_providers import llm_middle, llm_highest

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
    ],
)

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
    ],
)

# --- Code Builder Agent ---
code_builder_agent = Agent(
    name="CodeBuilder",
    model=llm_highest,
    description="Generates complete, runnable code for each specified project file.",
    instructions=[
        "You are a master Code Generation Agent.",
        "Given a project objective, programming language, and filename, generate the full runnable code for that file.",
        "Your response must consist solely of the raw source code lines, with NO markdown fences, backticks, or delimiters.",
        "Do NOT include comments, explanations, or any non-code characters—only the code itself.",
        "Ensure the code is idiomatic, functional, and ready to execute as is.",
    ],
)

# --- File Writer Utility ---
def write_files(code_map: dict[str, str], destination_dir: str | Path):
    print(f"💾 [FileWriter] Saving {len(code_map)} files to {destination_dir}...")
    dest_path = Path(destination_dir)
    try:
        dest_path.mkdir(parents=True, exist_ok=True)
        for relative_path_str, content in code_map.items():
            full_path = dest_path / relative_path_str
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding='utf-8')
            print(f"   -> Saved {full_path}")
        print("✅ All files saved.")
    except Exception as e:
        print(f"❌ Error writing files: {e}")

if __name__ == '__main__':
    print("--- 🧠 AGNO Pro Alive Agents Ready ---")
