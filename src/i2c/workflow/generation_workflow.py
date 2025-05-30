# i2c/workflow/generation_workflow.py
from agno.workflow import Workflow, RunResponse
from pathlib import Path
from typing import Iterator, Dict, Any

# Import existing agents

from i2c.agents.sre_team import unit_test_generator, code_quality_sentinel
from i2c.workflow.modification.file_operations import write_files_to_disk
from i2c.cli.controller import canvas

class GenerationWorkflow(Workflow):
    """
    Agno workflow for project generation cycle.
    Uses existing agents and follows the same steps as execute_generation_cycle.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_state.setdefault("generation_memory", [])
        
    def run(self, structured_goal: dict, project_path: Path) -> Iterator[RunResponse]:
        """Execute the generation workflow, yielding responses at each step."""
        canvas.start_process(f"Generation Cycle for: {project_path.name}")
        
        # Initialize session state
        self.session_state["generation_memory"] = []
        self.session_state["language"] = structured_goal.get("language")
        self.session_state["objective"] = structured_goal.get("objective")
        self.session_state["code_map"] = None
        
        # Start workflow
        yield RunResponse(content=f"🚀 Starting Generation Workflow for: {project_path.name}")
        
        # Step 1: Plan Files
        yield from self.planning_phase(structured_goal)
        
        # Step 2: Code Generation
        yield from self.code_generation_phase()
        
        # Step 3: Unit Tests
        yield from self.unit_test_phase()
        
        # Step 4: Quality Checks
        quality_result = self.quality_check_phase()
        yield quality_result
        
        # Step 5: Write Files to Disk
        yield from self.file_writing_phase(project_path)
        
        # Step 6: Index files for RAG
        yield from self.index_files_phase(project_path)
        # Final status
        success = bool(self.session_state.get("code_map"))
        canvas.end_process(f"Generation cycle for {project_path.name} {'completed successfully' if success else 'failed'}")
        
        yield RunResponse(
            content=f"✅ Generation Workflow {'completed successfully' if success else 'failed'}",
            extra_data={
                "success": success,
                "language": self.session_state.get("language"),
                "code_map": self.session_state.get("code_map")
            }
        )
    
    # In generation_workflow.py
    def planning_phase(self, structured_goal: dict) -> Iterator[RunResponse]:
        """Plan files based on structured goal."""
        canvas.step("Planning minimal file structure...")
        
        language = structured_goal.get("language")
        objective = structured_goal.get("objective")
        
        try:
            # Check for constraints and add them to the prompt
            constraints_text = ""
            if "constraints" in structured_goal:
                constraints_text = "\n\n# QUALITY CONSTRAINTS (MUST FOLLOW):\n"
                for i, constraint in enumerate(structured_goal["constraints"], 1):
                    constraints_text += f"{i}. {constraint}\n"
                canvas.info(f"Added {len(structured_goal['constraints'])} quality constraints to planning prompt")
            
            # Build the plan prompt with constraints
            plan_prompt = f"Objective: {objective}\nLanguage: {language}{constraints_text}"
            
            # Get RAG-enabled planner with session state
            from i2c.agents.core_agents import get_rag_enabled_agent
            planner = get_rag_enabled_agent("planner", self.session_state)
            
            # Use the enhanced planner
            response = planner.run(plan_prompt)
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Process response into file list
            import json
            content_processed = content.strip()
            if "```" in content_processed:
                content_processed = content_processed.split("```")[1].strip()
                if content_processed.startswith("json"):
                    content_processed = content_processed[4:].strip()
            
            file_plan = json.loads(content_processed)
            if not isinstance(file_plan, list):
                raise ValueError("Planner did not return a list.")
                
            # Store in session state
            self.session_state["file_plan"] = file_plan
            
            canvas.success(f"Planned files: {file_plan}")
            yield RunResponse(
                content=f"📑 File planning completed: {len(file_plan)} files",
                extra_data={"file_plan": file_plan}
            )
        except Exception as e:
            self.session_state["error"] = f"Planning error: {str(e)}"
            canvas.error(f"Error planning files: {e}")
            yield RunResponse(
                content=f"❌ File planning failed: {e}",
                extra_data={"error": str(e)}
            )
            
    def code_generation_phase(self) -> Iterator[RunResponse]:
        """Generate code for planned files."""
        canvas.step("Generating code files...")
        
        file_plan = self.session_state.get("file_plan", [])
        objective = self.session_state.get("objective")
        language = self.session_state.get("language")
        generated_code = {}
        
        # Check for constraints and add them to the prompt
        constraints_text = ""
        if "constraints" in self.session_state:
            constraints_text = "\n\n# QUALITY CONSTRAINTS (MUST FOLLOW):\n"
            for i, constraint in enumerate(self.session_state["constraints"], 1):
                constraints_text += f"{i}. {constraint}\n"
            canvas.info(f"Added {len(self.session_state['constraints'])} quality constraints to code generation prompt")
        
        try:
            for file_path in file_plan:
                build_prompt = (
                    f"Objective: {objective}\nLanguage: {language}{constraints_text}\n"
                    f"Generate complete, runnable code for the file '{file_path}'."
                )
                # Get RAG-enabled code builder with session state
                from i2c.agents.core_agents import get_rag_enabled_agent
                builder = get_rag_enabled_agent("code_builder", self.session_state)
                
                # Use the enhanced builder
                response = builder.run(build_prompt)
                
                raw = response.content if hasattr(response, 'content') else str(response)
                
                # Clean code response
                if raw.strip().startswith("```"):
                    lines = raw.splitlines()
                    if lines and lines[0].strip().startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip().startswith("```"):
                        lines = lines[:-1]
                    code = "\n".join(lines)
                else:
                    code = raw
                    
                generated_code[file_path] = code.strip()
                canvas.success(f"Generated: {file_path}")
                
                yield RunResponse(
                    content=f"🔧 Generated file: {file_path}",
                    extra_data={"file": file_path, "length": len(code)}
                )
                
            # Store in session state
            self.session_state["generated_code"] = generated_code
        except Exception as e:
            self.session_state["error"] = f"Code generation error: {str(e)}"
            canvas.error(f"Error generating code: {e}")
            yield RunResponse(
                content=f"❌ Code generation failed: {e}",
                extra_data={"error": str(e)}
            )
            
    def unit_test_phase(self) -> Iterator[RunResponse]:
        """Generate unit tests for code."""
        canvas.step("Generating Unit Tests...")
        
        generated_code = self.session_state.get("generated_code", {})
        
        try:
            code_map_with_tests = unit_test_generator.generate_tests(generated_code)
            
            # Store in session state
            self.session_state["code_map"] = code_map_with_tests
            
            yield RunResponse(
                content=f"🧪 Unit test generation completed: {len(code_map_with_tests)} files",
                extra_data={"code_map": code_map_with_tests}
            )
        except Exception as e:
            # On failure, use original code
            self.session_state["code_map"] = generated_code
            self.session_state["test_error"] = str(e)
            canvas.error(f"Error during Unit Test Generation: {e}")
            canvas.warning("Proceeding without generated unit tests due to error.")
            
            yield RunResponse(
                content=f"⚠️ Unit test generation failed: {e}",
                extra_data={"error": str(e)}
            )
    
    def quality_check_phase(self) -> RunResponse:
        """Run quality checks on code."""
        canvas.step("Performing SRE Code Quality Check...")
        
        code_map = self.session_state.get("code_map", {})
        
        try:
            issues = code_quality_sentinel.check_code(code_map)
            
            # Store quality check results
            self.session_state["quality_issues"] = issues
            
            if issues:
                canvas.warning(f"Code quality issues found: {len(issues)}")
                return RunResponse(
                    content=f"⚠️ Quality check found {len(issues)} issues",
                    extra_data={"issues": issues}
                )
            else:
                canvas.success("Code quality checks passed.")
                return RunResponse(
                    content="✅ Quality check passed",
                    extra_data={"issues": []}
                )
        except Exception as e:
            self.session_state["quality_error"] = str(e)
            canvas.error(f"Error during SRE Quality Check: {e}")
            return RunResponse(
                content=f"❌ Quality check failed: {e}",
                extra_data={"error": str(e)}
            )
    
    def file_writing_phase(self, project_path: Path) -> Iterator[RunResponse]:
        """Write files to disk."""
        canvas.step("Writing files to disk...")
        
        code_map = self.session_state.get("code_map", {})
        
        try:
            # Create __init__.py files
            def ensure_init_py(path: Path):
                init_file = path / "__init__.py"
                if not init_file.exists():
                    init_file.touch()
                    canvas.success(f"✅ [AutoPatch] Created missing __init__.py at {init_file}")
            
            # Write files
            write_files_to_disk(code_map, project_path)
            
            # Ensure packages
            ensure_init_py(project_path.parent)
            ensure_init_py(project_path)
            
            yield RunResponse(
                content=f"📝 Wrote {len(code_map)} files to disk",
                extra_data={"files_written": len(code_map)}
            )
        except Exception as e:
            self.session_state["file_write_error"] = str(e)
            canvas.error(f"Error during file writing step: {e}")
            yield RunResponse(
                content=f"❌ File writing failed: {e}",
                extra_data={"error": str(e)}
            )
            
    def index_files_phase(self, project_path: Path) -> Iterator[RunResponse]:
        """Index generated files for RAG retrieval."""
        canvas.step("Indexing code for RAG context...")

        try:
            from i2c.agents.modification_team.context_reader.context_reader_agent import ContextReaderAgent

            # ✅ DO NOT recreate LanceDB tables here
            # Just index the project using the agent
            reader_agent = ContextReaderAgent(project_path)
            status = reader_agent.index_project_context()

            # ⚠️ Warn but don't fail if there were errors
            if status.get('errors'):
                canvas.warning(f"\u26a0\ufe0f Indexing completed with errors: {status.get('errors')}")
                yield RunResponse(
                    content=f"\u26a0\ufe0f Code indexing completed with issues",
                    extra_data={"indexing_status": status}
                )
            else:
                canvas.success(f"✅ Indexed {status.get('files_indexed')} files ({status.get('chunks_indexed')} chunks) for RAG context")
                yield RunResponse(
                    content=f"📚 Indexed {status.get('files_indexed')} files for context",
                    extra_data={"indexing_status": status}
                )

        except Exception as e:
            canvas.error(f"❌ Error during code indexing: {e}")
            yield RunResponse(
                content=f"❌ Code indexing failed: {e}",
                extra_data={"error": str(e)}
            )
            
