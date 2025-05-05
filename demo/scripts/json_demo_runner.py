import os
import sys
from metrics_collector import DemoMetricsCollector
import time
from datetime import datetime
import json
from pathlib import Path

os.environ["TOKENIZERS_PARALLELISM"] = "false"

sys.path.append(str(Path(__file__).parent.parent.parent))

from llm_providers import initialize_groq_providers
import builtins
(
    builtins.llm_highest,
    builtins.llm_middle,
    builtins.llm_small,
    builtins.llm_xs
) = initialize_groq_providers()

from cli.controller import canvas
from agents.budget_manager import BudgetManagerAgent
from agents.core_agents import input_processor_agent
from workflow.orchestrator import route_and_execute

class JSONDemoRunner:
    def __init__(self, scenario_file: str):
        self.script_path = Path(__file__).parent.parent / scenario_file
        self.scenarios = self._load_scenarios()
        self.budget_manager = BudgetManagerAgent(session_budget=10.0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_project_path = Path(__file__).parent.parent / "output" / f"project_{timestamp}"
        self.current_project_path.mkdir(parents=True)
        
        canvas.info(f"📁 Output will be saved to: {self.current_project_path}")
        
        self.current_structured_goal = None
        self.metrics = DemoMetricsCollector()

    def _load_scenarios(self):
        with open(self.script_path, "r") as f:
            return json.load(f)

    def run(self):
        canvas.info("🚀 Running JSON-Based Demo")
        for idx, section in enumerate(self.scenarios):
            self._execute_section(idx, section)
            input("\n⏸ Press Enter to continue...\n")

        total_tokens = self.metrics.metrics['tokens_used']
        estimated_cost = total_tokens / 1_000_000 * 0.50  # $0.50 per 1M tokens
        canvas.info("📊 Metrics Summary")
        canvas.info(f"🧮 Total tokens used: {total_tokens}")
        canvas.info(f"💵 Estimated LLM cost: ${estimated_cost:.4f}")

    def _execute_section(self, idx, section):
        canvas.info(f"\n{'='*50}")
        canvas.info(f"📍 Step {idx+1}: {section.get('name', 'Unnamed')}")
        canvas.info(f"{'='*50}")

        if section.get("type") == "narration":
            canvas.info(f"\n💬 {section.get('message', '')}")
            time.sleep(section.get("pause", 2))

        elif section.get("type") == "initial_generation":
            prompt = section.get("prompt")
            if not prompt:
                canvas.error("❌ Missing prompt for initial generation")
                return

            canvas.info(f"\n📝 Prompt: {prompt}")
            start_time = time.time()
            response = self._execute_with_timeout(lambda: input_processor_agent.run(prompt), timeout=30)
            duration = time.time() - start_time
            tokens = getattr(response, "usage", {}).get("total_tokens", 0)
            # canvas.info(f"🧪 Response object (debug): {response}")

            canvas.info(f"⏱ Took {duration:.2f}s | 💬 {tokens} tokens used")
            self.metrics.record_operation('generation', duration, tokens)
            self.current_structured_goal = json.loads(response.content)

            success = route_and_execute(
                action_type="generate",
                action_detail=self.current_structured_goal,
                current_project_path=self.current_project_path,
                current_structured_goal=self.current_structured_goal,
            )

            if success:
                canvas.success("✅ Initial generation completed successfully!")
            else:
                canvas.error("❌ Generation failed.")

        elif section.get("type") == "modification":
            prompt = section.get("prompt")
            if not prompt:
                canvas.error("❌ Missing prompt for modification")
                return

            canvas.info(f"\n🛠 Prompt: {prompt}")
            start_time = time.time()
            result = self._execute_with_timeout(
                lambda: route_and_execute(
                    action_type="modify",
                    action_detail=f"f {prompt}",
                    current_project_path=self.current_project_path,
                    current_structured_goal=self.current_structured_goal,
                ),
                timeout=30
            )
            duration = time.time() - start_time
            tokens = result.metadata.get("usage", {}).get("total_tokens", 0) if hasattr(result, 'metadata') else 0
            self.metrics.record_operation('modification', duration, tokens)

            if result:
                canvas.success("✅ Modification completed successfully!")
            else:
                canvas.error("❌ Modification failed.")

        else:
            canvas.warning(f"⚠️ Unknown or unhandled section type: {section.get('type')}")

    def _handle_rate_limit(self):
        canvas.warning("🚦 API rate limit hit, switching to backup mode or using cached response.")
        self.use_backup_mode = True

    def _execute_with_timeout(self, func, timeout=30):
        import signal

        def handler(signum, frame):
            raise TimeoutError("Operation timed out")

        signal.signal(signal.SIGALRM, handler)
        signal.alarm(timeout)
        try:
            result = func()
            signal.alarm(0)
            return result
        except TimeoutError:
            canvas.warning("⏱ Operation timed out. Using fallback response...")
            self._handle_rate_limit()
            self.metrics.record_error_recovery()
            return self._get_cached_response()

    def _get_cached_response(self):
        return {
            "type": "fallback",
            "content": "Cached default response"
        }

if __name__ == "__main__":
    runner = JSONDemoRunner("scenarios/crypto_dashboard_wow.json")
    runner.run()
    runner.metrics.save_metrics()
    canvas.success("🎉 Demo Complete")
    canvas.info("📊 Demo metrics saved to demo/metrics.json")
    canvas.info(f"📁 Final output folder: {runner.current_project_path}")
    canvas.info(f"🔗 Open latest in VSCode: code demo/output/crypto-dashboard")
