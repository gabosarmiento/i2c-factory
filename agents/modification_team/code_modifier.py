# /agents/modification_team/code_modifier.py
# Agent responsible for applying planned modifications to code files, using RAG context.

import os
from pathlib import Path
from agno.agent import Agent
from llm_providers import llm_highest # Use high-capacity model for code modification

class CodeModifierAgent(Agent):
    """Applies planned code changes to existing or new files, utilizing provided RAG context."""
    def __init__(self, **kwargs):
        super().__init__(
            name="CodeModifier",
            model=llm_highest,
            description="Generates modified or new code based on a specific plan step and relevant context.",
            instructions=[
                "You are an expert Code Modification Agent.",
                "You will receive the existing code of a file (if applicable), a specific instruction ('what' and 'how') for modifying/creating it, and potentially relevant context snippets from the codebase.",
                "If the action is 'modify', integrate the requested change seamlessly into the existing code, preserving the rest. Use the provided context snippets for guidance on style, related functions, or implementation details.",
                "If the action is 'create', generate the complete code for the new file based on the 'what' and 'how', using the provided context snippets for guidance.",
                "Focus ONLY on generating the final, complete source code for the specified file.",
                "Output ONLY the raw code. Do NOT include explanations, comments outside the code, markdown fences, or diffs.",
            ],
            # No retry params here
            **kwargs
        )
        print("✍️  [CodeModifierAgent] Initialized.")

    # <<< MODIFIED SIGNATURE to accept retrieved_context >>>
    def modify_code(self, modification_step: dict, project_path: Path, retrieved_context: str | None = None) -> str | None:
        """
        Generates the new/modified code content for a single step in the plan, using RAG context.

        Args:
            modification_step: A dictionary from the planner's output.
            project_path: The root path of the project.
            retrieved_context: Optional string containing relevant code snippets from RAG.

        Returns:
            The full code content for the modified/new file, or None on failure.
        """
        action = modification_step.get('action', '').lower()
        file_rel_path = modification_step.get('file')
        what_to_do = modification_step.get('what')
        how_to_do_it = modification_step.get('how')

        if not all([action, file_rel_path, what_to_do, how_to_do_it]):
            print(f"   ❌ [CodeModifierAgent] Invalid modification step received: {modification_step}")
            return None

        if action == 'delete':
            # This case is handled before calling modify_code now, but keep for safety
            print(f"   ⚪ [CodeModifierAgent] 'delete' action should not reach modify_code method for {file_rel_path}.")
            return None

        print(f"   -> Applying '{action}' to '{file_rel_path}': {what_to_do}")

        full_file_path = project_path / file_rel_path
        existing_code = ""
        if action == 'modify':
            if full_file_path.is_file():
                try:
                    existing_code = full_file_path.read_text(encoding='utf-8')
                    print(f"      Read existing code ({len(existing_code)} chars).")
                except Exception as e:
                    print(f"      ⚠️ Warning: Could not read existing file {file_rel_path} for modification: {e}")
                    action = 'create' # Fallback to create if read fails
            else:
                print(f"      ⚠️ Warning: File {file_rel_path} not found for modification. Treating as 'create'.")
                action = 'create' # Treat as create if file doesn't exist

        # --- <<< Construct Prompt with RAG Context >>> ---
        prompt = f"Project Path: {project_path}\nFile to modify/create: {file_rel_path}\nAction: {action}\n"
        prompt += f"Task Description (What): {what_to_do}\nImplementation Details (How): {how_to_do_it}\n\n"

        # Add retrieved context if available
        if retrieved_context:
            prompt += f"Potentially Relevant Context from Project:\n{retrieved_context}\n\n"
        else:
            prompt += "No specific relevant context was retrieved.\n\n"

        # Add existing code if modifying
        if existing_code:
            prompt += f"Existing Code of '{file_rel_path}':\n```\n{existing_code}\n```\n\n"
            prompt += f"Apply the requested modification ('{what_to_do}') to the existing code, using the provided context for guidance."
        else: # Create action
            prompt += f"Generate the complete code for the new file '{file_rel_path}' based on the task, using the provided context for guidance."

        prompt += "\n\nOutput ONLY the final, complete, raw source code for the file."
        # --- <<< End Prompt Construction >>> ---

        try:
            # Use direct agent.run() - Rely on try/except in caller (workflow/modification.py)
            response = self.run(prompt)
            modified_code = response.content if hasattr(response, 'content') else str(response)

            # Basic cleaning
            modified_code = modified_code.strip()
            if modified_code.startswith("```") and modified_code.endswith("```"):
                 modified_code = modified_code.splitlines()
                 if len(modified_code) > 1:
                      if modified_code[0].strip().startswith("```"): modified_code = modified_code[1:]
                      if modified_code[-1].strip() == "```": modified_code = modified_code[:-1]
                 modified_code = "\n".join(modified_code).strip()

            if modified_code:
                print(f"      ✅ Generated modified/new code for {file_rel_path} ({len(modified_code)} chars).")
                return modified_code
            else:
                print(f"      ⚠️ LLM returned empty content for {file_rel_path}.")
                raise ValueError(f"LLM returned empty content for {file_rel_path}")

        except Exception as e:
            print(f"   ❌ Error generating modified code for {file_rel_path}: {e}")
            raise e # Re-raise so the caller knows it failed

# Instantiate the agent for easy import
code_modifier_agent = CodeModifierAgent()
