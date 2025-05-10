# src/i2c/agents/modification_team/function_modification_team.py

import ast
import difflib
import re
from pathlib import Path
from typing import Dict, Optional, Union, List, Any

from agno.agent import Agent
from agno.models.groq import Groq
from agno.team import Team
from agno.tools import tool
from builtins import llm_small

from i2c.agents.modification_team.patch import Patch
from i2c.tools.neurosymbolic.semantic_tool import SemanticGraphTool

MODEL_ID=llm_small
# Custom tools for the function modification team
@tool()
def extract_function(agent: Agent, file_path: str, function_name: str) -> str:
    """
    Extract a function from a file by name.
    
    Args:
        file_path: Path to the file
        function_name: Name of the function to extract
        
    Returns:
        The function source code or an error message
    """
    # Get the project path from the agent's session state
    project_path = Path(agent.session_state.get("project_path", "."))
    full_path = project_path / file_path
    
    if not full_path.exists():
        return f"ERROR: File {file_path} does not exist"
    
    try:
        source = full_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        
        # Look for the function in the AST
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                func_src = ast.get_source_segment(source, node)
                agent.session_state["extracted_function"] = {
                    "source": func_src,
                    "node_info": {
                        "lineno": node.lineno,
                        "end_lineno": node.end_lineno
                    }
                }
                return func_src
                
        # If not found via AST, try regex as fallback
        pattern = re.compile(
            r'(def\s+' + re.escape(function_name) + r'\s*\([^)]*\).*?(?=\n\s*\S|$))', 
            re.DOTALL | re.MULTILINE
        )
        match = pattern.search(source)
        if match:
            func_src = match.group(1)
            # Store in session state
            line_count = source[:match.start()].count('\n') + 1
            end_line = line_count + func_src.count('\n')
            agent.session_state["extracted_function"] = {
                "source": func_src,
                "node_info": {
                    "lineno": line_count,
                    "end_lineno": end_line
                }
            }
            return func_src
            
        return f"ERROR: Function '{function_name}' not found in {file_path}"
            
    except Exception as e:
        return f"ERROR: Failed to extract function: {e}"


@tool()
def modify_function_content(agent: Agent, function_source: str, modifications: str) -> str:
    """
    Create a modified version of a function based on instructions.
    
    Args:
        function_source: Original function source code
        modifications: Description of required modifications
        
    Returns:
        The modified function source code
    """
    # Get the original function from context if not provided
    if not function_source and "extracted_function" in agent.session_state:
        function_source = agent.session_state["extracted_function"]["source"]
    
    if not function_source:
        return "ERROR: No function source provided"
    
    # Extract function name for prompt
    func_name_match = re.match(r'def\s+(\w+)', function_source)
    if not func_name_match:
        return "ERROR: Invalid function source format"
    
    func_name = func_name_match.group(1)
    
    # Prepare the prompt for the LLM
    prompt = f"""# Function Modification Task

## Current Function Code
```python
{function_source}
```

## Modification Request
{modifications}

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
        # Call the LLM directly
        response = agent.run(prompt)
        response_content = response.content if hasattr(response, 'content') else str(response)
        
        # Extract the function code from the response
        modified_func = extract_code_from_response(response_content)
        
        # Store the modified function in session state
        agent.session_state["modified_function"] = modified_func
        
        return modified_func
    except Exception as e:
        return f"ERROR: Failed to modify function: {e}"


@tool()
def apply_function_to_file(agent: Agent, file_path: str, function_code: str) -> str:
    """
    Apply a modified function to a file, replacing the original function.
    
    Args:
        file_path: Path to the file to modify
        function_code: New function code to insert
        
    Returns:
        Success message or error
    """
    project_path = Path(agent.session_state.get("project_path", "."))
    full_path = project_path / file_path
    
    if not full_path.exists():
        return f"ERROR: File {file_path} does not exist"
    
    # Get existing information from session state
    extracted_info = agent.session_state.get("extracted_function", {})
    if not extracted_info:
        return "ERROR: No extracted function information found in state"
    
    try:
        # Read the file content
        file_content = full_path.read_text(encoding="utf-8")
        
        # Get line info from extracted function
        start_line = extracted_info["node_info"]["lineno"] - 1  # 0-based index
        end_line = extracted_info["node_info"]["end_lineno"]  # 1-based index
        
        # Split into lines and replace the function
        lines = file_content.splitlines(True)  # Keep line endings
        modified_lines = function_code.splitlines(True)
        
        # Create updated content
        new_content = ''.join(lines[:start_line] + modified_lines + lines[end_line:])
        
        # Write back to file
        full_path.write_text(new_content, encoding="utf-8")
        
        # Generate and store diff
        diff = generate_diff(extracted_info["source"], function_code, 
                           "Original", "Modified")
        agent.session_state["function_diff"] = diff
        
        # Calculate overall file diff for patch
        file_diff = generate_diff(file_content, new_content, file_path, file_path)
        agent.session_state["file_diff"] = file_diff
        
        return f"Function successfully updated in {file_path}"
    except Exception as e:
        return f"ERROR: Failed to apply function to file: {e}"


@tool()
def delete_function(agent: Agent, file_path: str, function_name: str) -> str:
    """
    Delete a function from a file.
    
    Args:
        file_path: Path to the file
        function_name: Name of the function to delete
        
    Returns:
        Success message or error
    """
    project_path = Path(agent.session_state.get("project_path", "."))
    full_path = project_path / file_path
    
    if not full_path.exists():
        return f"ERROR: File {file_path} does not exist"
    
    try:
        # First extract the function to keep a record
        extract_result = extract_function(agent, file_path, function_name)
        if extract_result.startswith("ERROR"):
            return extract_result
            
        # Read the file content
        file_content = full_path.read_text(encoding="utf-8")
        
        # Get line info from extracted function
        extracted_info = agent.session_state.get("extracted_function", {})
        if not extracted_info:
            return "ERROR: No extracted function information found in state"
            
        start_line = extracted_info["node_info"]["lineno"] - 1  # 0-based index
        end_line = extracted_info["node_info"]["end_lineno"]  # 1-based index
        
        # Split into lines and remove the function
        lines = file_content.splitlines(True)  # Keep line endings
        
        # Create updated content
        new_content = ''.join(lines[:start_line] + lines[end_line:])
        
        # Write back to file
        full_path.write_text(new_content, encoding="utf-8")
        
        # Calculate overall file diff for patch
        file_diff = generate_diff(file_content, new_content, file_path, file_path)
        agent.session_state["file_diff"] = file_diff
        
        return f"Function '{function_name}' successfully deleted from {file_path}"
    except Exception as e:
        return f"ERROR: Failed to delete function: {e}"


@tool()
def add_function(agent: Agent, file_path: str, function_code: str, position: str = "end") -> str:
    """
    Add a new function to a file.
    
    Args:
        file_path: Path to the file
        function_code: Function code to add
        position: Where to add the function ("end", "beginning", or "after:function_name")
        
    Returns:
        Success message or error
    """
    project_path = Path(agent.session_state.get("project_path", "."))
    full_path = project_path / file_path
    
    try:
        # Ensure directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # If file exists, read it; otherwise, start with empty content
        file_content = ""
        if full_path.exists():
            file_content = full_path.read_text(encoding="utf-8")
        
        # Process the position parameter
        if position == "end" or not file_content:
            # Add at the end with newlines
            if file_content and not file_content.endswith("\n\n"):
                if file_content.endswith("\n"):
                    new_content = file_content + "\n" + function_code
                else:
                    new_content = file_content + "\n\n" + function_code
            else:
                new_content = file_content + function_code
                
        elif position == "beginning":
            # Add at the beginning with newlines
            if function_code.endswith("\n"):
                new_content = function_code + "\n" + file_content
            else:
                new_content = function_code + "\n\n" + file_content
                
        elif position.startswith("after:"):
            # Add after a specific function
            target_func = position[6:]
            
            # First extract the target function
            extract_result = extract_function(agent, file_path, target_func)
            if extract_result.startswith("ERROR"):
                # If target function not found, add at the end
                if file_content and not file_content.endswith("\n\n"):
                    if file_content.endswith("\n"):
                        new_content = file_content + "\n" + function_code
                    else:
                        new_content = file_content + "\n\n" + function_code
                else:
                    new_content = file_content + function_code
            else:
                # Get line info from extracted function
                extracted_info = agent.session_state.get("extracted_function", {})
                if not extracted_info:
                    # Fallback to adding at the end
                    if file_content and not file_content.endswith("\n\n"):
                        if file_content.endswith("\n"):
                            new_content = file_content + "\n" + function_code
                        else:
                            new_content = file_content + "\n\n" + function_code
                    else:
                        new_content = file_content + function_code
                else:
                    end_line = extracted_info["node_info"]["end_lineno"]  # 1-based index
                    
                    # Split into lines and insert the function
                    lines = file_content.splitlines(True)  # Keep line endings
                    
                    # Add newlines if needed
                    insert_content = "\n\n" + function_code
                    
                    # Create updated content
                    new_content = ''.join(lines[:end_line] + [insert_content] + lines[end_line:])
        else:
            # Default to adding at the end
            if file_content and not file_content.endswith("\n\n"):
                if file_content.endswith("\n"):
                    new_content = file_content + "\n" + function_code
                else:
                    new_content = file_content + "\n\n" + function_code
            else:
                new_content = file_content + function_code
                
        # Write back to file
        full_path.write_text(new_content, encoding="utf-8")
        
        # Generate and store diff for patch
        file_diff = generate_diff(file_content, new_content, file_path, file_path)
        agent.session_state["file_diff"] = file_diff
        
        # Store the added function
        agent.session_state["added_function"] = function_code
        
        return f"Function successfully added to {file_path}"
    except Exception as e:
        return f"ERROR: Failed to add function: {e}"


@tool()
def create_patch(agent: Agent) -> str:
    """
    Create a patch from the modification that was performed.
    
    Returns:
        Patch object serialized as a string
    """
    file_diff = agent.session_state.get("file_diff", "")
    if not file_diff:
        return "ERROR: No file diff found in state"
    
    file_path = agent.session_state.get("current_file", "")
    if not file_path:
        return "ERROR: No file path found in state"
    
    # Create a Patch object
    patch = Patch(file_path, file_diff)
    
    # Store the patch in the session state
    agent.session_state["patch"] = patch
    
    # Return a string representation
    return f"Patch created for file {file_path}:\n{file_diff}"


@tool()
def analyze_code_with_semantic_graph(agent: Agent, file_path: str) -> str:
    """
    Analyze a file using the semantic graph tool.
    
    Args:
        file_path: Path to the file to analyze
        
    Returns:
        Semantic analysis results
    """
    project_path = Path(agent.session_state.get("project_path", "."))
    
    try:
        # Create the semantic graph tool
        semantic_tool = SemanticGraphTool(project_path=project_path)
        
        # Initialize the tool with the specific file
        init_result = semantic_tool.initialize(project_path, target_file=file_path)
        
        # Get context for the file
        context_result = semantic_tool.get_context_for_file(file_path)
        
        # Store the semantic context in session state
        agent.session_state["semantic_context"] = context_result
        
        # Return a summary of the context
        return f"Semantic analysis completed for {file_path}:\n" + str(context_result)
    except Exception as e:
        return f"ERROR: Failed to analyze code with semantic graph: {e}"


@tool()
def validate_modification(agent: Agent, file_path: str, modified_code: str) -> str:
    """
    Validate a modified code against semantic rules.
    
    Args:
        file_path: Path to the file
        modified_code: Modified code to validate
        
    Returns:
        Validation results
    """
    project_path = Path(agent.session_state.get("project_path", "."))
    
    try:
        # Create the semantic graph tool
        semantic_tool = SemanticGraphTool(project_path=project_path)
        
        # Initialize the tool with the specific file
        semantic_tool.initialize(project_path, target_file=file_path)
        
        # Determine the modification type
        modification_type = agent.session_state.get("modification_action", "modify")
        
        # Validate the modification
        validation_result = semantic_tool.validate_modification(
            file_path, modification_type, modified_code
        )
        
        # Store the validation result in session state
        agent.session_state["validation_result"] = validation_result
        
        if validation_result.get("valid", False):
            return "Validation passed successfully."
        else:
            errors = validation_result.get("errors", [])
            warnings = validation_result.get("warnings", [])
            
            result = "Validation failed with the following issues:\n\n"
            
            if errors:
                result += "Errors:\n" + "\n".join(f"- {err}" for err in errors) + "\n\n"
                
            if warnings:
                result += "Warnings:\n" + "\n".join(f"- {warn}" for warn in warnings)
                
            return result
    except Exception as e:
        return f"ERROR: Failed to validate modification: {e}"


# Helper functions

def extract_code_from_response(response: str) -> str:
    """Extract function code from the LLM response."""
    # First try to extract code from markdown code blocks
    code_blocks = re.findall(r'```(?:python)?\n(.*?)\n```', response, re.DOTALL)
    if code_blocks:
        return code_blocks[0].strip()
    
    # If no code blocks, use the entire response
    return response.strip()


def generate_diff(original: str, modified: str, from_file: str = "Original", to_file: str = "Modified") -> str:
    """Generate a unified diff between two strings."""
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile=str(from_file),
            tofile=str(to_file),
            lineterm=""
        )
    )


class FunctionModificationTeam:
    """Team of agents that modify, add, or delete functions in code files."""
    
    def __init__(self, project_path: Path,model_id: str = MODEL_ID):
        """
        Initialize the function modification team.
        
        Args:
            project_path: Path to the project root
        """
        self.project_path = project_path
        self.model_id = model_id
        
        # Create the individual agents
        self.analyzer_agent = self._create_analyzer_agent()
        self.modifier_agent = self._create_modifier_agent()
        self.validator_agent = self._create_validator_agent()
        
        # Create the team
        self.team = Team(
            name="Function Modification Team",
            mode="coordinate",
            model=Groq(id=self.model_id),
            session_state={
                "project_path": str(project_path),
                "current_file": None,
                "current_function": None,
                "modification_action": None,
            },
            members=[
                self.analyzer_agent,
                self.modifier_agent,
                self.validator_agent,
            ],
            tools=[
                extract_function,
                create_patch,
            ],
            instructions=[
                "You are a team that modifies, adds, or deletes functions in code files.",
                "You orchestrate the analysis, modification, and validation of code changes.",
                "Always follow this process:",
                "1. Analyze the code and the requested modification using the analyzer agent",
                "2. Apply changes with the modifier agent",
                "3. Validate changes with the validator agent",
                "4. Create and return a patch",
                "Your team state contains important context about the project and modifications."
            ],
            add_state_in_messages=True,  # Include state in messages
            markdown=True,
            show_tool_calls=True,
            show_members_responses=True,
        )
    
    def _create_analyzer_agent(self):
        """Create the code analyzer agent."""
        return Agent(
            name="Code Analyzer",
            role="Analyze code structure and identify modification points",
            model=Groq(id=self.model_id),
            tools=[
                extract_function,
                analyze_code_with_semantic_graph,
            ],
            instructions=[
                "You analyze code files and functions to understand their structure.",
                "Extract the target function and analyze it using the semantic graph tool.",
                "Provide insights about the function's purpose, structure, and relationships.",
                "Always extract the function first before performing any modifications."
            ],
        )
        
    def _create_modifier_agent(self):
        """Create the code modifier agent."""
        return Agent(
            name="Code Modifier",
            role="Modify code according to requirements",
            model=Groq(id=self.model_id),
            tools=[
                modify_function_content,
                apply_function_to_file,
                delete_function,
                add_function,
            ],
            instructions=[
                "You modify code according to specific requirements.",
                "Follow the exact instructions for the modification.",
                "Preserve the coding style and patterns of the original code.",
                "Make minimal changes to achieve the required functionality.",
                "For deletions, ensure clean removal without breaking dependencies.",
                "For additions, follow the file's existing patterns and style."
            ],
        )
        
    def _create_validator_agent(self):
        """Create the code validator agent."""
        return Agent(
            name="Code Validator",
            role="Validate code changes against multiple criteria",
            model=Groq(id=self.model_id),
            tools=[
                validate_modification,
                create_patch,
            ],
            instructions=[
                "You validate code changes to ensure they meet quality standards.",
                "Check for syntax errors, semantic correctness, and style consistency.",
                "Verify that the modification achieves its intended purpose.",
                "Ensure error handling is appropriate.",
                "Create a clean patch for the validated changes.",
                "If validation fails, provide specific feedback on what needs to be fixed."
            ],
        )
        
    def process_modification(self, modification_step: Dict, retrieved_context: Optional[str] = None) -> Union[Patch, Dict]:
        """
        Process a modification request through the team.
        
        Args:
            modification_step: Dictionary with modification details
            retrieved_context: Optional additional context from RAG
            
        Returns:
            Patch object or error dictionary
        """
        # Update the team session state
        self.team.session_state.update({
            "current_file": modification_step.get("file"),
            "current_function": modification_step.get("function"),
            "modification_action": modification_step.get("action", "modify"),
            "modification_what": modification_step.get("what", ""),
            "modification_how": modification_step.get("how", ""),
        })
        
        # Prepare the task for the team
        task = f"""
        # Code Modification Request
        
        ## File Information
        File: {modification_step.get('file')}
        Function: {modification_step.get('function')}
        Action: {modification_step.get('action', 'modify')}
        
        ## Modification Details
        What to do: {modification_step.get('what', '')}
        How to do it: {modification_step.get('how', '')}
        
        """
        
        if retrieved_context:
            task += f"""
            ## Additional Context
            {retrieved_context}
            """
            
        task += """
        ## Instructions
        1. First, use the Code Analyzer to extract and analyze the function
        2. Then, use the Code Modifier to make the requested changes
        3. Next, use the Code Validator to validate the changes
        4. Finally, create a patch for the changes
        
        Return the patch if successful, or detailed error information if the modification fails.
        """
        
        # Execute the team task
        response = self.team.run(task)
        
        # Check if a patch was created
        if "patch" in self.team.session_state:
            return self.team.session_state["patch"]
            
        # If no patch was created but we have file diff information
        if "file_diff" in self.team.session_state:
            file_path = self.team.session_state.get("current_file", "unknown_file")
            file_diff = self.team.session_state.get("file_diff", "")
            return Patch(file_path, file_diff)
            
        # If we have a specific error message from a tool
        for message in self.team.run_response.messages:
            if hasattr(message, "content") and message.content:
                content = message.content
                error_match = re.search(r'ERROR:\s+(.*)', content)
                if error_match:
                    return {"error": error_match.group(1)}
                    
        # Default error response
        return {"error": "Failed to process modification: No patch was created"}


# Create an instance for global use
def get_function_modification_team(project_path: Path,model_id: str = MODEL_ID) -> FunctionModificationTeam:
    """Get or create a function modification team for a project path."""
    # This could be enhanced with caching if needed
    return FunctionModificationTeam(project_path)