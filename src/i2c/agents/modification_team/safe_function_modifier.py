# src/i2c/agents/modification_team/safe_function_modifier.py

import ast
import re
import difflib
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, List, Union, Set

from agno.agent import Agent
from builtins import llm_highest  # Use high-capacity model for code modification

class SafeFunctionModifierAgent(Agent):
    """Agent specifically designed to safely modify, add, or delete functions within a file."""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="SafeFunctionModifier",
            model=llm_highest,
            description="Precisely modifies, adds, or removes functions within a file, with minimal disturbance to the rest of the code.",
            instructions=[
                "You are an expert Function Modification Agent.",
                "You will receive information about a function to modify, add, or delete, along with specific instructions.",
                "Your job is to make precise, targeted changes to accomplish the goal while minimizing impact on the rest of the code.",
                
                "# Key Principles",
                "1. Make only the requested changes - no additional refactoring or 'improvements'",
                "2. When modifying a function, preserve its signature unless explicitly told to change it",
                "3. Maintain coding style, indentation, and patterns from the original code",
                "4. Follow the specific instructions in the 'how' field precisely",
                "5. Be aware of context and dependencies when adding new functions",
                
                "# Output Format",
                "Return ONLY the necessary code with no explanations or markdown formatting.",
                "For modifications or additions, return the complete function code.",
                "For deletions, return 'FUNCTION_DELETED' as confirmation.",
            ],
            **kwargs
        )
        print("🔧 [SafeFunctionModifierAgent] Initialized.")
    
    def list_functions(self, file_path: Path) -> list:
        """
        List all functions and methods in a file, with fallback to regex if AST parsing fails.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of function names found in the file
        """
        try:
            # Read file content
            source = file_path.read_text(encoding="utf-8")
            
            # Try AST parsing first
            try:
                import ast
                tree = ast.parse(source)
                
                functions = []
                
                # Find top-level functions
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef):
                        functions.append(node.name)
                
                # Find methods in classes
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        for child in node.body:
                            if isinstance(child, ast.FunctionDef):
                                functions.append(f"{node.name}.{child.name}")
                
                return functions
                
            except SyntaxError as e:
                # Fall back to regex for function detection if AST parsing fails
                print(f"AST parsing failed when listing functions: {e}. Trying regex approach...")
            
            # Use regex to find all function definitions
            import re
            
            # Find all top-level function definitions
            functions = []
            
            # Pattern for functions: def name(params):
            func_matches = re.finditer(r'(?:^|\n)[ \t]*def[ \t]+([a-zA-Z_][a-zA-Z0-9_]*)[ \t]*\(', source)
            for match in func_matches:
                functions.append(match.group(1))
            
            # Pattern for class definitions: class Name:
            class_matches = re.finditer(r'(?:^|\n)[ \t]*class[ \t]+([a-zA-Z_][a-zA-Z0-9_]*)[ \t]*(?:\([^)]*\))?[ \t]*:', source)
            for class_match in class_matches:
                class_name = class_match.group(1)
                class_start = class_match.start()
                class_end = len(source)
                
                # Find the end of the class (approximately)
                next_class = re.search(r'(?:^|\n)[ \t]*class[ \t]+', source[class_start + 1:])
                if next_class:
                    class_end = class_start + 1 + next_class.start()
                
                class_content = source[class_start:class_end]
                
                # Find method definitions within this class content
                method_matches = re.finditer(r'(?:^|\n)[ \t]+def[ \t]+([a-zA-Z_][a-zA-Z0-9_]*)[ \t]*\(', class_content)
                for method_match in method_matches:
                    functions.append(f"{class_name}.{method_match.group(1)}")
            
            return functions
            
        except Exception as e:
            print(f"Error listing functions in {file_path}: {e}")
            return []  # Return empty list instead of failing
          
    def extract_function(self, file_path: Path, func_name: str) -> tuple:
        """
        Extract a specific function from a file, with fallbacks for when AST parsing fails.
        
        Args:
            file_path: Path to the Python file
            func_name: Name of the function to extract
            
        Returns:
            If successful: Tuple of (function_source, function_node)
            If failed: Tuple of (error_message, None)
        """
        try:
            # Read file content
            source = file_path.read_text(encoding="utf-8")
            
            # Try AST parsing first (for clean files)
            try:
                import ast
                tree = ast.parse(source)
                
                # Find the function node by name
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == func_name:
                        func_src = ast.get_source_segment(source, node)
                        return func_src, node
                        
                # Also check for methods in classes
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        for method in node.body:
                            if isinstance(method, ast.FunctionDef) and method.name == func_name:
                                func_src = ast.get_source_segment(source, method)
                                return func_src, method
                
                # Not found via AST, try regex
                print(f"Function '{func_name}' not found via AST. Trying regex...")
            except Exception as ast_error:
                # AST parsing failed, try regex
                print(f"AST parsing failed: {ast_error}. Trying regex...")
            
            # Attempt regex-based extraction (more robust)
            import re
            
            # First try with function definition and indented block
            pattern = re.compile(
                r'(def[ \t]+' + re.escape(func_name) + r'[ \t]*\([^)]*\)[ \t]*:.*?(?=\n[ \t]*\S|$))', 
                re.DOTALL | re.MULTILINE
            )
            
            match = pattern.search(source)
            if match:
                func_src = match.group(1)
                
                # Create a minimal node object with the necessary attributes
                class DummyNode:
                    pass
                
                node = DummyNode()
                node.name = func_name
                node.lineno = source[:match.start()].count('\n') + 1
                node.end_lineno = node.lineno + func_src.count('\n')
                
                return func_src, node
            
            # Try to find with decorator
            decorator_pattern = re.compile(
                r'((?:@[^\n]*\n)+[ \t]*def[ \t]+' + re.escape(func_name) + r'[ \t]*\([^)]*\)[ \t]*:.*?(?=\n[ \t]*\S|$))',
                re.DOTALL | re.MULTILINE
            )
            
            match = decorator_pattern.search(source)
            if match:
                func_src = match.group(1)
                
                # Create a minimal node object with the necessary attributes
                class DummyNode:
                    pass
                    
                node = DummyNode()
                node.name = func_name
                node.lineno = source[:match.start()].count('\n') + 1
                node.end_lineno = node.lineno + func_src.count('\n')
                
                return func_src, node
            
            # Function not found - provide helpful suggestions
            similar_functions = self._find_similar_functions(source, func_name)
            if similar_functions:
                suggestion = f"Did you mean one of these: {', '.join(similar_functions)}?"
                return f"ERROR: Function '{func_name}' not found. {suggestion}", None
            else:
                return f"ERROR: Function '{func_name}' not found in {file_path}", None
                
        except Exception as e:
            return f"ERROR: Failed to extract function: {e}", None
    
    def _validate_file_integrity(self, file_path: Path) -> None:
        """
        Check and fix the integrity of a Python file after modifications.
        
        Args:
            file_path: Path to the Python file to check
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Try parsing with AST
            try:
                ast.parse(content)
                # No syntax errors, file is valid
                return
            except SyntaxError as e:
                # Found syntax errors, try to fix them
                print(f"Found syntax errors in {file_path}: {e}. Attempting to fix...")
                self._fix_syntax_errors(file_path)
                
        except Exception as e:
            print(f"Error validating file integrity: {e}")
            
    def replace_function(self, file_path: Path, func_node: ast.FunctionDef, new_func_src: str) -> None:
        """
        Replace a function in a file with new code.
        
        Args:
            file_path: Path to the Python file
            func_node: AST node of the original function
            new_func_src: New source code for the function
        """
        try:
            original_lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
            
            # AST nodes use 1-based line numbers
            start = func_node.lineno - 1
            end = func_node.end_lineno
            
            # Prepare new function lines with proper line endings
            new_lines = new_func_src.splitlines(keepends=True)
            
            # Splice the new function in place of the old
            updated = original_lines[:start] + new_lines + original_lines[end:]
            file_path.write_text("".join(updated), encoding="utf-8")
            
        except Exception as e:
            raise ValueError(f"Error replacing function in {file_path}: {e}")
    
    def delete_function(self, file_path: Path, func_name: str) -> str:
        """
        Delete a function from a file, with fallbacks for different file structures.
        
        Args:
            file_path: Path to the Python file
            func_name: Name of the function to delete
            
        Returns:
            "FUNCTION_DELETED" if successful, otherwise an error message
        """
        try:
            # Read file content
            file_content = file_path.read_text(encoding="utf-8")
            
            # Try AST parsing first (for clean files)
            try:
                import ast
                tree = ast.parse(file_content)
                
                # Find the function node
                function_node = None
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == func_name:
                        function_node = node
                        break
                
                if function_node:
                    # Get line numbers (1-based in AST)
                    start_line = function_node.lineno - 1
                    end_line = function_node.end_lineno
                    
                    # Split the file into lines
                    lines = file_content.splitlines(keepends=True)
                    
                    # Remove the function
                    new_content = ''.join(lines[:start_line] + lines[end_line:])
                    
                    # Write the updated content back
                    file_path.write_text(new_content, encoding="utf-8")
                    return "FUNCTION_DELETED"
            except Exception as ast_error:
                print(f"AST parsing failed: {ast_error}. Trying simpler approach...")
            
            # Fallback to simpler pattern matching
            import re
            
            # More robust pattern matching (simplified)
            # Look for function definition followed by indented block
            func_pattern = re.compile(
                r'(^|\n)[ \t]*(def[ \t]+' + re.escape(func_name) + r'[ \t]*\([^)]*\)[ \t]*:.*?(?=\n[ \t]*\S|$))', 
                re.DOTALL | re.MULTILINE
            )
            
            match = func_pattern.search(file_content)
            if match:
                # Replace function with empty string (or newline if needed)
                new_content = func_pattern.sub(r'\1', file_content)
                file_path.write_text(new_content, encoding="utf-8")
                return "FUNCTION_DELETED"
            
            # If function still not found, look for decorator + function
            decorator_pattern = re.compile(
                r'(^|\n)[ \t]*(?:@[^\n]*\n)+[ \t]*def[ \t]+' + re.escape(func_name) + r'[ \t]*\([^)]*\)[ \t]*:.*?(?=\n[ \t]*\S|$)',
                re.DOTALL | re.MULTILINE
            )
            
            match = decorator_pattern.search(file_content)
            if match:
                # Replace function with empty string (or newline if needed)
                new_content = decorator_pattern.sub(r'\1', file_content)
                file_path.write_text(new_content, encoding="utf-8")
                return "FUNCTION_DELETED"
            
            # Function not found after all attempts
            similar_functions = self._find_similar_functions(file_content, func_name)
            if similar_functions:
                suggestion = f"Function '{func_name}' not found. Did you mean one of these: {', '.join(similar_functions)}?"
                return f"ERROR: {suggestion}"
            else:
                return f"ERROR: Function '{func_name}' not found in file"
            
        except Exception as e:
            return f"ERROR: Failed to delete function: {e}"
            
    def _find_similar_functions(self, content: str, target_name: str) -> list:
        """Find function names that are similar to the target name"""
        import re
        
        # Extract all function names
        func_matches = re.finditer(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', content)
        all_functions = [match.group(1) for match in func_matches]
        
        # Find similar names (simple approach)
        similar = []
        for name in all_functions:
            # If names are at least 50% similar in length and share characters
            if (len(name) >= len(target_name) * 0.5 and len(target_name) >= len(name) * 0.5) or \
            (target_name in name or name in target_name):
                similar.append(name)
        
        return similar
           
    def _fix_syntax_errors(self, file_path: Path) -> None:
        """
        Fix common syntax errors that might be introduced during function deletion.
        
        Args:
            file_path: Path to the Python file to fix
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Fix 1: Ensure there are newlines between functions
            import re
            content = re.sub(r'(\S)def\s+', r'\1\n\ndef ', content)
            
            # Fix 2: Ensure decorators have newlines before them
            content = re.sub(r'(\S)@', r'\1\n\n@', content)
            
            # Fix 3: Ensure classes have newlines before them
            content = re.sub(r'(\S)class\s+', r'\1\n\nclass ', content)
            
            # Fix 4: Remove extra blank lines (more than 2 consecutive)
            content = re.sub(r'\n{3,}', '\n\n', content)
            
            # Write back the fixed content
            file_path.write_text(content, encoding="utf-8")
            
            # Validate the fixed file can be parsed
            try:
                import ast
                ast.parse(content)
            except SyntaxError as e:
                print(f"Warning: Could not fully fix syntax errors in {file_path}: {e}")
        
        except Exception as e:
            print(f"Error fixing syntax in {file_path}: {e}")
    
    def add_function(self, file_path: Path, new_func_src: str, position: str = "end") -> None:
        """
        Add a new function to a file.
        
        Args:
            file_path: Path to the Python file
            new_func_src: Source code for the new function
            position: Where to add the function ("end", "begin", or "after:function_name")
        """
        try:
            # Get original file content
            original_lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
            
            # Prepare new function lines
            new_lines = new_func_src.splitlines(keepends=True)
            
            # Determine where to insert the function
            if position == "end":
                # Add at the end of the file with extra newlines
                updated = original_lines + ["\n\n"] + new_lines
                
            elif position == "begin":
                # Add at the beginning of the file with extra newlines
                updated = new_lines + ["\n\n"] + original_lines
                
            elif position.startswith("after:"):
                # Add after a specific function
                target_func = position[6:]  # Remove "after:"
                
                try:
                    # Find the target function's location
                    _, func_node = self.extract_function(file_path, target_func)
                    
                    # Insert after the function with a newline
                    end = func_node.end_lineno
                    updated = original_lines[:end] + ["\n\n"] + new_lines + original_lines[end:]
                    
                except ValueError:
                    # Target function not found, add at the end
                    print(f"Target function '{target_func}' not found, adding at the end")
                    updated = original_lines + ["\n\n"] + new_lines
            else:
                # Default to adding at the end
                updated = original_lines + ["\n\n"] + new_lines
            
            # Write the updated file
            file_path.write_text("".join(updated), encoding="utf-8")
            
        except Exception as e:
            raise ValueError(f"Error adding function to {file_path}: {e}")
    
    def modify_function(self, modification_step: Dict, project_path: Path) -> str:
        """
        Modifies a specific function in a file based on the modification step.
        Handles errors gracefully with fallbacks and suggestions.
        
        Args:
            modification_step: Dictionary with keys:
                - file: Path to the file relative to project_path
                - function: Name of the function to modify
                - what: Description of what to modify
                - how: Specific instructions on how to modify
            project_path: Base path of the project
                
        Returns:
            If successful: Modified function code
            If failed: Error message string starting with "ERROR:"
        """
        # Extract details from the modification step
        file_path_str = modification_step.get('file')
        func_name = modification_step.get('function')
        what_to_do = modification_step.get('what', '')
        how_to_do_it = modification_step.get('how', '')
        
        if not file_path_str:
            return "ERROR: Missing 'file' in modification step"
        
        # Get full path to the file
        file_path = project_path / file_path_str
        
        if not file_path.exists():
            return f"ERROR: File '{file_path}' does not exist"
        
        # Determine the operation type
        action = modification_step.get('action', 'modify').lower()
        
        if action == 'delete' and func_name:
            # Delete the function - already returns proper error messages
            return self.delete_function(file_path, func_name)
            
        elif action == 'add':
            try:
                # Generate a new function
                new_function = self._generate_new_function(
                    file_path=file_path,
                    func_name=func_name,
                    what_to_do=what_to_do,
                    how_to_do_it=how_to_do_it
                )
                
                # Add the function to the file
                position = modification_step.get('position', 'end')
                self.add_function(file_path, new_function, position)
                
                return new_function
            except Exception as e:
                return f"ERROR: Failed to add function: {e}"
                
        else:  # Default is 'modify'
            if not func_name:
                return "ERROR: Missing 'function' in modification step"
                
            # Extract the function
            result = self.extract_function(file_path, func_name)
            
            # Check if extraction failed
            if isinstance(result[0], str) and result[0].startswith("ERROR:"):
                return result[0]  # Return the error message
                
            func_src, func_node = result
                
            # Prepare the prompt
            prompt = f"""# Function Modification Task

    ## Current Function Code
    ```python
    {func_src}
    ```

    ## Modification Request
    What to do: {what_to_do}

    How to do it: {how_to_do_it}

    ## Requirements
    1. Make only the requested changes
    2. Preserve the exact function signature unless explicitly told to change it
    3. Maintain the coding style and patterns
    4. Follow the specific instructions precisely

    ## IMPORTANT FORMATTING INSTRUCTIONS
    1. DO NOT include any import statements in your response - we will handle imports separately
    2. Your response should begin with 'def {func_name}' (the function definition)
    3. Return ONLY the complete modified function code with no explanations or extra content

    Return the complete function code (starting with 'def {func_name}'):
    """
            
            try:
                # Call the model
                response = self.run(prompt)
                response_content = response.content if hasattr(response, 'content') else str(response)
                
                # Extract the function code from the response
                modified_func = self._extract_code_from_response(response_content)
                
                # Validate the modified function
                try:
                    self._validate_modified_function(modified_func, func_src, func_name)
                except ValueError as validation_error:
                    return f"ERROR: Validation failed: {validation_error}"
                
                # Replace the function in the file
                try:
                    self.replace_function(file_path, func_node, modified_func)
                except Exception as replace_error:
                    return f"ERROR: Failed to replace function in file: {replace_error}"
                
                # Show diff
                try:
                    diff = self._generate_diff(func_src, modified_func)
                    print(f"Changes made:\n{diff}")
                except Exception as diff_error:
                    print(f"Warning: Failed to generate diff: {diff_error}")
                
                return modified_func
            except Exception as e:
                return f"ERROR: Failed to modify function: {e}"
    
    def _generate_new_function(self, file_path: Path, func_name: str, what_to_do: str, how_to_do_it: str) -> str:
        """
        Generate a new function based on requirements.
        
        Args:
            file_path: Path to the file where the function will be added (for context)
            func_name: Name of the new function
            what_to_do: Description of what the function should do
            how_to_do_it: Specific implementation details
            
        Returns:
            Source code for the new function
        """
        # Get file context for style consistency
        context = self._get_file_context(file_path)
        
        # Prepare the prompt
        prompt = f"""# New Function Creation Task

## File Context
```python
{context}
```

## New Function Requirements
Function name: {func_name}
What it should do: {what_to_do}
Implementation details: {how_to_do_it}

## Style Guidelines
1. Follow the coding style visible in the file context
2. Use appropriate docstrings and comments
3. Include proper error handling
4. Use the function name specified

## IMPORTANT FORMATTING INSTRUCTIONS
1. DO NOT include import statements - we'll handle imports separately
2. Your response should begin with 'def {func_name}' (the function definition)
3. Return ONLY the function code with no explanations

Return the complete function code (starting with 'def {func_name}'):
"""
        
        # Call the model
        response = self.run(prompt)
        response_content = response.content if hasattr(response, 'content') else str(response)
        
        # Extract the function code from the response
        new_func = self._extract_code_from_response(response_content, func_name)
        
        # Validate the new function
        try:
            ast.parse(new_func)
        except SyntaxError as e:
            raise ValueError(f"New function has syntax errors: {e}")
        
        # Check that it defines the requested function
        if not re.search(rf"def\s+{re.escape(func_name)}\s*\(", new_func):
            raise ValueError(f"Generated function does not define '{func_name}'")
        
        return new_func
    
    def _get_file_context(self, file_path: Path, max_lines: int = 50) -> str:
        """
        Get a sample of code from the file to establish coding style.
        
        Args:
            file_path: Path to the file
            max_lines: Maximum number of lines to include
            
        Returns:
            Sample of code from the file
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()
            
            if len(lines) <= max_lines:
                return content
            
            # Get a representative sample from the beginning and middle
            begin = "\n".join(lines[:20])
            middle_start = max(20, len(lines) // 2 - 15)
            middle = "\n".join(lines[middle_start:middle_start + 30])
            
            return f"{begin}\n\n# ... more code ...\n\n{middle}"
            
        except Exception as e:
            print(f"Error getting file context from {file_path}: {e}")
            return "# Unable to get file context"
    
    def _extract_code_from_response(self, response: str, expected_func_name: str) -> str:
        """Extract function code from the response, removing markdown and any non-function content."""
        # First try to extract code from markdown code blocks
        code_blocks = re.findall(r'```(?:python)?\n(.*?)\n```', response, re.DOTALL)
        if code_blocks:
            content = code_blocks[0].strip()
        else:
            # If no code blocks, use the entire response
            content = response.strip()
        
        # Find where the function definition starts
        func_def_pattern = re.compile(rf'def\s+{re.escape(expected_func_name)}\s*\(')
        match = func_def_pattern.search(content)
        
        if match:
            # Extract from function definition to the end
            start_idx = match.start()
            return content[start_idx:]
        else:
            # If function definition not found, look for any function definition
            any_func_match = re.search(r'def\s+\w+\s*\(', content)
            if any_func_match:
                return content[any_func_match.start():]
        
        # If all else fails, return the entire content
        return content
    
    
        """
        Generate a unified diff between original and modified code.
        
        Args:
            original: Original code
            modified: Modified code
            
        Returns:
            Unified diff as a string
        """
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            lineterm='',
            fromfile='Original',
            tofile='Modified'
        )
        
        return '\n'.join(diff)

    def _generate_diff(self, original: str, modified: str) -> str:
        """
        Generate a unified diff between original and modified code.
        
        Args:
            original: Original code
            modified: Modified code
            
        Returns:
            Unified diff as a string
        """
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            lineterm='',
            fromfile='Original',
            tofile='Modified'
        )
        
        return '\n'.join(diff)

    def _validate_modified_function(self, modified_func: str, original_func: str, func_name: str) -> None:
        """
        Validate that the modified function maintains critical aspects of the original.
        
        Args:
            modified_func: Modified function code
            original_func: Original function code
            func_name: Function name
        
        Raises:
            ValueError: If validation fails
        """
        # Check that it's valid Python syntax
        try:
            import ast
            ast.parse(modified_func)
        except SyntaxError as e:
            raise ValueError(f"Modified function has syntax errors: {e}")
        
        # Extract function signature from original
        original_signature = original_func.splitlines()[0]
        
        # Check that it still defines the same function
        import re
        if not re.search(rf"def\s+{re.escape(func_name)}\s*\(", modified_func):
            raise ValueError(f"Modified function does not define '{func_name}'")
        
        # Check that the function signature is preserved
        modified_lines = modified_func.splitlines()
        if not modified_lines:
            raise ValueError("Modified function is empty")
            
        modified_signature = modified_lines[0]
        
        # Check if modified_signature contains import statements
        if modified_signature.startswith("from ") or modified_signature.startswith("import "):
            raise ValueError(f"Response includes import statements rather than function code")
            
        if modified_signature != original_signature:
            raise ValueError(f"Function signature changed from '{original_signature}' to '{modified_signature}'")
# Create an instance for easy importing
safe_function_modifier_agent = SafeFunctionModifierAgent()
    