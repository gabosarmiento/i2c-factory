# demo/scripts/interactive_demo.py
import os
import sys
import time
import json
from pathlib import Path

os.environ["TOKENIZERS_PARALLELISM"] = "false"

sys.path.append(str(Path(__file__).parent.parent.parent))

# Load LLMs and set builtins
from llm_providers import initialize_groq_providers
import builtins
(
    builtins.llm_highest,
    builtins.llm_middle,
    builtins.llm_small,
    builtins.llm_xs
) = initialize_groq_providers()

from cli.controller import canvas
from workflow.session import run_session

class InteractiveDemoPresenter:
    def __init__(self):
        self.script_sections = self._load_script()
        self.current_section = 0
    
    def _load_script(self):
        script_path = Path(__file__).parent.parent / "scenarios" / "crypto_dashboard.json"
        with open(script_path, "r") as f:
            return json.load(f)
    
    def run_presentation(self):
        canvas.info("🎭 Starting Interactive Demo Presentation")
        
        for section in self.script_sections:
            self._present_section(section)
            input("\nPress Enter to continue...")
    
    def _present_section(self, section):
        canvas.info(f"\n{'='*50}")
        canvas.info(f"📍 {section.get('name', 'Unnamed Step')}")
        canvas.info(f"{'='*50}")
        
        # Handle narration/message
        if 'message' in section:
            canvas.info(f"\n💬 {section['message']}")
            time.sleep(section.get('pause', 2))
        
        # Handle actions
        if section.get('type') in ['initial_generation', 'modification']:
            canvas.info(f"\n🔧 Executing: {section['type']}")
            canvas.info(f"📝 Prompt: {section.get('prompt')}")
            self._simulate_action(section['type'], section.get('prompt'))
    
    def _simulate_action(self, action, prompt):
        canvas.info("\n⚡ Processing...")
        time.sleep(3)  # Simulate processing
        canvas.success(f"✅ {action.capitalize()} completed successfully!")

if __name__ == "__main__":
    presenter = InteractiveDemoPresenter()
    presenter.run_presentation()