# /agents/quality_team/guardrail_agent.py
# Agent responsible for applying predefined rules to block or warn about low-quality code.

from pathlib import Path
from typing import Dict, List, Any

# Import CLI for logging
try:
    from i2c.cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_GUARD] {msg}")
        def error(self, msg): print(f"[ERROR_GUARD] {msg}")
        def info(self, msg): print(f"[INFO_GUARD] {msg}")
        def success(self, msg): print(f"[SUCCESS_GUARD] {msg}")
    canvas = FallbackCanvas()

# Define decision constants
GUARDRAIL_CONTINUE = "CONTINUE"
GUARDRAIL_WARN = "WARN"
GUARDRAIL_BLOCK = "BLOCK"

# --- Configuration (Adjust thresholds as needed) ---
MAX_CRITICAL_LINT_ERRORS = 5 # Example threshold
BLOCK_ON_SYNTAX_ERROR = True
BLOCK_ON_VULNERABILITY = True # Assuming DependencyVerifier adds specific vulnerability info later

class GuardrailAgent:
    """
    Applies predefined quality and security rules to decide if the generated
    code cycle should proceed (e.g., to commit).
    Does not use an LLM itself, operates on data from other agents.
    """
    def __init__(self):
        print("🚦 [GuardrailAgent] Initialized.")

    def evaluate_results(
        self,
        static_analysis_summary: Dict[str, Any] | None,
        dependency_summary: List[str] | None, # List of vulnerability strings
        syntax_check_result: tuple[bool, str] | None, # (success, message)
        review_feedback: str | None # Raw text from reviewer for now
        ) -> tuple[str, List[str]]:
        """
        Evaluates the results from previous SRE/Quality steps against predefined rules.

        Args:
            static_analysis_summary: Output from StaticAnalysisAgent.get_analysis_summary.
            dependency_summary: Output from DependencyVerifierAgent.check_dependencies.
            syntax_check_result: Output from SandboxExecutorAgent.execute.
            review_feedback: Output from ReviewerAgent.review_code.

        Returns:
            A tuple containing:
            - Decision (str): GUARDRAIL_CONTINUE, GUARDRAIL_WARN, or GUARDRAIL_BLOCK.
            - Reasons (List[str]): A list of reasons for the decision if not CONTINUE.
        """
        canvas.info("🤖 [GuardrailAgent] Evaluating cycle results...")
        decision = GUARDRAIL_CONTINUE
        reasons = []

        # Rule 1: Syntax Errors (from SandboxExecutor)
        if BLOCK_ON_SYNTAX_ERROR and syntax_check_result and not syntax_check_result[0]:
            decision = GUARDRAIL_BLOCK
            reason = f"Syntax check failed: {syntax_check_result[1].splitlines()[0]}" # First line of error
            reasons.append(reason)
            canvas.error(f"   [Guardrail] Rule Triggered: {reason}")

        # Rule 2: Critical Dependencies (from DependencyVerifier)
        # TODO: Enhance DependencyVerifier to categorize vulnerabilities
        if BLOCK_ON_VULNERABILITY and dependency_summary:
            # Simple check for now: block if *any* vulnerability string exists
            if dependency_summary and "Vulnerability found" in " ".join(dependency_summary):
                 # Make decision WARN for now, BLOCK might be too strict initially
                 if decision != GUARDRAIL_BLOCK: decision = GUARDRAIL_WARN
                 reason = f"Potential vulnerabilities found by Dependency Verifier ({len(dependency_summary)} issue(s))."
                 reasons.append(reason)
                 canvas.warning(f"   [Guardrail] Rule Triggered: {reason}")

        # Rule 3: Excessive Linting Errors (from StaticAnalysisAgent)
        if static_analysis_summary:
             lint_errors_count = static_analysis_summary.get("total_lint_errors", 0)
             # TODO: Refine lint error check to look for specific critical codes (e.g., F821 undefined name)
             if lint_errors_count > MAX_CRITICAL_LINT_ERRORS:
                  if decision != GUARDRAIL_BLOCK: decision = GUARDRAIL_WARN # Downgrade block to warn if syntax is ok
                  reason = f"High number of linting issues found ({lint_errors_count})."
                  reasons.append(reason)
                  canvas.warning(f"   [Guardrail] Rule Triggered: {reason}")

        # Rule 4: Negative AI Review (Basic Check)
        # TODO: Structure ReviewerAgent output (e.g., JSON with score/flags) for better rules
        if review_feedback:
             review_lower = review_feedback.lower()
             negative_keywords = ["fail", "error", "incorrect", "missing core logic", "does not align", "significant issues"]
             if any(keyword in review_lower for keyword in negative_keywords):
                  if decision != GUARDRAIL_BLOCK: decision = GUARDRAIL_WARN
                  reason = f"AI Reviewer flagged potential issues."
                  reasons.append(reason)
                  canvas.warning(f"   [Guardrail] Rule Triggered: {reason}")


        # Final Decision Log
        if decision == GUARDRAIL_CONTINUE:
            canvas.success("   [Guardrail] Evaluation passed. Proceeding.")
        elif decision == GUARDRAIL_WARN:
             canvas.warning("   [Guardrail] Evaluation resulted in WARN. Proceeding with caution.")
        else: # BLOCK
             canvas.error("   [Guardrail] Evaluation resulted in BLOCK. Halting further actions (e.g., commit).")

        return decision, reasons

# Instantiate the agent globally for easy import
guardrail_agent = GuardrailAgent()
