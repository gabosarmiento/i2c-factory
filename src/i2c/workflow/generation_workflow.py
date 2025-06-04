# i2c/workflow/generation_workflow.py
from agno.workflow import Workflow, RunResponse
from pathlib import Path
from typing import Iterator, Dict, Any, AsyncGenerator

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
        
        # Step 0: Knowledge Analysis with KnowledgeTeam (FIXED - NO ASYNC)
        canvas.step("Analyzing context with KnowledgeTeam...")
        try:
            # DEBUG: Verify knowledge_base before using
            if 'knowledge_base' in self.session_state:
                canvas.success("✅ DEBUG: Knowledge base available in GenerationWorkflow")
                kb = self.session_state['knowledge_base']
                test_chunks = kb.retrieve_knowledge("test", limit=1)
                canvas.info(f"🔍 DEBUG: Test retrieval returned {len(test_chunks)} items")
            else:
                canvas.error("❌ DEBUG: NO knowledge_base in GenerationWorkflow session_state!")
                canvas.info(f"🔍 DEBUG: Available keys: {list(self.session_state.keys())}")

            from i2c.agents.knowledge.knowledge_team import build_knowledge_team
            import asyncio

            knowledge_team = build_knowledge_team(self.session_state)
            knowledge_lead = knowledge_team.members[0]

            # CRITICAL DEBUG: Check if KnowledgeTeam can access the database
            canvas.info(f"🔍 CRITICAL: Testing KnowledgeTeam database connection...")
            # Check if knowledge_lead has the required components
            canvas.info(f"🔍 CRITICAL: knowledge_lead.knowledge_manager exists: {knowledge_lead.knowledge_manager is not None}")
            canvas.info(f"🔍 CRITICAL: knowledge_lead.embed_model exists: {knowledge_lead.embed_model is not None}")

            # Test direct database access
            try:
                from i2c.db_utils import get_db_connection
                db = get_db_connection()
                if db and "knowledge_base" in db.table_names():
                    kb_table = db.open_table("knowledge_base")
                    row_count = len(kb_table.to_pandas())
                    canvas.info(f"🔍 CRITICAL: Direct DB access shows {row_count} rows in knowledge_base")
                else:
                    canvas.error(f"🔍 CRITICAL: Direct DB access failed - no knowledge_base table")
            except Exception as e:
                canvas.error(f"🔍 CRITICAL: Direct DB access error: {e}")

            # Test if KnowledgeTeam can retrieve anything
            # Test if KnowledgeTeam can retrieve anything
            if knowledge_lead.knowledge_manager:
                try:
                    test_retrieval = knowledge_lead.knowledge_manager.retrieve_knowledge("test", limit=1)
                    canvas.info(f"🔍 CRITICAL: KnowledgeTeam test retrieval returned {len(test_retrieval)} items")
                    
                    # Test AGNO-specific retrieval
                    agno_retrieval = knowledge_lead.knowledge_manager.retrieve_knowledge("AGNO", limit=3)
                    canvas.info(f"🔍 CRITICAL: AGNO retrieval returned {len(agno_retrieval)} items")
                    
                    if agno_retrieval:
                        for i, item in enumerate(agno_retrieval[:2]):
                            canvas.info(f"🔍 CRITICAL: AGNO item {i}: {str(item)[:200]}...")
                    
                except Exception as e:
                    canvas.error(f"🔍 CRITICAL: KnowledgeTeam retrieval failed: {e}")
            else:
                canvas.error(f"🔍 CRITICAL: KnowledgeTeam has no knowledge_manager!")
                

            current_project_path = Path(self.session_state.get("project_path", "."))
            task = structured_goal.get("objective", "")
            
            canvas.info(f"🔍 DEBUG: Using KnowledgeTeam to analyze task: {task}")
            
            # CALL IT SYNCHRONOUSLY
            project_context = asyncio.run(knowledge_lead.analyze_project_context(
                project_path=current_project_path,
                task=task
            ))
            
            canvas.info(f"🔍 DEBUG: KnowledgeTeam analysis complete")

            # DEBUG: Log what the KnowledgeTeam actually found
            canvas.info(f"🔍 DEBUG: Project context keys: {list(project_context.keys())}")

            if "documentation" in project_context:
                docs = project_context["documentation"]
                canvas.info(f"🔍 DEBUG: Documentation keys: {list(docs.keys())}")
                
                if "references" in docs:
                    refs = docs["references"]
                    canvas.info(f"🔍 DEBUG: Found {len(refs)} references")
                    for i, ref in enumerate(refs[:2]):
                        canvas.info(f"🔍 DEBUG: Ref {i}: {str(ref)[:200]}...")

            if "best_practices" in project_context:
                bp = project_context["best_practices"]
                canvas.info(f"🔍 DEBUG: Found {len(bp)} best practices")
                for i, practice in enumerate(bp[:2]):
                    canvas.info(f"🔍 DEBUG: Practice {i}: {str(practice)[:200]}...")

            # Store the context
            self.session_state["knowledge_context"] = project_context

            yield RunResponse(content=f"🧠 Knowledge analysis completed")
            
        except Exception as e:
            canvas.error(f"KnowledgeTeam error: {e}")
            yield RunResponse(content=f"⚠️ Knowledge analysis failed: {e}")
        
        # Step 1: Plan Files
        for item in self.planning_phase(structured_goal):
            yield item

        # Step 2: Code Generation
        for item in self.code_generation_phase():
            yield item

        # Step 3: Unit Tests
        for item in self.unit_test_phase():
            yield item

        # Step 4: Quality Checks
        quality_result = self.quality_check_phase()
        yield quality_result

        # Step 5: Write Files to Disk
        for item in self.file_writing_phase(project_path):
            yield item

        # Step 5.5: Extract API routes if system has APIs and UI
        arch_context = self.session_state.get("architectural_context", {})
        system_type = arch_context.get("system_type")
        canvas.info(f"🔍 DEBUG: System type: {system_type}")
        canvas.info(f"🔍 DEBUG: Arch context: {arch_context}")
        if system_type in ["fullstack_web_app", "microservices"]:
            canvas.step("Extracting API routes for UI integration...")
            try:
                from i2c.utils.api_route_tracker import inject_api_routes_into_session
                project_path = Path(self.session_state.get("project_path", ""))
                canvas.info(f"🔍 DEBUG: Project path: {project_path}")
                canvas.info(f"🔍 DEBUG: Files in project: {list(project_path.rglob('*.py'))}")
                self.session_state = inject_api_routes_into_session(project_path, self.session_state)
                canvas.success("✅ API routes extracted for frontend integration")
            except Exception as e:
                canvas.warning(f"⚠️ API route extraction failed: {e}")
                
        # Step 6: Index files for RAG
        for item in self.index_files_phase(project_path):
            yield item

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


    async def knowledge_analysis_phase(self, structured_goal: dict, project_path: Path) -> AsyncGenerator[RunResponse, None]:
        """Use KnowledgeTeam to analyze context before generation."""
        canvas.step("Analyzing project context with KnowledgeTeam...")
        
        try:
            # Import and build the KnowledgeTeam
            from i2c.agents.knowledge.knowledge_team import build_knowledge_team
            
            knowledge_team = build_knowledge_team(self.session_state)
            knowledge_lead = knowledge_team.members[0]  # Get the KnowledgeLeadAgent
            
            # Use the KnowledgeTeam to analyze the task context
            task = structured_goal.get("objective", "")
            project_context = await knowledge_lead.analyze_project_context(
                project_path=project_path,
                task=task
            )
            
            # Store the rich context in session state
            self.session_state["knowledge_context"] = project_context
            self.session_state["knowledge_team"] = knowledge_team
            
            # Extract and store retrieved context for the enhancer system
            if "documentation" in project_context:
                docs = project_context["documentation"].get("references", [])
                if docs:
                    context_parts = []
                    for doc in docs:
                        context_parts.append(f"Source: {doc.get('source', 'Unknown')}")
                        context_parts.append(doc.get('content', ''))
                        context_parts.append("---")
                    
                    self.session_state["retrieved_context"] = "\n".join(context_parts)
                    canvas.success(f"🧠 KnowledgeTeam provided context: {len(docs)} knowledge items")
            
            yield RunResponse(
                content=f"🧠 Knowledge analysis completed: Found {len(project_context.get('documentation', {}).get('references', []))} knowledge items",
                extra_data={"project_context": project_context}
            )
            
        except Exception as e:
            canvas.error(f"Error in knowledge analysis: {e}")
            yield RunResponse(
                content=f"⚠️ Knowledge analysis failed: {e}",
                extra_data={"error": str(e)}
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
            plan_prompt = f"""Objective: {objective}
            Language: {language}{constraints_text}

            CRITICAL: You must return ONLY a valid JSON object with this exact structure:
            {{"files": ["path/to/file1.py", "path/to/file2.py", "path/to/file3.py"]}}

            Do not include any explanations, markdown, or reasoning. Return ONLY the raw JSON object.
            The files should use AGNO framework patterns from your knowledge context."""
            
            # Get RAG-enabled planner with session state
            
            from i2c.agents.core_agents import get_rag_enabled_agent
            planner = get_rag_enabled_agent("planner", session_state=self.session_state)

            # DEBUG: Check if planner has knowledge context
            if self.session_state and "retrieved_context" in self.session_state:
                canvas.info(f"🧠 DEBUG: Planner has knowledge context: {len(self.session_state['retrieved_context'])} chars")
                canvas.info(f"🔍 DEBUG: Context preview: {self.session_state['retrieved_context'][:150]}...")
            else:
                canvas.warning("⚠️ DEBUG: Planner missing knowledge context")

            if hasattr(planner, '_enhanced_with_knowledge'):
                canvas.info(f"✅ DEBUG: Planner enhanced with knowledge")
            else:
                canvas.warning("⚠️ DEBUG: Planner not enhanced with knowledge")
            
            # Use the enhanced planner
            response = planner.run(plan_prompt)
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Process response into file list
            # Process response into file list using robust JSON extraction
            from i2c.utils.json_extraction import extract_json_with_fallback

            # DEBUG: Log what the planner actually returned
            canvas.info(f"🔍 DEBUG: Planner raw response: {content[:200]}...")

            # Fallback file plan in case JSON extraction fails
            fallback_plan = ["backend/main.py", "backend/app.py", "frontend/src/App.jsx"]

            try:
                # Use the robust JSON extractor
                file_plan_data = extract_json_with_fallback(content, fallback={"files": fallback_plan})
                
                # Handle different response formats
                if isinstance(file_plan_data, dict):
                    file_plan = file_plan_data.get("files", file_plan_data.get("file_plan", fallback_plan))
                elif isinstance(file_plan_data, list):
                    file_plan = file_plan_data
                else:
                    file_plan = fallback_plan
                    
                if not isinstance(file_plan, list):
                    canvas.warning("Planner response was not a list, using fallback")
                    file_plan = fallback_plan
                    
                canvas.info(f"🔍 DEBUG: Extracted file plan: {file_plan}")
                
            except Exception as e:
                canvas.error(f"JSON extraction failed: {e}")
                file_plan = fallback_plan
                canvas.warning("Using fallback file plan due to extraction error")
                
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

        # DEBUG: Check if AGNO knowledge is still available for code generation
        if "knowledge_context" in self.session_state:
            kc = self.session_state["knowledge_context"]
            if "documentation" in kc:
                refs = kc["documentation"].get("references", [])
                canvas.info(f"🔍 DEBUG: Code generation has {len(refs)} knowledge references")
                
                # Check if any reference contains AGNO content
                agno_found = False
                for ref in refs:
                    if isinstance(ref, dict) and "content" in ref:
                        if "agno" in ref["content"].lower():
                            agno_found = True
                            break
                canvas.info(f"🔍 DEBUG: AGNO content found in knowledge: {agno_found}")
            else:
                canvas.warning("🔍 DEBUG: No documentation in knowledge_context")
        else:
            canvas.warning("🔍 DEBUG: No knowledge_context in session_state")

        file_plan = self.session_state.get("file_plan", [])
        
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
                    f"Generate complete, runnable code for the file '{file_path}'.\n\n"
                    f"IMPORTANT: Use any specific frameworks, patterns, or imports mentioned in your instructions above. "
                    f"Do not generate generic code if specific patterns are provided."
                )
                
                # Get RAG-enabled code builder with session state
                from i2c.agents.core_agents import get_rag_enabled_agent
                builder = get_rag_enabled_agent("code_builder", session_state=self.session_state)

                # DEBUG: Check if builder has knowledge context
                if hasattr(builder, '_enhanced_with_knowledge'):
                    canvas.info(f"✅ DEBUG: Builder enhanced with {len(builder._knowledge_patterns)} patterns")
                    canvas.info(f"🔍 DEBUG: First pattern: {list(builder._knowledge_patterns.keys())[0] if builder._knowledge_patterns else 'None'}")
                else:
                    canvas.warning("⚠️ DEBUG: Builder not enhanced with knowledge")

                if hasattr(builder, 'instructions') and isinstance(builder.instructions, list):
                    canvas.info(f"📋 DEBUG: Builder has {len(builder.instructions)} instructions")
                    canvas.info(f"🔍 DEBUG: First instruction: {builder.instructions[0][:100] if builder.instructions else 'None'}...")
                    
                    # ADD DETAILED DEBUG
                    canvas.info(f"📋 DEBUG: Builder instructions preview:")
                    for i, instruction in enumerate(builder.instructions[:3]):
                        canvas.info(f"  {i+1}: {instruction[:100]}...")
                    
                    # Check if knowledge is actually in the instructions
                    instructions_text = " ".join(builder.instructions).lower()
                    knowledge_indicators = ['agno', 'agent', 'team', 'framework', 'import', 'pattern']
                    found_indicators = [word for word in knowledge_indicators if word in instructions_text]
                    canvas.info(f"🔍 DEBUG: Knowledge indicators in instructions: {found_indicators}")

                # Use the enhanced builder
                response = builder.run(build_prompt)

                raw = response.content if hasattr(response, 'content') else str(response)

                # Clean code response and remove any "Applied patterns" documentation
                from i2c.utils.markdown import strip_markdown_code_block
                print(f"DEBUG: Content ends with: {repr(code[-20:])}")
                code = strip_markdown_code_block(raw)
                print(f"DEBUG: After strip ends with: {repr(code[-20:])}")
                # Remove any "Applied patterns" or similar documentation sections
                import re
                code = re.sub(r'\n*Applied patterns:.*$', '', code, flags=re.DOTALL | re.MULTILINE)
                code = re.sub(r'\n*# Applied patterns:.*$', '', code, flags=re.DOTALL | re.MULTILINE)
                    
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
        """Write files to disk and validate knowledge application."""
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
            
            # NEW: Validate knowledge application after writing files
            if self.session_state.get("retrieved_context") and code_map:
                canvas.step("Validating knowledge application...")
                
                try:
                    from i2c.agents.knowledge.knowledge_validator import KnowledgeValidator
                    
                    validator = KnowledgeValidator()
                    validation_result = validator.validate_generation_output(
                        generated_files=code_map,
                        retrieved_context=self.session_state["retrieved_context"],
                        task_description=self.session_state.get("objective", "")
                    )
                    
                    # Store validation results
                    self.session_state["knowledge_validation"] = {
                        "success": validation_result.success,
                        "score": validation_result.score,
                        "violations": validation_result.violations,
                        "applied_patterns": validation_result.applied_patterns
                    }
                    
                    # Report validation results
                    if validation_result.success:
                        canvas.success(f"✅ Knowledge validation passed (score: {validation_result.score:.2f})")
                        yield RunResponse(
                            content=f"✅ Knowledge validation: {validation_result.score:.2f}/1.0",
                            extra_data={
                                "validation_success": True,
                                "validation_score": validation_result.score,
                                "applied_patterns": validation_result.applied_patterns
                            }
                        )
                    else:
                        canvas.warning(f"⚠️ Knowledge validation issues (score: {validation_result.score:.2f})")
                        canvas.warning(f"Violations: {', '.join(validation_result.violations[:3])}")
                        
                        yield RunResponse(
                            content=f"⚠️ Knowledge validation: {validation_result.score:.2f}/1.0 - some patterns not applied",
                            extra_data={
                                "validation_success": False,
                                "validation_score": validation_result.score,
                                "violations": validation_result.violations[:5],  # Limit for readability
                                "missing_patterns": validation_result.missing_patterns
                            }
                        )
                    
                except Exception as validation_error:
                    canvas.warning(f"Knowledge validation failed: {validation_error}")
                    self.session_state["knowledge_validation_error"] = str(validation_error)
                    
                    yield RunResponse(
                        content="⚠️ Knowledge validation could not be completed",
                        extra_data={"validation_error": str(validation_error)}
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
            
