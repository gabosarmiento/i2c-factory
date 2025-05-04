# /agents/modification_team/code_modifier.py
# Agent responsible for applying planned modifications to code files, using RAG context.

import os
import re
from pathlib import Path
from typing import Dict, Optional, Any, List, Set

from agno.agent import Agent
from builtins import llm_highest  # Use high-capacity model for code modification

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
                
                # --- <<< CONTEXT UTILIZATION SECTION >>> ---
                "## Context Utilization",
                "Carefully analyze the provided code context to:",
                "1. Understand the project's coding style and patterns",
                "2. Identify relevant functions, classes, or patterns to follow",
                "3. Detect naming conventions, formatting preferences, and code organization",
                "4. Recognize error handling approaches used in the project",
                "5. Understand how similar features are implemented",
                
                "Pay particular attention to:",
                "- Import styles and patterns",
                "- Function signatures and return types",
                "- Error handling mechanisms",
                "- Documentation and comment styles",
                "- Testing approaches if present",
                
                # --- <<< CODE MODIFICATION SECTION >>> ---
                "## Code Modification Approach",
                "If the action is 'modify':",
                "1. First understand the existing code's structure and purpose",
                "2. Identify precisely where the change should be made",
                "3. Implement the requested change while preserving all other functionality",
                "4. Ensure the change integrates seamlessly with existing code",
                "5. Maintain consistent style, naming, and patterns",
                "6. Update relevant comments or docstrings as needed",
                
                "If the action is 'create':",
                "1. Follow the project's file structure and organization patterns",
                "2. Include appropriate imports based on context",
                "3. Implement the requested functionality completely",
                "4. Use naming, documentation, and style consistent with context",
                "5. Include appropriate error handling similar to the project",
                
                # --- <<< CODE QUALITY GUIDANCE >>> ---
                "## Code Quality Requirements",
                "Ensure generated code:",
                "1. Follows consistent styling with the project",
                "2. Uses appropriate error handling",
                "3. Has compatible API designs with existing code",
                "4. Handles edge cases appropriately",
                "5. Has meaningful variable/function names matching project conventions",
                "6. Is well-structured for readability and maintainability",
                
                # --- <<< OUTPUT REQUIREMENTS >>> ---
                "Focus ONLY on generating the final, complete source code for the specified file.",
                "Output ONLY the raw code. Do NOT include explanations, comments outside the code, markdown fences, or diffs.",
            ],
            **kwargs
        )
        print("✍️  [CodeModifierAgent] Initialized.")

    def _extract_imports_from_context(self, retrieved_context: str) -> List[str]:
        """
        Extracts import patterns from retrieved context to inform new code generation.
        
        Args:
            retrieved_context: The formatted context string from RAG
            
        Returns:
            List of import statements found in context
        """
        if not retrieved_context:
            return []
            
        imports = []
        # Look for Python import statements in context chunks
        import_pattern = re.compile(r'^(?:from|import)\s+.+$', re.MULTILINE)
        
        # Process each context chunk
        chunks = retrieved_context.split("--- Start Chunk:")
        for chunk in chunks:
            if "--- End Chunk:" not in chunk:
                continue
                
            # Extract the code content (between start and end markers)
            content = chunk.split("--- End Chunk:")[0]
            
            # Find all import statements
            chunk_imports = import_pattern.findall(content)
            imports.extend(chunk_imports)
            
        # Remove duplicates while preserving order
        unique_imports = []
        seen = set()
        for imp in imports:
            normalized = imp.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_imports.append(normalized)
                
        return unique_imports

    def _extract_coding_patterns(self, retrieved_context: str) -> Dict[str, List[str]]:
        """
        Identifies common coding patterns from context to inform style consistency.
        
        Args:
            retrieved_context: The formatted context string from RAG
            
        Returns:
            Dictionary with identified patterns by category
        """
        if not retrieved_context:
            return {"error_handling": [], "function_patterns": [], "naming_conventions": []}
            
        patterns = {
            "error_handling": [],
            "function_patterns": [],
            "naming_conventions": [],
        }
        
        # Extract code blocks from context
        chunks = retrieved_context.split("--- Start Chunk:")
        for chunk in chunks:
            if "--- End Chunk:" not in chunk:
                continue
                
            # Get chunk metadata
            chunk_header = chunk.split("\n")[0] if "\n" in chunk else ""
            
            # Extract the code content
            content = chunk.split("--- End Chunk:")[0]
            
            # Look for error handling patterns
            if "try:" in content and "except" in content:
                # Simple extraction of try-except blocks
                try_blocks = re.findall(r'try:.*?except.*?:', content, re.DOTALL)
                patterns["error_handling"].extend(try_blocks[:2])  # Limit to 2 examples
                
            # Extract function definitions to understand patterns
            function_defs = re.findall(r'def\s+\w+\([^)]*\).*?:', content, re.DOTALL)
            patterns["function_patterns"].extend(function_defs[:3])  # Limit to 3 examples
            
            # Extract some variable naming patterns
            var_names = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=', content)
            if var_names:
                patterns["naming_conventions"].extend(var_names[:5])  # Limit to 5 examples
                
        return patterns

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
        
        # --- Extract useful patterns from context ---
        imports = []
        patterns = {"error_handling": [], "function_patterns": [], "naming_conventions": []}
        if retrieved_context:
            imports = self._extract_imports_from_context(retrieved_context)
            patterns = self._extract_coding_patterns(retrieved_context)
        
        # --- Section 1: Project and Task Information ---
        prompt = f"# Project and Task Information\n"
        prompt += f"Project Path: {project_path}\n"
        prompt += f"File to {action}: {file_rel_path}\n"
        prompt += f"Task Description (What): {what_to_do}\n"
        prompt += f"Implementation Details (How): {how_to_do_it}\n\n"

        # --- Section 2: Retrieved Context Analysis ---
        if retrieved_context:
            prompt += f"# Retrieved Context Analysis\n"
            
            # Include common imports found in context
            if imports:
                prompt += f"## Common Import Patterns\n"
                prompt += "These import patterns were found in the project and may be relevant:\n"
                for imp in imports[:5]:  # Limit to 5 most relevant imports
                    prompt += f"- `{imp}`\n"
                prompt += "\n"
            
            # Include identified code patterns
            if any(patterns.values()):
                prompt += f"## Code Style Patterns\n"
                prompt += "The following patterns were identified in the codebase:\n"
                
                if patterns["function_patterns"]:
                    prompt += "Function declaration examples:\n"
                    for pattern in patterns["function_patterns"][:2]:  # Limit examples
                        prompt += f"- `{pattern.strip()}`\n"
                    prompt += "\n"
                
                if patterns["error_handling"]:
                    prompt += "Error handling approach:\n"
                    for pattern in patterns["error_handling"][:1]:  # Just one example
                        prompt += f"- Uses pattern like: `{pattern.strip()}`\n"
                    prompt += "\n"
                    
                if patterns["naming_conventions"]:
                    naming_examples = ", ".join([f"`{name}`" for name in patterns["naming_conventions"][:5]])
                    prompt += f"Variable naming examples: {naming_examples}\n\n"
            
            # Raw context chunks
            prompt += f"## Raw Context Chunks\n"
            prompt += f"{retrieved_context}\n\n"
        else:
            prompt += "# No specific relevant context was retrieved from the project.\n\n"

        # --- Section 3: Existing Code (if modifying) ---
        if existing_code and action == 'modify':
            prompt += f"# Existing Code of '{file_rel_path}'\n"
            prompt += f"```\n{existing_code}\n```\n\n"
            prompt += f"## Modification Requirements\n"
            prompt += f"1. Apply the requested modification ('{what_to_do}') to the existing code above\n"
            prompt += f"2. Implement specifically: {how_to_do_it}\n"
            prompt += f"3. Maintain all existing functionality not related to this change\n"
            prompt += f"4. Follow the project's coding style and patterns\n"
        else:  # Create action
            prompt += f"# New File Creation Requirements\n"
            prompt += f"1. Create a complete implementation for '{file_rel_path}'\n"
            prompt += f"2. Implement the functionality: {what_to_do}\n"
            prompt += f"3. Specific implementation details: {how_to_do_it}\n"
            prompt += f"4. Follow the project's coding style and patterns from context\n"
        
        # --- Section 4: Quality Check Instructions ---
        prompt += "\n# Quality Check Requirements\n"
        prompt += "Before finalizing your code, verify that it:\n"
        prompt += "1. Implements all required functionality completely\n"
        prompt += "2. Follows consistent style with project context\n"
        prompt += "3. Has appropriate error handling\n"
        prompt += "4. Uses similar patterns to those in the context\n"
        prompt += "5. Includes necessary imports (use context patterns when relevant)\n"
        
        prompt += "\n# Output Format\n"
        prompt += "Return ONLY the complete source code for the file, with no explanations or markdown."
        
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
            
            # Enhanced cleanup of code fences and other artifacts
            if modified_code.startswith("```") and modified_code.endswith("```"):
                # Handle language-specific code blocks or plain code blocks
                lines = modified_code.splitlines()
                
                # Check if first line contains language identifier
                first_line = lines[0].strip().lower()
                start_idx = 1  # Default starting line (skipping opening ```)
                
                if first_line.startswith("```"):
                    # Extract possible language identifier
                    language_spec = first_line[3:].strip()
                    if language_spec:  # If there's a language specifier
                        start_idx = 1  # Skip first line with language
                    else:
                        # Just remove backticks from first line
                        lines[0] = lines[0][3:].strip()
                        start_idx = 0
                
                # Remove closing backticks
                end_idx = len(lines)
                if lines[-1].strip() == "```":
                    end_idx = -1
                elif lines[-1].endswith("```"):
                    lines[-1] = lines[-1][:-3].strip()
                
                # Extract code content without fences
                if end_idx == -1:
                    lines = lines[start_idx:-1]
                else:
                    lines = lines[start_idx:]
                
                modified_code = "\n".join(lines).strip()
            
            # Remove any explanatory text before or after the code
            # This is a more aggressive attempt to isolate just the code content
            # (Only use if needed - can sometimes be too aggressive)
            """
            if "# " in modified_code and not file_rel_path.endswith((".py", ".sh", ".md")):
                # Try to find the first line that looks like code and not a comment
                lines = modified_code.splitlines()
                start_idx = 0
                for i, line in enumerate(lines):
                    if not line.strip().startswith("# ") and line.strip():
                        start_idx = i
                        break
                modified_code = "\n".join(lines[start_idx:])
            """

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