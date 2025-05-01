# /agents/modification_team/code_modifier.py
# Agent responsible for applying planned modifications to code files, using RAG context.

import os
from pathlib import Path
from typing import Dict, Optional, Any

from agno.agent import Agent
from llm_providers import llm_highest  # Use high-capacity model for code modification

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

    def _prepare_modification_prompt(self, 
                                     modification_step: Dict, 
                                     project_path: Path, 
                                     existing_code: str = "",
                                     retrieved_context: Optional[str] = None) -> str:
        """
        Constructs a comprehensive prompt for code modification/creation that effectively
        uses retrieved context.
        
        Args:
            modification_step: A dictionary from the planner's output with action, file, what, how
            project_path: The root path of the project
            existing_code: The content of the file if it exists (for modify action)
            retrieved_context: Optional string containing relevant code snippets from RAG
            
        Returns:
            The constructed prompt string
        """
        action = modification_step.get('action', '').lower()
        file_rel_path = modification_step.get('file')
        what_to_do = modification_step.get('what')
        how_to_do_it = modification_step.get('how')
        
        # --- Section 1: Project and Task Information ---
        prompt = f"# Project and Task Information\n"
        prompt += f"Project Path: {project_path}\n"
        prompt += f"File to {action}: {file_rel_path}\n"
        prompt += f"Task Description (What): {what_to_do}\n"
        prompt += f"Implementation Details (How): {how_to_do_it}\n\n"

        # --- Section 2: Retrieved Context (if available) ---
        if retrieved_context:
            prompt += f"# Relevant Context from Project\n"
            prompt += f"{retrieved_context}\n\n"
        else:
            prompt += "# No specific relevant context was retrieved from the project.\n\n"

        # --- Section 3: Existing Code (if modifying) ---
        if existing_code and action == 'modify':
            prompt += f"# Existing Code of '{file_rel_path}'\n"
            prompt += f"```\n{existing_code}\n```\n\n"
            prompt += f"Apply the requested modification ('{what_to_do}') to the existing code above,"
            prompt += f"using any provided context for guidance.\n"
        else:  # Create action
            prompt += f"Generate the complete code for the new file '{file_rel_path}' based on the task,"
            prompt += f"using any provided context for guidance.\n"
        
        # --- Section 4: Instructions ---
        prompt += "\n# Instructions\n"
        if action == 'modify':
            prompt += "1. Identify where and how to implement the requested change\n"
            prompt += "2. Make the modification while preserving the rest of the code\n"
            prompt += "3. Ensure the change aligns with the existing code style and patterns\n"
        else:  # create
            prompt += "1. Generate complete, runnable code for the new file\n"
            prompt += "2. Follow project patterns and conventions visible in the context\n"
            prompt += "3. Implement the functionality described in the task\n"
        
        prompt += "\nOutput ONLY the final, complete source code for the file."
        
        return prompt

    def modify_code(self, modification_step: Dict, project_path: Path, retrieved_context: Optional[str] = None) -> Optional[str]:
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
        
        if not all([action, file_rel_path]):
            print(f"   ❌ [CodeModifierAgent] Invalid modification step received: {modification_step}")
            return None

        if action == 'delete':
            # This case is handled before calling modify_code now, but keep for safety
            print(f"   ⚪ [CodeModifierAgent] 'delete' action should not reach modify_code method for {file_rel_path}.")
            return None

        print(f"   -> Applying '{action}' to '{file_rel_path}': {modification_step.get('what', '')}")

        # Retrieve existing code if we're modifying a file
        existing_code = ""
        full_file_path = project_path / file_rel_path
        if action == 'modify':
            if full_file_path.is_file():
                try:
                    existing_code = full_file_path.read_text(encoding='utf-8')
                    print(f"      Read existing code ({len(existing_code)} chars).")
                except Exception as e:
                    print(f"      ⚠️ Warning: Could not read existing file {file_rel_path} for modification: {e}")
                    action = 'create'  # Fallback to create if read fails
            else:
                print(f"      ⚠️ Warning: File {file_rel_path} not found for modification. Treating as 'create'.")
                action = 'create'  # Treat as create if file doesn't exist

        # Prepare the prompt with all necessary context
        prompt = self._prepare_modification_prompt(
            modification_step=modification_step,
            project_path=project_path,
            existing_code=existing_code,
            retrieved_context=retrieved_context
        )

        try:
            # Use direct agent.run() - Rely on try/except in caller (workflow/modification.py)
            response = self.run(prompt)
            modified_code = response.content if hasattr(response, 'content') else str(response)

            # Basic cleaning
            modified_code = modified_code.strip()
            
            # Remove markdown code fences if present
            if modified_code.startswith("```") and modified_code.endswith("```"):
                lines = modified_code.splitlines()
                # Check if first line contains language identifier
                first_line = lines[0].strip().lower()
                if first_line.startswith("```"):
                    # Handle potential language tag
                    language_spec = first_line[3:].strip()  # Extract language specifier
                    if language_spec:  # If there's a language specifier
                        lines = lines[1:]  # Skip first line with language
                    else:
                        # Otherwise just remove the backticks from the first line
                        lines[0] = lines[0][3:].strip()
                
                # Remove closing backticks
                if lines[-1].strip() == "```":
                    lines = lines[:-1]
                elif lines[-1].endswith("```"):
                    lines[-1] = lines[-1][:-3].strip()
                
                modified_code = "\n".join(lines).strip()

            if modified_code:
                print(f"      ✅ Generated modified/new code for {file_rel_path} ({len(modified_code)} chars).")
                return modified_code
            else:
                print(f"      ⚠️ LLM returned empty content for {file_rel_path}.")
                raise ValueError(f"LLM returned empty content for {file_rel_path}")

        except Exception as e:
            print(f"   ❌ Error generating modified code for {file_rel_path}: {e}")
            raise e  # Re-raise so the caller knows it failed

# Instantiate the agent for easy import
code_modifier_agent = CodeModifierAgent()