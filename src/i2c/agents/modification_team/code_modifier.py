# /agents/modification_team/code_modifier.py
# Agent responsible for applying planned modifications to code files, using RAG context.

import os
import re
from pathlib import Path
from typing import Dict, Optional, Any, List, Set

from agno.agent import Agent
from i2c.tools.neurosymbolic.semantic_tool import SemanticGraphTool
from builtins import llm_highest  # Use high-capacity model for code modification

class CodeModifierAgent(Agent):
    """Applies planned code changes to existing or new files, utilizing provided RAG context."""
    def __init__(self, **kwargs):
        # Add semantic tool to existing tools
        semantic_tool = SemanticGraphTool()
        
        super().__init__(
            name="CodeModifier",
            model=llm_highest,
            tools=[semantic_tool],
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
        
        # Detect language from file extension for better code generation
        language = "python"  # Default to Python
        if file_rel_path:
            if file_rel_path.endswith('.js'):
                language = "javascript"
            elif file_rel_path.endswith('.html'):
                language = "html"
            elif file_rel_path.endswith('.ts'):
                language = "typescript"
            elif file_rel_path.endswith('.java'):
                language = "java"
            elif file_rel_path.endswith('.go'):
                language = "go"
        
        # --- Section 1: Project and Task Information ---
        prompt = f"# Project and Task Information\n"
        prompt += f"Project Path: {project_path}\n"
        prompt += f"File to {action}: {file_rel_path}\n"
        prompt += f"File Language: {language}\n"  # Added language specification
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
        
        # --- Section 4: Enhanced Quality Check Instructions ---
        prompt += "\n# Quality Check Requirements\n"
        prompt += "Before finalizing your code, verify that it:\n"
        prompt += "1. Has valid syntax with no compilation or runtime errors\n"  # Enhanced emphasis on errors
        prompt += "2. Implements all required functionality completely\n"
        prompt += "3. Follows consistent style with project context\n"
        prompt += "4. Has appropriate error handling for all operations\n"  # Strengthened error handling requirement
        prompt += "5. Includes proper documentation (docstrings, comments)\n"  # Added documentation emphasis
        prompt += "6. Uses similar patterns to those in the context\n"
        prompt += "7. Includes all necessary imports (use context patterns when relevant)\n"
        prompt += "8. Contains no undefined references or missing dependencies\n"  # Added check for undefined references
        
        # --- Section 5: Critical Reliability Requirements ---
        prompt += "\n# Critical Reliability Requirements\n"  # New section for reliability
        prompt += f"1. The code MUST be syntactically valid {language} code with no errors\n"
        prompt += "2. All referenced functions, classes, and variables must be properly defined\n"
        prompt += "3. All imports must be correct and available in the project\n"
        prompt += "4. Error handling must be included for all operations that could fail\n"
        prompt += "5. The code must be directly executable without manual fixes\n"
        
        prompt += "\n# Output Format\n"
        prompt += "Return ONLY the complete source code for the file, with no explanations or markdown formatting.\n"
        prompt += "The code must be valid syntax with no errors.\n"
        
        return prompt

    def modify_code(self, modification_step: Dict, project_path: Path, retrieved_context: Optional[str] = None) -> Optional[str]:
        # Initialize semantic tool with project path
        self.tools[0].initialize(project_path)
        
        # Get enhanced semantic context
        file_path = modification_step.get('file')
        semantic_context = self.tools[0].get_context_for_file(file_path)
        
        # Enhance retrieved context with semantic information
        enhanced_context = self._enhance_context(retrieved_context, semantic_context)
        
        # Create prompt with enhanced context
        prompt = self._prepare_modification_prompt(
            modification_step, project_path, existing_code, enhanced_context
        )
        
        # Generate initial code
        response = self.run(prompt)
        modified_code = self._extract_code_from_response(response)
        
        # Validate the modification
        validation = self.tools[0].validate_modification(
            file_path, 
            modification_step.get('action'),
            modified_code
        )
        
        # If validation failed, try to fix
        if not validation['valid']:
            # Create a fixing prompt
            fixing_prompt = self._create_fixing_prompt(modified_code, validation)
            # Run again
            fix_response = self.run(fixing_prompt)
            modified_code = self._extract_code_from_response(fix_response)
            
        return modified_code
    
# Instantiate the agent for easy import
code_modifier_agent = CodeModifierAgent()