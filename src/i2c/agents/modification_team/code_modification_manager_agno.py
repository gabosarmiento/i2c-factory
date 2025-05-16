# code_modification_manager_agno.py
"""
Code Modification Manager using Agno: A drop-in replacement that leverages Agno's team capabilities.
Simply save this file alongside your existing code_modification_manager.py and update one import line.
"""

import json
import os
import re
import pathlib
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.team.team import Team
from builtins import llm_middle, llm_highest

# Keep these compatible with your existing classes
@dataclass
class ModificationRequest:
    project_root: str
    user_prompt: str
    rag_context: str = ""

@dataclass
class AnalysisResult:
    details: str = ""

@dataclass
class ModPayload:
    file_path: str
    original: str
    modified: str

@dataclass
class ModificationPlan:
    diff_hints: str

class ModifierAdapter:
    """Drop-in replacement for the existing ModifierAdapter using Agno's team capabilities."""
    
    def __init__(self, agent=None):
        """Initialize with an optional agent (not used but kept for compatibility)."""
        # Build the team directly - ignore the passed agent
        self.team = self._build_modification_team()
    
    def _build_modification_team(self) -> Team:
        """Build the Agno team for code modification."""
        analyzer_agent = Agent(
            name="AnalyzerAgent",
            model=llm_middle,
            role="Code Analyzer",
            instructions=[
                "You are an expert code analyzer who examines code structure and patterns.",
                "Focus on understanding functions, parameters, and requirements in the modification request.",
                "IMPORTANT: Identify ALL requirements, especially parameter additions."
            ],
        )
        
        modifier_agent = Agent(
            name="ModifierAgent",
            model=llm_highest,
            role="Code Modifier",
            instructions=[
                "You are an expert code modifier. Your PRIMARY responsibility is to correctly implement ALL requested changes.",
                "CRITICAL REQUIREMENTS:",
                "1. When asked to add parameters to functions, ALWAYS include them in the function signature",
                "2. For test files, ensure there's only ONE unittest.main() call at the end",
                "3. NEVER include 'unknown.py' template fragments in your code",
                "VERIFY all parameters are added and the implementation uses them correctly.",
            ],
        )
        
        validator_agent = Agent(
            name="ValidatorAgent",
            model=llm_middle,
            role="Code Validator",
            instructions=[
                "You are an expert code validator. Verify that ALL requirements are implemented.",
                "Check specifically for:",
                "1. Parameters requested in the modification are present in function signatures",
                "2. Implementation uses new parameters correctly",
                "3. No unittest.main() duplicates in test files",
                "4. No 'unknown.py' template fragments",
                "If requirements are missing, identify what's missing."
            ],
        )
        
        return Team(
            name="Code Modification Team",
            mode="coordinate",
            model=llm_middle,
            members=[analyzer_agent, modifier_agent, validator_agent],
            instructions=[
                "You are a team that modifies code based on user requirements.",
                "WORKFLOW:",
                "1. Analyze the modification request to identify ALL requirements",
                "2. Have the AnalyzerAgent examine the relevant file(s)",
                "3. Have the ModifierAgent implement ALL required changes",
                "4. Have the ValidatorAgent verify that ALL requirements were implemented",
                "5. If validation fails, return to the ModifierAgent with specific issues",
                "6. Return the result as a JSON object with file_path, original, and modified fields"
            ],
            enable_agentic_context=True,
            share_member_interactions=True,
        )
    
    def _extract_file_info(self, request: ModificationRequest) -> dict:
        """Extract file path, what, and how from the request."""
        try:
            data = json.loads(request.user_prompt)
            if isinstance(data, dict):
                file_path = data.get("file", "unknown.py")
                what = data.get("what", "")
                how = data.get("how", "")
                
                # Try to read the original file content
                abs_path = os.path.join(request.project_root, file_path)
                original_content = ""
                try:
                    if os.path.exists(abs_path):
                        with open(abs_path, 'r') as f:
                            original_content = f.read()
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")
                
                return {
                    "file_path": file_path,
                    "what": what,
                    "how": how,
                    "original_content": original_content
                }
        except Exception as e:
            print(f"Error parsing request: {e}")
        
        # Default file info
        return {
            "file_path": "unknown.py",
            "what": "",
            "how": "",
            "original_content": ""
        }
    
    def modify(self, request: ModificationRequest, analysis: AnalysisResult) -> ModificationPlan:
        """
        Modify code based on the request and analysis - drop-in replacement for existing method.
        
        Args:
            request: The modification request
            analysis: Analysis results
            
        Returns:
            ModificationPlan with diff hints
        """
        print(f"ModifierAdapter (Agno version): Processing modification request")
        
        # Extract info from the request
        file_info = self._extract_file_info(request)
        file_path = file_info["file_path"]
        what = file_info["what"]
        how = file_info["how"]
        original_content = file_info["original_content"]
        
        # Prepare the request for the team
        team_request = {
            "file": file_path,
            "what": what,
            "how": how,
            "original_content": original_content,
            "project_root": request.project_root,
            "rag_context": request.rag_context if hasattr(request, 'rag_context') else "",
            "analysis": analysis.details if analysis else ""
        }
        
        # Send the request to the team
        print(f"Sending request to Agno team: {json.dumps(team_request)[:200]}...")
        response = self.team.run(json.dumps(team_request))
        print(f"Received response from Agno team")
        
        # Extract and process the response
        response_content = response.content
        if isinstance(response_content, str):
            try:
                # Try to parse as JSON
                result = json.loads(response_content)
            except json.JSONDecodeError:
                # Fallback if not valid JSON
                result = {
                    "file_path": file_path,
                    "original": original_content,
                    "modified": response_content
                }
        elif isinstance(response_content, dict):
            # Already a dictionary
            result = response_content
        else:
            # Fallback for unexpected response types
            result = {
                "file_path": file_path,
                "original": original_content,
                "modified": str(response_content)
            }
            
        # Ensure all required fields are present
        result["file_path"] = result.get("file_path", file_path)
        result["original"] = result.get("original", original_content)
        result["modified"] = result.get("modified", original_content)
        
        # Apply post-processing to fix common issues
        modified_content = result["modified"]
        
        # Fix duplicate unittest.main() calls
        if file_path.startswith('test_') and file_path.endswith('.py') and 'unittest.main()' in modified_content:
            main_calls = modified_content.count('unittest.main()')
            if main_calls > 1:
                print(f"Fixing multiple unittest.main() calls in {file_path}")
                lines = modified_content.splitlines()
                main_indices = [i for i, line in enumerate(lines) if 'unittest.main()' in line]
                
                # Keep only the last unittest.main() call
                for idx in main_indices[:-1]:
                    lines[idx] = f"#     unittest.main() # Removed duplicate"
                
                modified_content = '\n'.join(lines)
        
        # Fix unknown.py fragments
        if "unknown.py" in modified_content:
            print(f"Removing 'unknown.py' template in {file_path}")
            lines = modified_content.splitlines()
            filtered_lines = [line for line in lines if "unknown.py" not in line]
            modified_content = '\n'.join(filtered_lines)
        
        # Update the result with the fixed content
        result["modified"] = modified_content
        
        # Create and return the ModificationPlan
        return ModificationPlan(diff_hints=json.dumps(result))

# Drop-in replacement function for your orchestrator
def build_code_modification_team(**kwargs):
    """
    Build a code modification team using Agno.
    This is a drop-in replacement for your existing function.
    
    Returns:
        The ModifierAdapter that integrates with your existing system
    """
    # Create and return a ModifierAdapter with Agno team
    return ModifierAdapter()

# Example usage - identical to your existing code
"""
from i2c.agents.modification_team.code_modification_manager_agno import build_code_modification_team

# In your orchestrator, just update the import line:
# Old: from i2c.agents.modification_team.code_modification_manager import build_code_modification_team
# New: from i2c.agents.modification_team.code_modification_manager_agno import build_code_modification_team

# Everything else stays the same
team = build_code_modification_team()
"""