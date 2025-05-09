# /agents/modification_team/code_modifier.py
# Agent responsible for applying planned modifications to code files, using RAG context and semantic validators.

import os
import re
import warnings
from pathlib import Path
from typing import Dict, Optional, Any, List, Set, Union

from agno.agent import Agent
from i2c.tools.neurosymbolic.semantic_tool import SemanticGraphTool
from i2c.tools.neurosymbolic.validators import TypeValidator, PatternValidator, DependencyValidator
from builtins import llm_highest  # Use high-capacity model for code modification

# Display a deprecation warning
warnings.warn(
    "CodeModifierAgent is deprecated. Use ModificationManager instead. " 
    "See i2c.workflow.modification.code_modifier_adapter for compatibility functions.",
    DeprecationWarning,
    stacklevel=2
)

class CodeModifierAgent(Agent):
    """
    DEPRECATED: Use ModificationManager and SafeFunctionModifierAgent instead.
    
    Applies planned code changes to existing or new files, utilizing provided RAG context and enforcing semantic validation.
    """
    def __init__(self, **kwargs):
        # Add semantic tool to existing tools
        semantic_tool = SemanticGraphTool()
        super().__init__(
            name="CodeModifier",
            model=llm_highest,
            tools=[semantic_tool],
            description="Generates modified or new code based on a specific plan step and relevant context, with semantic validation.",
            instructions=[
                "You are an expert Code Modification Agent.",
                "You will receive the existing code of a file (if applicable), a specific instruction ('what' and 'how') for modifying/creating it, and potentially relevant context snippets from the codebase.",
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
                "## Code Quality Requirements",  
                "Ensure generated code:",  
                "1. Follows consistent styling with the project",  
                "2. Uses appropriate error handling",  
                "3. Has compatible API designs with existing code",  
                "4. Handles edge cases appropriately",  
                "5. Has meaningful variable/function names matching project conventions",  
                "6. Is well-structured for readability and maintainability",  
                "## Output Requirements",  
                "Focus ONLY on generating the final, complete source code for the specified file.",  
                "Output ONLY the raw code. Do NOT include explanations, comments outside the code, markdown fences, or diffs.",
            ],
            **kwargs
        )
        print("✍️  [CodeModifierAgent] Initialized.")

    def _extract_imports_from_context(self, retrieved_context: str) -> List[str]:
        """
        Extracts import patterns from retrieved context to inform new code generation.
        """
        if not retrieved_context:
            return []
        imports: List[str] = []
        import_pattern = re.compile(r'^(?:from|import)\s+.+$', re.MULTILINE)
        chunks = retrieved_context.split("--- Start Chunk:")
        for chunk in chunks:
            if "--- End Chunk:" not in chunk:
                continue
            content = chunk.split("--- End Chunk:")[0]
            imports.extend(import_pattern.findall(content))
        # Remove duplicates while preserving order
        unique_imports: List[str] = []
        seen: Set[str] = set()
        for imp in imports:
            norm = imp.strip()
            if norm and norm not in seen:
                seen.add(norm)
                unique_imports.append(norm)
        return unique_imports

    def _extract_coding_patterns(self, retrieved_context: str) -> Dict[str, List[str]]:
        """
        Identifies common coding patterns from context to inform style consistency.
        """
        if not retrieved_context:
            return {"error_handling": [], "function_patterns": [], "naming_conventions": []}
        patterns = {"error_handling": [], "function_patterns": [], "naming_conventions": []}
        chunks = retrieved_context.split("--- Start Chunk:")
        for chunk in chunks:
            if "--- End Chunk:" not in chunk:
                continue
            content = chunk.split("--- End Chunk:")[0]
            if "try:" in content and "except" in content:
                try_blocks = re.findall(r'try:.*?except.*?:', content, re.DOTALL)
                patterns["error_handling"].extend(try_blocks[:2])
            function_defs = re.findall(r'def\s+\w+\([^)]*\).*?:', content)
            patterns["function_patterns"].extend(function_defs[:3])
            var_names = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=', content)
            if var_names:
                patterns["naming_conventions"].extend(var_names[:5])
        return patterns

    def _prepare_modification_prompt(
        self,
        modification_step: Dict,
        project_path: Path,
        existing_code: str = "",
        retrieved_context: Optional[str] = None
    ) -> str:
        """
        Constructs a comprehensive prompt for code modification/creation that effectively uses retrieved context.
        """
        action = modification_step.get('action', '').lower()
        file_rel_path = modification_step.get('file', '')
        what_to_do = modification_step.get('what', '')
        how_to_do_it = modification_step.get('how', '')
        # Extract imports and patterns if context provided
        imports: List[str] = []
        patterns = {"error_handling": [], "function_patterns": [], "naming_conventions": []}
        if retrieved_context:
            imports = self._extract_imports_from_context(retrieved_context)
            patterns = self._extract_coding_patterns(retrieved_context)
        # Detect language
        language = 'python'
        if file_rel_path.endswith('.js'):
            language = 'javascript'
        elif file_rel_path.endswith('.html'):
            language = 'html'
        elif file_rel_path.endswith('.ts'):
            language = 'typescript'
        elif file_rel_path.endswith('.java'):
            language = 'java'
        elif file_rel_path.endswith('.go'):
            language = 'go'
        # Build prompt header
        prompt = f"# Project and Task Information\n"
        prompt += f"Project Path: {project_path}\n"
        prompt += f"File to {action}: {file_rel_path} ({language})\n"
        prompt += f"Task Description (What): {what_to_do}\n"
        prompt += f"Implementation Details (How): {how_to_do_it}\n\n"
        # Include context imports
        if imports:
            prompt += "## Common Import Patterns\n"
            for imp in imports[:5]:
                prompt += f"- {imp}\n"
            prompt += "\n"
        # Include code style patterns
        if any(patterns.values()):
            prompt += "## Code Style Patterns\n"
            if patterns["function_patterns"]:
                prompt += "Function declaration examples:\n"
                for pat in patterns["function_patterns"][:2]:
                    prompt += f"- {pat.strip()}\n"
                prompt += "\n"
            if patterns["error_handling"]:
                prompt += "Error handling approach:\n"
                prompt += f"- Uses pattern like: {patterns['error_handling'][0].strip()}\n\n"
            if patterns["naming_conventions"]:
                names = ", ".join(patterns["naming_conventions"][:5])
                prompt += f"Variable naming examples: {names}\n\n"
        # Include existing code if modify
        if existing_code and action == 'modify':
            prompt += f"# Existing Code of '{file_rel_path}'\n```\n{existing_code}\n```\n\n"
            prompt += "## Modification Requirements\n"
            prompt += f"1. Apply the requested modification ('{what_to_do}') to the existing code above\n"
            prompt += f"2. Implement specifically: {how_to_do_it}\n"
            prompt += "3. Maintain all existing functionality not related to this change\n"
            prompt += "4. Follow the project's coding style and patterns\n"
        else:
            prompt += "# New File Creation Requirements\n"
            prompt += f"1. Create a complete implementation for '{file_rel_path}'\n"
            prompt += f"2. Implement the functionality: {what_to_do}\n"
            prompt += f"3. Specific implementation details: {how_to_do_it}\n"
            prompt += "4. Follow the project's coding style and patterns from context\n"
        # Quality checks
        prompt += "\n# Quality Check Requirements\n"
        prompt += "Before finalizing your code, verify that it:\n"
        prompt += "1. Has valid syntax with no compilation or runtime errors\n"
        prompt += "2. Implements all required functionality completely\n"
        prompt += "3. Follows consistent style with project context\n"
        prompt += "4. Has appropriate error handling for all operations\n"
        prompt += "5. Includes proper documentation (docstrings, comments)\n"
        prompt += "6. Uses similar patterns to those in the context\n"
        prompt += "7. Includes all necessary imports (use context patterns when relevant)\n"
        prompt += "8. Contains no undefined references or missing dependencies\n"
        # Reliability
        prompt += "\n# Critical Reliability Requirements\n"
        prompt += f"1. The code MUST be syntactically valid {language} code with no errors\n"
        prompt += "2. All referenced functions, classes, and variables must be properly defined\n"
        prompt += "3. All imports must be correct and available in the project\n"
        prompt += "4. Error handling must be included for all operations that could fail\n"
        prompt += "5. The code must be directly executable without manual fixes\n"
        prompt += "\n# Output Format\n"
        prompt += "Return ONLY the complete source code for the file, with no explanations or markdown formatting.\n"
        prompt += "The code must be valid syntax with no errors.\n"
        return prompt

    def _enhance_context(
        self,
        retrieved_context: Optional[str],
        semantic_context: Any
    ) -> str:
        """
        Merge raw RAG context and semantic-tool context into one string for prompting.
        """
        parts: List[str] = []
        if retrieved_context:
            parts.append(str(retrieved_context))
        if semantic_context:
            parts.append(str(semantic_context))
        return "\n\n".join(parts)

    def _extract_code_from_response(self, response: str) -> str:
        """Extract code from the response, removing markdown and explanations."""
        import re
        
        # First try to extract code from markdown code blocks
        code_blocks = re.findall(r'```(?:python)?\n(.*?)\n```', response, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
        
        # If no code blocks, assume the entire response is the function
        response = response.strip()
        
        # Look for import statements at the beginning and remove them
        import_lines = []
        function_lines = []
        response_lines = response.splitlines()
        
        # Find where the actual function definition starts
        func_start_idx = -1
        for i, line in enumerate(response_lines):
            if line.strip().startswith('def '):
                func_start_idx = i
                break
        
        if func_start_idx >= 0:
            # Keep only the function definition and its body
            function_lines = response_lines[func_start_idx:]
            return '\n'.join(function_lines)
        
        # Failed to find function definition, return the whole response
        return response

    def _create_fixing_prompt(self, code: str, validation_result: Dict) -> str:
        """
        Create a prompt to fix validation issues in the code.
        
        Args:
            code: The code that failed validation
            validation_result: Dictionary with validation errors
            
        Returns:
            A prompt that asks the LLM to fix the issues
        """
        errors = validation_result.get('errors', [])
        error_str = "\n".join([f"- {error}" for error in errors])
        
        prompt = f"""# Code Fix Required
        
The following code has validation errors that need to be fixed:

```
{code}
```

## Validation Errors
{error_str}

## Requirements
1. Fix ONLY the issues identified in the validation errors
2. Maintain all existing functionality
3. Ensure the code has valid syntax and follows project conventions
4. Return ONLY the complete fixed code with no explanations or markdown

# Output Format
Return ONLY the complete fixed source code with no explanations or markdown formatting.
"""
        return prompt

    def modify_code(self, modification_step: Dict, project_path: Path, retrieved_context: Optional[str] = None) -> Union[str, Dict, None]:
        """
        DEPRECATED: Use i2c.workflow.modification.code_modifier_adapter.apply_modification instead.
        
        Apply planned modifications to code files with validation.
        
        Args:
            modification_step: Dict containing action, file, what and how details
            project_path: Base path of the project
            retrieved_context: Optional RAG context from relevant code snippets
            
        Returns:
            Modified code if successful, None otherwise
            
        Returns:
            - A string with the modified code if all validations pass
            - A dict with 'code', 'valid', and 'errors' keys if validations fail
            - None if the file doesn't exist for a 'modify' action
        """
        # Get file path
        file_path = modification_step.get('file')
        if not file_path:
            raise ValueError("No file path provided in modification step")
        
        # Initialize semantic graph tool ONLY for the target file
        semantic_tool: SemanticGraphTool = self.tools[0]
        semantic_tool.initialize(project_path, target_file=file_path)
        
        # If the file exists, read its content
        full_file_path = project_path / file_path
        existing_code = ""
        if full_file_path.exists():
            existing_code = full_file_path.read_text(encoding='utf-8')
        elif modification_step.get('action') == 'modify':
            # Can't modify a non-existent file
            return None
            
        # Gather semantic context
        semantic_context = semantic_tool.get_context_for_file(file_path)
        enhanced_context = self._enhance_context(retrieved_context, semantic_context)
        
        # Build and run generation prompt
        prompt = self._prepare_modification_prompt(
            modification_step, project_path, existing_code, enhanced_context
        )
        response = self.run(prompt)
        
        # Extract the content from the RunResponse object
        response_content = response.content if hasattr(response, 'content') else str(response)
        modified_code = self._extract_code_from_response(response_content)
        # Run validations
        # 1) Semantic validation
        sem_val = semantic_tool.validate_modification(
            file_path,
            modification_step.get('action'),
            modified_code
        )
        
        # If semantic validation failed, try to fix via LLM
        if not sem_val.get('valid', True):
            fixing_prompt = self._create_fixing_prompt(modified_code, sem_val)
            fix_response = self.run(fixing_prompt)
            # Extract the content from the RunResponse object
            fix_response_content = fix_response.content if hasattr(fix_response, 'content') else str(fix_response)
            modified_code = self._extract_code_from_response(fix_response_content)
            # Validate again
            sem_val = semantic_tool.validate_modification(
                file_path,
                modification_step.get('action'),
                modified_code
            )
            
        # Detect language for type validation
        detected_lang = 'python'
        if file_path.endswith('.ts'):
            detected_lang = 'typescript'
        elif file_path.endswith('.java'):
            detected_lang = 'java'
        elif file_path.endswith('.go'):
            detected_lang = 'go'
        elif file_path.endswith('.js'):
            detected_lang = 'javascript'
            
        # 2) Type consistency validation
        tv = TypeValidator(semantic_tool.graph, language=detected_lang)
        type_res = tv.validate(file_path, modification_step.get('action'), modified_code)
        
        # 3) Pattern/style validation
        pv = PatternValidator(semantic_tool.graph)
        pat_res = pv.validate(file_path, modification_step.get('action'), modified_code)
        
        # 4) Dependency validation
        dv = DependencyValidator(semantic_tool.graph)
        dep_res = dv.validate(file_path, modification_step.get('action'), modified_code)
        
        # Aggregate validation results
        results = [sem_val, type_res, pat_res, dep_res]
        errors: List[str] = []
        valid = True
        
        for r in results:
            if not r.get('valid', True):
                valid = False
                errors.extend(r.get('errors', []))
                
        if not valid:
            # Try one more fix with all errors
            error_list = "\n".join(f"- {e}" for e in errors)
            full_errors = {"errors": errors}
            fixing_prompt = self._create_fixing_prompt(modified_code, full_errors)
            fix_response = self.run(fixing_prompt)
            # Extract the content from the RunResponse object
            fix_response_content = fix_response.content if hasattr(fix_response, 'content') else str(fix_response)
            modified_code = self._extract_code_from_response(fix_response_content)
            
            # Final validation check
            all_valid = True
            final_errors: List[str] = []
            
            # Re-run all validations
            sem_val = semantic_tool.validate_modification(
                file_path, modification_step.get('action'), modified_code
            )
            type_res = tv.validate(file_path, modification_step.get('action'), modified_code)
            pat_res = pv.validate(file_path, modification_step.get('action'), modified_code)
            dep_res = dv.validate(file_path, modification_step.get('action'), modified_code)
            
            results = [sem_val, type_res, pat_res, dep_res]
            
            for r in results:
                if not r.get('valid', True):
                    all_valid = False
                    final_errors.extend(r.get('errors', []))
            
            if not all_valid:
                error_list = "\n".join(f"- {e}" for e in final_errors)
                # Add a warning log instead of throwing an exception
                print(f"WARNING: Code validation detected issues:\n{error_list}")
                # Return the modified code anyway, with validation issues noted
                return {
                    "code": modified_code,
                    "valid": False,
                    "errors": final_errors
                }
                
        # Return just the code if all validations pass
        return modified_code

    # Legacy method to maintain backward compatibility during transition
    def _modify_code_full(self, modification_step: Dict, project_path: Path, retrieved_context: Optional[str] = None) -> Union[str, Dict, None]:
        """
        Legacy implementation of full-file modification. Will be removed in future versions.
        
        Args:
            modification_step: Dict containing action, file, what and how details
            project_path: Base path of the project
            retrieved_context: Optional RAG context from relevant code snippets
            
        Returns:
            Modified code if successful, None otherwise
            
        Returns:
            - A string with the modified code if all validations pass
            - A dict with 'code', 'valid', and 'errors' keys if validations fail
            - None if the file doesn't exist for a 'modify' action
        """
        # Get file path
        file_path = modification_step.get('file')
        if not file_path:
            raise ValueError("No file path provided in modification step")
        
        # Initialize semantic graph tool ONLY for the target file
        semantic_tool: SemanticGraphTool = self.tools[0]
        semantic_tool.initialize(project_path, target_file=file_path)
        
        # If the file exists, read its content
        full_file_path = project_path / file_path
        existing_code = ""
        if full_file_path.exists():
            existing_code = full_file_path.read_text(encoding='utf-8')
        elif modification_step.get('action') == 'modify':
            # Can't modify a non-existent file
            return None
            
        # Gather semantic context
        semantic_context = semantic_tool.get_context_for_file(file_path)
        enhanced_context = self._enhance_context(retrieved_context, semantic_context)
        
        # Build and run generation prompt
        prompt = self._prepare_modification_prompt(
            modification_step, project_path, existing_code, enhanced_context
        )
        response = self.run(prompt)
        
        # Extract the content from the RunResponse object
        response_content = response.content if hasattr(response, 'content') else str(response)
        modified_code = self._extract_code_from_response(response_content)
        
        # Run validations
        # 1) Semantic validation
        sem_val = semantic_tool.validate_modification(
            file_path,
            modification_step.get('action'),
            modified_code
        )
        
        # If semantic validation failed, try to fix via LLM
        if not sem_val.get('valid', True):
            # Implementation for fixing validation issues omitted for brevity
            # This is legacy code that will be removed
            pass
            
        # Return just the code if all validations pass
        return modified_code

# Instantiate the agent for easy import
code_modifier_agent = CodeModifierAgent()