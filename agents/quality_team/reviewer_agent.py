# /agents/quality_team/reviewer_agent.py
# Agent responsible for performing a basic code review using an LLM.

import os
import json
from pathlib import Path
from typing import Dict, List, Any

# Import Agno Agent and LLM provider instance
from agno.agent import Agent
from llm_providers import llm_middle # Use middle tier for review tasks

# Import CLI for logging
try:
    from cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_REV] {msg}")
        def error(self, msg): print(f"[ERROR_REV] {msg}")
        def info(self, msg): print(f"[INFO_REV] {msg}")
        def success(self, msg): print(f"[SUCCESS_REV] {msg}")
    canvas = FallbackCanvas()

# Configuration
MAX_SNIPPET_LENGTH = 400 # Max characters per file snippet in prompt
MAX_FILES_IN_PROMPT = 10 # Max files to include snippets for in prompt

class ReviewerAgent(Agent):
    """
    Performs a basic review of generated code using an LLM, focusing on
    alignment with the objective and obvious logical issues.
    """
    def __init__(self, **kwargs):
        super().__init__(
            name="ReviewerAgent",
            model=llm_middle,
            description="Reviews generated code snippets for objective alignment and obvious errors.",
            instructions=[
                "You are an AI Code Review Assistant.",
                "Your task is to perform a brief, high-level review of the provided code snippets based on the project objective and static analysis summary.",
                "Focus on these points:",
                "1. Objective Alignment: Does the code *seem* to address the core objective? (Brief Yes/No + reason).",
                "2. Obvious Logical Issues: Based *only* on the snippets and analysis, are there any immediately obvious potential logical errors, missing core functionality mentioned in the objective, or clear anti-patterns? Be specific but concise.",
                "3. Key Suggestion: What is the single most important suggestion for improvement based on this limited view? If none, state 'No specific suggestion'.",
                "Consider the provided static analysis summary (lint errors, dependencies) if available.",
                "Keep your entire response concise and focused on the provided information.",
                "Output ONLY the review text, no greetings or markdown formatting."
            ],
            # No retry params here, rely on try/except in caller
            **kwargs
        )
        print("🧐 [ReviewerAgent] Initialized.")

    def _prepare_review_prompt(self, structured_goal: dict, code_map: dict, analysis_summary: dict | None = None) -> str:
        """Constructs the prompt for the LLM review."""
        objective = structured_goal.get('objective', 'N/A')
        language = structured_goal.get('language', 'N/A')

        prompt = f"Project Objective: {objective}\nLanguage: {language}\n\n"

        if analysis_summary:
             prompt += "[Static Analysis Summary:]\n"
             errors = analysis_summary.get('total_lint_errors', 0)
             files_w_errors = len(analysis_summary.get('files_with_lint_errors', []))
             deps = len(analysis_summary.get('all_dependencies', []))
             prompt += f"- Lint Errors: {errors} found in {files_w_errors} file(s).\n"
             # Add more summary points later (complexity, security)
             prompt += f"- Dependencies Found: {deps}\n\n"
        else:
             prompt += "[Static Analysis Summary: Not Available]\n\n"


        prompt += "[Code Snippets:]\n"
        file_count = 0
        for file_path, code_content in code_map.items():
            if file_count >= MAX_FILES_IN_PROMPT:
                 prompt += f"... (plus {len(code_map) - file_count} more files)\n"
                 break
            prompt += f"--- File: {file_path} ---\n"
            snippet = code_content[:MAX_SNIPPET_LENGTH] + ('...' if len(code_content) > MAX_SNIPPET_LENGTH else '')
            prompt += f"```\n{snippet}\n```\n"
            file_count += 1
        prompt += "\n"

        prompt += "Please provide your review based ONLY on the objective, analysis summary, and snippets above:"
        return prompt


    def review_code(self, structured_goal: dict, code_map: dict, analysis_summary: dict | None = None) -> str | None:
        """
        Performs the code review by calling the LLM.

        Args:
            structured_goal: The project's objective and language.
            code_map: Dictionary mapping file paths to generated code content.
            analysis_summary: Optional dictionary from StaticAnalysisAgent.

        Returns:
            A string containing the review feedback, or None on failure.
        """
        canvas.info(f"🤖 [ReviewerAgent] Starting code review for objective: {structured_goal.get('objective', 'N/A')[:40]}...")

        if not code_map:
             canvas.warning("   [ReviewerAgent] No code provided to review. Skipping.")
             return "No code provided for review."

        prompt = self._prepare_review_prompt(structured_goal, code_map, analysis_summary)

        try:
            # Use direct agent call, rely on try/except in orchestrator
            response = self.run(prompt)
            review_text = response.content if hasattr(response, 'content') else str(response)
            canvas.success("   [ReviewerAgent] Review generated successfully.")
            return review_text.strip()

        except Exception as e:
            canvas.error(f"   ❌ [ReviewerAgent] Error during LLM review call: {e}")
            return None # Indicate failure

# Instantiate the agent globally for easy import
reviewer_agent = ReviewerAgent()
