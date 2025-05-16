# /Users/caroco/Gabo-Dev/idea_to_code_factory/src/i2c/workflow/modification/code_modifier_adapter.py

from pathlib import Path
from typing import Dict, Optional, Union
import json 
# Import Patch class
from i2c.agents.modification_team.patch import Patch

def apply_modification(
    modification_step: Dict, 
    project_path: Path,
    retrieved_context: Optional[str] = None
) -> Union[Patch, Dict]:
    from i2c.cli.controller import canvas
    
    # Add diagnostic logging
    canvas.info("=" * 40)
    canvas.info(f"APPLYING MODIFICATION: {modification_step.get('what', 'Unknown')}")
    canvas.info(f"Project path: {project_path}")
    canvas.info(f"RAG context: {len(retrieved_context) if retrieved_context else 0} characters")
    canvas.info("=" * 40)
    
    try:
        # Import the clean architecture team builder
        from i2c.agents.modification_team.code_modification_manager import build_code_modification_team, ManagerAgent
        
        # Get the database and embedding model if available
        db = None
        embed_model = None
        try:
            from i2c.db_utils import get_db_connection
            from i2c.workflow.modification.rag_config import get_embed_model
            
            db = get_db_connection()
            embed_model = get_embed_model()
        except Exception as e:
            canvas.warning(f"Error initializing RAG components: {e}")
        
        # Build the team with RAG components
        team = build_code_modification_team(
            project_path=project_path, 
            db=db,
            embed_model=embed_model
        )
        
        # Get the manager agent (it's the first member of the team)
        manager = team.members[0]
        
        # Update the manager's project path
        manager._project_path = project_path
        
        # Create a properly formatted input message for the manager
        from agno.agent import Message
        
        # Read the file to modify
        file_path = modification_step.get("file", "")
        full_file_path = project_path / file_path
        file_content = ""
        if full_file_path.exists() and modification_step.get("action") != "create":
            try:
                file_content = full_file_path.read_text(encoding='utf-8')
                canvas.info(f"Read original file content: {len(file_content)} characters")
            except Exception as e:
                canvas.warning(f"Error reading file {file_path}: {e}")
        
        # Add quality constraints to the message
        quality_constraints = (
            "\n\nQUALITY REQUIREMENTS (MUST FOLLOW):\n"
            "1. Use a consistent data model across all files\n"
            "2. Avoid creating duplicate implementations of the same functionality\n"
            "3. Ensure tests do not have duplicate unittest.main() calls\n"
            "4. If creating a CLI app, use a single approach for the interface\n"
            "5. Use consistent file naming for data storage (e.g., todos.json)\n"
        )
        
        # Create message with modification step, context, and quality constraints
        message_content = {
            "modification_step": modification_step,
            "project_path": str(project_path),
            "retrieved_context": retrieved_context or "",
            "quality_constraints": quality_constraints,
            "original_file_content": file_content
        }
        
        # Call the manager's predict method directly with improved prompting
        # Add stronger emphasis on providing complete, modified content
        enhanced_message = Message(role="user", content=(
            "You MUST generate a specific, complete modification for the file. "
            "Respond with COMPLETE modified file content or a clear unified diff. "
            "Do not return empty content or placeholder responses.\n\n" + 
            json.dumps(message_content)
        ))
        
        # Make multiple attempts if needed
        max_attempts = 2
        for attempt in range(max_attempts):
            canvas.info(f"Making code modification request (attempt {attempt+1}/{max_attempts})")
            response = manager.predict([enhanced_message])
            
            # Log the raw response
            canvas.info(f"Manager response length: {len(response) if response else 0}")
            canvas.info(f"Response preview: {response[:200] if response else 'None'}...")
            
            # Process the response
            if not response or len(response.strip()) < 20:  # Minimum viable length check
                if attempt < max_attempts - 1:
                    canvas.warning(f"Attempt {attempt+1}: Received empty/short response. Retrying...")
                    continue
                else:
                    canvas.warning("All attempts failed with empty responses.")
                    break
                    
            # Try to extract useful content from the response
            patch = None
            
            # Try to parse as JSON first
            try:
                result = json.loads(response)
                
                # Extract unified diff or modified content
                if "unified_diff" in result and result["unified_diff"].strip():
                    file_path = modification_step.get("file", result.get("file_path", "unknown.py"))
                    patch = Patch(file_path=file_path, unified_diff=result["unified_diff"])
                    break
                    
                elif "modified_content" in result and result["modified_content"].strip():
                    file_path = modification_step.get("file", result.get("file_path", "unknown.py"))
                    modified_content = result["modified_content"]
                    
                    # Create a diff between original and modified content
                    patch = Patch(
                        file_path=file_path,
                        unified_diff=(
                            f"--- {file_path}\n"
                            f"+++ {file_path}\n"
                            f"@@ -1,{len(file_content.splitlines()) if file_content else 1} "
                            f"+1,{len(modified_content.splitlines()) if modified_content else 1} @@\n"
                            f"-{file_content}\n"
                            f"+{modified_content}\n"
                        )
                    )
                    break
            except json.JSONDecodeError:
                pass
                
            # Check if it's a markdown response with sections
            if "## Patch" in response:
                try:
                    # Extract patch section
                    patch_section = response.split("## Patch")[1].split("##")[0].strip()
                    if patch_section:
                        patch = Patch(file_path=modification_step.get("file", "unknown.py"), unified_diff=patch_section)
                        break
                except Exception:
                    pass
                    
            # Check if it's a raw diff
            if response.startswith("---") or response.startswith("diff --git"):
                patch = Patch(file_path=modification_step.get("file", "unknown.py"), unified_diff=response)
                break
            
            # Look for code blocks in the response
            import re
            code_block_pattern = r"```(?:python|java|javascript|typescript|html|css|ruby|go|rust|csharp|cpp|c\+\+|c)?(.*?)```"
            matches = re.findall(code_block_pattern, response, re.DOTALL)
            
            if matches:
                # Use the largest code block found
                largest_block = max(matches, key=len).strip()
                if len(largest_block) > 20:  # Ensure it's substantial
                    patch = Patch(
                        file_path=modification_step.get("file", "unknown.py"),
                        unified_diff=(
                            f"--- {modification_step.get('file', 'unknown.py')}\n"
                            f"+++ {modification_step.get('file', 'unknown.py')}\n"
                            f"@@ -1,{len(file_content.splitlines()) if file_content else 1} "
                            f"+1,{len(largest_block.splitlines())} @@\n"
                            f"-{file_content}\n"
                            f"+{largest_block}\n"
                        )
                    )
                    break
            
            # If we received raw code (no markdown, no JSON)
            if len(response.strip()) > 20 and not response.startswith("{") and not response.startswith("<"):
                # Check if it contains import statements, function definitions or class definitions
                # which indicate it might be complete code
                code_indicators = ['import ', 'def ', 'class ', 'function ', 'var ', 'let ', 'const ']
                if any(indicator in response for indicator in code_indicators):
                    patch = Patch(
                        file_path=modification_step.get("file", "unknown.py"),
                        unified_diff=(
                            f"--- {modification_step.get('file', 'unknown.py')}\n"
                            f"+++ {modification_step.get('file', 'unknown.py')}\n"
                            f"@@ -1,{len(file_content.splitlines()) if file_content else 1} "
                            f"+1,{len(response.splitlines())} @@\n"
                            f"-{file_content}\n"
                            f"+{response}\n"
                        )
                    )
                    break
        
        # If we found a valid patch, return it
        if patch:
            return patch
            
        # If we've reached here, retry with a different model or approach
        canvas.warning("Could not extract valid modification from response. Trying a direct approach.")
        
        # Try using a different model directly (outside Agno framework)
        # Import LLM utilities
        from i2c.llm_providers import get_llm_model, LLMProviderType
        try:
            # Get a different provider than what Agno might be using
            llm_model = get_llm_model(provider=LLMProviderType.GROQ, model_tier='highest')
            
            # Build a direct prompt
            prompt = f"""
            You are a code modification expert. Please modify the following file to implement this change:
            
            FILE: {file_path}
            
            REQUESTED CHANGE: {modification_step.get('what', '')}
            
            HOW TO IMPLEMENT: {modification_step.get('how', '')}
            
            ORIGINAL CONTENT:
            ```
            {file_content}
            ```
            
            {quality_constraints}
            
            INSTRUCTIONS:
            1. Return ONLY the complete modified file content with NO explanations or markdown formatting.
            2. The code must be complete, valid, and include the requested change.
            3. Do not use placeholders. Implement the full change.
            4. If there's a test file, ensure there's only one unittest.main() call.
            """
            
            # Make the request
            canvas.info("Making direct request to language model...")
            direct_response = llm_model.generate(prompt)
            direct_content = getattr(direct_response, 'content', str(direct_response))
            
            # Extract code from possible markdown
            if "```" in direct_content:
                code_matches = re.findall(r"```(?:python|java|javascript|.*?)?\n(.*?)\n```", direct_content, re.DOTALL)
                if code_matches:
                    direct_content = code_matches[0].strip()
                    
            # Return a patch with this content if it seems valid
            if len(direct_content) > 20:
                canvas.success("Successfully obtained modified content from direct LLM request")
                return Patch(
                    file_path=file_path,
                    unified_diff=(
                        f"--- {file_path}\n"
                        f"+++ {file_path}\n"
                        f"@@ -1,{len(file_content.splitlines()) if file_content else 1} "
                        f"+1,{len(direct_content.splitlines())} @@\n"
                        f"-{file_content}\n"
                        f"+{direct_content}\n"
                    )
                )
        except Exception as e:
            canvas.warning(f"Error in direct LLM request: {e}")
        
        # As a last resort, create a minimal patch with a comment
        canvas.warning("All approaches failed. Creating minimal patch with TODO comment.")
        return Patch(
            file_path=modification_step.get("file", "unknown.py"),
            unified_diff=f"--- {modification_step.get('file', 'unknown.py')}\n+++ {modification_step.get('file', 'unknown.py')}\n@@ -1,1 +1,2 @@\n+// TODO: Implement {modification_step.get('what', '')}\n{file_content}"
        )
            
    except Exception as e:
        import traceback
        canvas.error(f"Error in team execution: {e}")
        canvas.error(traceback.format_exc())
        return {"error": f"Team execution error: {e}"}