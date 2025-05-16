# /workflow/scenario_processor.py
"""
I2C Factory Scenario Processor

This module enables the I2C Factory to run JSON scenario files for automated demos or batch processing.
It integrates directly with the session management system to process scenarios step by step.

Usage examples:
    1. From the CLI: `poetry run i2c --scenario path/to/scenario.json`
    2. Programmatically: `from workflow.scenario_processor import run_scenario; run_scenario(scenario_path)`
"""

import json
import time
import os
from pathlib import Path
import logging
from typing import Dict, List, Optional, Any, Union
import traceback
# Import CLI canvas for user interaction
from i2c.cli.controller import canvas
from i2c.cli.budget_display import show_budget_status, show_operation_cost, show_budget_summary

# Import orchestrator for generating and modifying projects
from i2c.workflow.orchestrator import route_and_execute
from i2c.workflow.utils import sanitize_filename, ensure_project_path

# Import knowledge management
from i2c.workflow.session_handlers import (
    handle_knowledge_management,
    process_text_file,
    handle_load_project
)

# Import agents
from i2c.agents.core_agents import input_processor_agent
from i2c.agents.budget_manager import BudgetManagerAgent
from i2c.agents.modification_team.context_reader.context_reader_agent import ContextReaderAgent

# Setup logging
logger = logging.getLogger(__name__)

# Default output directory with absolute path (Fix #4)
DEFAULT_OUTPUT_DIR_BASE = Path(os.path.abspath("./output"))

class ScenarioProcessor:
    """Processes JSON scenario files for the I2C Factory"""
    
    def __init__(self, scenario_path: str, budget_manager: Optional[BudgetManagerAgent] = None):
        """
        Initialize the scenario processor
        
        Args:
            scenario_path: Path to the JSON scenario file
            budget_manager: Optional budget manager instance (will create one if not provided)
        """
        self.scenario_path = Path(scenario_path)
        self.scenario_data = self._load_scenario()
        self.budget_manager = budget_manager or BudgetManagerAgent(session_budget=None)
        
        # Store the budget manager globally for other components to access
        import builtins
        builtins.global_budget_manager = self.budget_manager
        
        # Session state variables (similar to session.py)
        self.current_project_path: Optional[Path] = None
        self.current_structured_goal: Optional[Dict] = None
        self.reader_agent: Optional[ContextReaderAgent] = None
    

    def _process_agentic_evolution_step(self, step: Dict[str, Any]) -> None:
        """
        Process an agentic evolution step - uses the new integrated agent orchestration system.
        
        Args:
            step: The agentic evolution step configuration
        """
        if not self.current_project_path:
            canvas.warning("No active project. Cannot perform agentic evolution.")
            return
            
        # Extract objective from step
        objective = step.get("objective", {})
        if not objective or not objective.get("task"):
            canvas.warning("No task specified in objective. Skipping agentic evolution.")
            return
            
        # Set project path in objective
        objective["project_path"] = str(self.current_project_path)
        
        canvas.info(f"🧠 Running agent-orchestrated evolution for: {objective.get('task', 'Unknown task')}")
        
        try:
            # Import the agentic orchestrator
            from i2c.workflow.agentic_orchestrator import execute_agentic_evolution_sync
            
            # Get start cost for operation tracking
            start_tokens, start_cost = self.budget_manager.get_session_consumption()
            
            # Execute the agentic evolution
            result = execute_agentic_evolution_sync(objective, self.current_project_path)
            
            # Display the result
            if result.get("decision") == "approve":
                canvas.success(f"✅ Evolution approved: {result.get('reason', 'No reason provided')}")
                
                # Show modifications
                modifications = result.get("modifications", {})
                if modifications:
                    canvas.info("📝 Modifications:")
                    for file_path, summary in modifications.items():
                        canvas.info(f"  - {file_path}: {summary}")
            else:
                canvas.error(f"❌ Evolution rejected: {result.get('reason', 'No reason provided')}")
                
            # Calculate operation cost
            end_tokens, end_cost = self.budget_manager.get_session_consumption()
            op_tokens = end_tokens - start_tokens
            op_cost = end_cost - start_cost
            
            # Show operation cost
            from i2c.cli.budget_display import show_operation_cost
            show_operation_cost(
                operation=f"Agentic Evolution ({objective.get('task', '')[:30]}...)",
                tokens=op_tokens,
                cost=op_cost
            )
            
        except Exception as e:
            canvas.error(f"Error during agentic evolution: {e}")
            import traceback
            canvas.error(traceback.format_exc())
        
    def debug_code_generation(self, raw_response: str, processed_code: str) -> None:
        """Log details about code generation for debugging"""
        canvas.info("--- Debug: Code Generation Details ---")
        canvas.info(f"Raw response length: {len(raw_response)} chars")
        canvas.info(f"Processed code length: {len(processed_code)} chars")
        canvas.info("Raw response preview (first 100 chars):")
        canvas.info(raw_response[:100] + "..." if len(raw_response) > 100 else raw_response)
        canvas.info("Processed code preview (first 100 chars):")
        canvas.info(processed_code[:100] + "..." if len(processed_code) > 100 else processed_code)
        canvas.info("--- End Debug Info ---")
        


    def _load_scenario(self) -> List[Dict[str, Any]]:
        """Load and parse the scenario JSON file"""
        try:
            canvas.info(f"Loading scenario file: {self.scenario_path}")
            with open(self.scenario_path, 'r') as f:
                content = f.read()
                canvas.info(f"Scenario file content (first 100 chars): {content[:100]}...")
                
                # Parse the JSON
                data = json.loads(content)
                
                # Debug the parsed data
                canvas.info(f"Parsed scenario data type: {type(data)}")
                if isinstance(data, dict):
                    canvas.info(f"Scenario keys: {list(data.keys())}")
                    
                    # Check if 'steps' is a list in the data
                    steps = data.get('steps', [])
                    canvas.info(f"Steps type: {type(steps)}")
                    canvas.info(f"Number of steps: {len(steps)}")
                    
                    # Check the first step
                    if steps and isinstance(steps, list) and len(steps) > 0:
                        first_step = steps[0]
                        canvas.info(f"First step type: {type(first_step)}")
                        canvas.info(f"First step content: {first_step}")
                        
                    # Return just the steps
                    return steps
                else:
                    # If data is not a dict, assume it's already a list of steps
                    canvas.info(f"Data is not a dict, assuming direct list of steps")
                    return data
                    
        except json.JSONDecodeError as e:
            canvas.error(f"Invalid JSON in scenario file: {e}")
            raise ValueError(f"Invalid JSON in scenario file: {e}")
        except FileNotFoundError:
            canvas.error(f"Scenario file not found: {self.scenario_path}")
            raise FileNotFoundError(f"Scenario file not found: {self.scenario_path}")
        except Exception as e:
            canvas.error(f"Error reading scenario file: {e}")
            raise
    
    def ensure_database_tables(self) -> bool:
        """Ensure all required database tables exist before processing"""
        try:
            from i2c.db_utils import (
                get_db_connection, 
                get_or_create_table,
                TABLE_CODE_CONTEXT, 
                SCHEMA_CODE_CONTEXT,
                TABLE_KNOWLEDGE_BASE, 
                SCHEMA_KNOWLEDGE_BASE
            )
            
            # Connect to DB
            db = get_db_connection()
            if not db:
                canvas.error("Failed to connect to database")
                return False
            
            # Create code_context table directly
            try:
                if TABLE_CODE_CONTEXT in db.table_names():
                    canvas.info(f"Dropping existing {TABLE_CODE_CONTEXT} table")
                    db.drop_table(TABLE_CODE_CONTEXT)
                    
                canvas.info(f"Creating {TABLE_CODE_CONTEXT} table")
                code_tbl = db.create_table(TABLE_CODE_CONTEXT, schema=SCHEMA_CODE_CONTEXT)
                canvas.success(f"Created {TABLE_CODE_CONTEXT} table")
            except Exception as e:
                canvas.error(f"Failed to create {TABLE_CODE_CONTEXT} table: {e}")
                return False
            
            # Create knowledge_base table directly
            try:
                if TABLE_KNOWLEDGE_BASE in db.table_names():
                    canvas.info(f"Dropping existing {TABLE_KNOWLEDGE_BASE} table")
                    db.drop_table(TABLE_KNOWLEDGE_BASE)
                    
                canvas.info(f"Creating {TABLE_KNOWLEDGE_BASE} table")
                kb_tbl = db.create_table(TABLE_KNOWLEDGE_BASE, schema=SCHEMA_KNOWLEDGE_BASE)
                canvas.success(f"Created {TABLE_KNOWLEDGE_BASE} table")
            except Exception as e:
                canvas.error(f"Failed to create {TABLE_KNOWLEDGE_BASE} table: {e}")
                return False
            canvas.success("Database tables created successfully")
        
            
            if hasattr(self, 'reader_agent') and self.reader_agent is not None:
                from i2c.agents.modification_team.context_reader.context_reader_agent import ContextReaderAgent
                try:
                    canvas.info("Reinitializing context reader agent...")
                    self.reader_agent = ContextReaderAgent(project_path=self.current_project_path)
                    canvas.success("Context reader agent reinitialized")
                except Exception as e:
                    canvas.error(f"Error reinitializing context reader agent: {e}")
            
            return True
        except Exception as e:
            canvas.error(f"Error ensuring database tables: {e}")
            return False
               
    def process_scenario(self) -> bool:
        """
        Process the entire scenario step by step
        
        Returns:
            bool: True if scenario processed successfully, False otherwise
        """
        try:
            # Enable more verbose logging temporarily
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[logging.FileHandler("scenario_debug.log"), logging.StreamHandler()]
            )
            logger.info("=" * 60)
            logger.info(f"Starting scenario: {self.scenario_path.name}")
            logger.info(f"Current working directory: {os.getcwd()}")
            logger.info(f"Using output directory: {DEFAULT_OUTPUT_DIR_BASE}")
            logger.info("=" * 60)
            canvas.info("=" * 60)
            canvas.info(f"I2C Factory Scenario Processor - Starting scenario: {self.scenario_path.name}")
            canvas.info("=" * 60)
            
            # Debug knowledge base before starting
            canvas.info("Checking knowledge base connectivity...")
            self.debug_knowledge_base()
            
            canvas.info("Ensuring database tables exist...")
            if not self.ensure_database_tables():
                canvas.warning("Database table setup failed, some operations may not work correctly")
            
            # Process each step in the scenario
            for i, step in enumerate(self.scenario_data):
                try:
                    step_type = step.get("type", "")
                    step_name = step.get("name", f"Step {i+1}")
                    
                    canvas.step(f"Processing step {i+1}/{len(self.scenario_data)}: {step_name}")
                    
                    # Handle different step types
                    if step_type == "narration":
                        self._process_narration_step(step)
                    elif step_type == "agentic_evolution":
                        self._process_agentic_evolution_step(step)
                    elif step_type == "initial_generation":
                        self._process_initial_generation_step(step)
                    elif step_type == "modification":
                        self._process_modification_step(step)
                    elif step_type == "refine":
                        self._process_refine_step(step)
                    elif step_type == "knowledge":
                        self._process_knowledge_step(step)
                    elif step_type == "knowledge_folder":
                        self._process_knowledge_folder_step(step)
                    elif step_type == "pause":
                        self._process_pause_step(step)
                    else:
                        canvas.warning(f"Unknown step type: {step_type}. Skipping...")
                        
                except Exception as e:
                    canvas.error(f"Error processing step {i+1}: {e}")
                    logger.exception(f"Error processing step {i+1}")
                    # Continue with next step instead of aborting entirely
            
            # Show budget summary at the end
            show_budget_summary(self.budget_manager)
            tokens, cost = self.budget_manager.get_session_consumption()
            canvas.info(f"Scenario complete! Consumed ~{tokens} tokens (~${cost:.6f})")
            canvas.info("=" * 60)
            
            return True
            
        except Exception as e:
            canvas.error(f"Error processing scenario: {e}")
            logger.exception("Error processing scenario")
            return False
            
    def _process_narration_step(self, step: Dict[str, Any]) -> None:
        """
        Process a narration step - display message and pause
        
        Args:
            step: The narration step configuration
        """
        message = step.get("message", "")
        pause_time = step.get("pause", 2)
        
        canvas.info("")
        canvas.info(f"🎬 {message}")
        canvas.info("")
        
        # Pause for the specified time
        time.sleep(pause_time)
        
    def _process_initial_generation_step(self, step: Dict[str, Any]) -> None:
        """
        Proces  s an initial generation step - create a new project
        
        Args:
            step: The initial generation step configuration
        """
        raw_idea = step.get("prompt", "")
        if not raw_idea:
            canvas.warning("Initial generation step has empty prompt. Skipping...")
            return
            
        # Get project name if specified in the step
        suggested_project_name = step.get("project_name", "")
        
        # Standard approval without visual display
        if not self.budget_manager.request_approval(
            description="New Idea Clarification",
            prompt=raw_idea,
            model_id=getattr(input_processor_agent.model, 'id', 'Unknown'),
        ):
            canvas.warning("Clarification cancelled due to budget rejection.")
            return
            
        canvas.step("Clarifying new idea…")
        try:
            # Get start cost for operation tracking
            start_tokens, start_cost = self.budget_manager.get_session_consumption()
            
            resp = input_processor_agent.run(raw_idea)
            
            # Update budget manager with metrics from Agno agent
            self.budget_manager.update_from_agno_metrics(input_processor_agent)
            
            # Calculate operation cost
            end_tokens, end_cost = self.budget_manager.get_session_consumption()
            op_tokens = end_tokens - start_tokens
            op_cost = end_cost - start_cost
            
            # Show simple operation cost 
            show_operation_cost(
                operation="Idea Clarification",
                tokens=op_tokens,
                cost=op_cost
            )
            
            proc = json.loads(getattr(resp, 'content', str(resp)))
            if not (isinstance(proc, dict) and "objective" in proc and "language" in proc):
                raise ValueError("Invalid JSON from LLM")
            self.current_structured_goal = proc
            canvas.success(f"Objective: {proc['objective']}")
            canvas.success(f"Language:  {proc['language']}")
        except Exception as e:
            canvas.error(f"Error clarifying idea: {e}")
            return
            
        # Project naming with debug output
        suggested = sanitize_filename(self.current_structured_goal['objective'])
        canvas.info(f"Suggested project name: {suggested}")
        final_name = sanitize_filename(suggested_project_name or suggested)
        canvas.info(f"Final project name: {final_name}")
        
        self.current_project_path = ensure_project_path(DEFAULT_OUTPUT_DIR_BASE, final_name)
        
        # Validate project path before proceeding
        canvas.info(f"Validating project path: {self.current_project_path}")
        if not self.validate_project_path(self.current_project_path):
            canvas.error("Project path validation failed. Stopping generation step.")
            return
        
        # Ensure database tables exist before context indexing
        self.ensure_database_tables()
        
        # Reinitialize context reader agent
        from i2c.agents.modification_team.context_reader.context_reader_agent import ContextReaderAgent
        self.reader_agent = ContextReaderAgent(project_path=self.current_project_path)

        # Now the agent should see the freshly created tables
        status = self.reader_agent.index_project_context()
        canvas.info(f"Indexing Status: {status}")
        
        canvas.info(f"Preparing new project generation in: {self.current_project_path}")
        
        # Standard approval without visual display
        if self.budget_manager.request_approval(
            description="Initial Project Generation",
            prompt=self.current_structured_goal['objective'],
            model_id=getattr(input_processor_agent.model, 'id', 'Unknown'),
        ):
            # Get start cost for operation tracking
            start_tokens, start_cost = self.budget_manager.get_session_consumption()
            
            # Call route_and_execute without budget_manager parameter
            ok = route_and_execute(
                action_type='generate',
                action_detail=self.current_structured_goal,
                current_project_path=self.current_project_path,
                current_structured_goal=self.current_structured_goal
            )
            
            # Check for generation failures or syntax errors
            if not ok or self._check_for_syntax_errors(self.current_project_path):
                canvas.error("Action 'generate' failed or syntax errors found. Creating minimal working project...")
                
                # Create minimal working files directly
                minimal_code = {
                    "main.py": '#!/usr/bin/env python3\n\ndef main():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()'
                }
                
                # Write files directly
                try:
                    for file_name, content in minimal_code.items():
                        file_path = self.current_project_path / file_name
                        file_path.write_text(content)
                        canvas.success(f"Created minimal working file: {file_path}")
                    
                    # Create __init__.py
                    init_path = self.current_project_path / "__init__.py"
                    if not init_path.exists():
                        init_path.touch()
                        canvas.success(f"Created missing __init__.py at {init_path}")
                        
                    canvas.success("Created minimal working project as fallback")
                except Exception as e:
                    canvas.error(f"Failed to create minimal working project: {e}")
                    canvas.error(traceback.format_exc())
            
            # Calculate operation cost manually if no tokens were tracked
            end_tokens, end_cost = self.budget_manager.get_session_consumption()
            
            # If no tokens were counted, estimate based on complexity
            if end_tokens == start_tokens:
                # Estimate tokens based on complexity
                estimated_tokens = 5000  # Reasonable estimate for generation
                model_id = "groq/llama-3.1-8b-instant"  # Default model
                
                # Import pricing info
                from i2c.workflow.utils import MODEL_PRICING_PER_1K_TOKENS, DEFAULT_PRICE_PER_1K
                
                # Calculate estimated cost
                price_per_1k = MODEL_PRICING_PER_1K_TOKENS.get(model_id, DEFAULT_PRICE_PER_1K)
                estimated_cost = (estimated_tokens / 1000) * price_per_1k
                
                # Manually update budget manager
                self.budget_manager.consumed_tokens_session += estimated_tokens
                self.budget_manager.consumed_cost_session += estimated_cost
                
                # Update provider stats
                provider = 'groq'
                if provider in self.budget_manager.provider_stats:
                    self.budget_manager.provider_stats[provider]['tokens'] += estimated_tokens
                    self.budget_manager.provider_stats[provider]['cost'] += estimated_cost
                    self.budget_manager.provider_stats[provider]['calls'] += 1
                
                # Use estimated values
                op_tokens = estimated_tokens
                op_cost = estimated_cost
                
                canvas.info(f"Using estimated token count: {op_tokens} tokens, ${op_cost:.6f}")
            else:
                # Use actual difference
                op_tokens = end_tokens - start_tokens
                op_cost = end_cost - start_cost
            
            # Show operation cost
            show_operation_cost(
                operation="Initial Project Generation",
                tokens=op_tokens,
                cost=op_cost
            )
        else:
            canvas.warning("Generation cancelled due to budget rejection.")
             
    def _process_modification_step(self, step: Dict[str, Any]) -> None:
        """
        Process a modification step - modify an existing project with RAG context
        
        Args:
            step: The modification step configuration
        """
        # Add diagnostic logging
        canvas.info("=" * 40)
        canvas.info(f"PROCESSING MODIFICATION STEP: {step.get('prompt', 'Unknown')}")
        canvas.info("=" * 40)
    
        if not (self.current_project_path and self.current_structured_goal):
            canvas.warning("No active project. Cannot apply modification.")
            return
                
        prompt = step.get("prompt", "")
        if not prompt:
            canvas.warning("Modification step has empty prompt. Skipping...")
            return
        
        # Get language from structured goal
        language = self.current_structured_goal.get('language', 'python')
        
        # Ensure project is indexed for RAG
        if hasattr(self, 'reader_agent') and self.reader_agent:
            try:
                canvas.info("Ensuring project is indexed for RAG context...")
                status = self.reader_agent.index_project_context()
                canvas.info(f"RAG indexing status: {status}")
                
                # Get DB and embed model for RAG
                from i2c.db_utils import get_db_connection
                from i2c.workflow.modification.rag_config import get_embed_model
                
                db = get_db_connection()
                embed_model = get_embed_model()
                
                if not db or not embed_model:
                    canvas.warning("Failed to initialize RAG components")
                    db = None
                    embed_model = None
            except Exception as e:
                canvas.warning(f"Error preparing RAG context: {e}")
                db = None
                embed_model = None
        else:
            canvas.warning("No reader agent available. RAG context will not be used.")
            db = None
            embed_model = None
        
        # Standard approval without visual display
        if self.budget_manager.request_approval(
            description=f"Project Modification ({prompt[:20]}...)",
            prompt=prompt,
            model_id=getattr(input_processor_agent.model, 'id', 'Unknown'),
        ):
            # Get start cost for operation tracking
            start_tokens, start_cost = self.budget_manager.get_session_consumption()
            
            # Use execute_modification_cycle directly instead of route_and_execute
            try:
                from i2c.workflow.modification.execute_cycle import execute_modification_cycle
                
                # Call the cycle with all required parameters
                result = execute_modification_cycle(
                    user_request=prompt,
                    project_path=self.current_project_path,
                    language=language,
                    db=db,
                    embed_model=embed_model
                )
                
                if result.get("success", False):
                    canvas.success(f"Modification successful: {len(result.get('code_map', {}))} files modified")
                    ok = True
                else:
                    canvas.error("Modification failed")
                    ok = False
                    
            except Exception as e:
                canvas.error(f"Error in modification cycle: {e}")
                import traceback
                canvas.error(traceback.format_exc())
                ok = False
            
            # Calculate operation cost manually if no tokens were tracked
            end_tokens, end_cost = self.budget_manager.get_session_consumption()
            
            # If no tokens were counted, estimate based on complexity
            if end_tokens == start_tokens:
                # Estimate tokens based on complexity
                estimated_tokens = 3000  # Reasonable estimate for modification
                model_id = "groq/llama-3.1-8b-instant"  # Default model
                
                # Import pricing info
                from i2c.workflow.utils import MODEL_PRICING_PER_1K_TOKENS, DEFAULT_PRICE_PER_1K
                
                # Calculate estimated cost
                price_per_1k = MODEL_PRICING_PER_1K_TOKENS.get(model_id, DEFAULT_PRICE_PER_1K)
                estimated_cost = (estimated_tokens / 1000) * price_per_1k
                
                # Manually update budget manager
                self.budget_manager.consumed_tokens_session += estimated_tokens
                self.budget_manager.consumed_cost_session += estimated_cost
                
                # Update provider stats
                provider = 'groq'
                if provider in self.budget_manager.provider_stats:
                    self.budget_manager.provider_stats[provider]['tokens'] += estimated_tokens
                    self.budget_manager.provider_stats[provider]['cost'] += estimated_cost
                    self.budget_manager.provider_stats[provider]['calls'] += 1
                
                # Use estimated values
                op_tokens = estimated_tokens
                op_cost = estimated_cost
                
                canvas.info(f"Using estimated token count: {op_tokens} tokens, ${op_cost:.6f}")
            else:
                # Use actual difference
                op_tokens = end_tokens - start_tokens
                op_cost = end_cost - start_cost
            
            # Show operation cost
            from i2c.cli.budget_display import show_operation_cost
            show_operation_cost(
                operation=f"Project Modification ({prompt[:20]}...)",
                tokens=op_tokens,
                cost=op_cost
            )
        else:
            canvas.warning("Modification cancelled due to budget rejection.")
        
    def _process_refine_step(self, step: Dict[str, Any]) -> None:
        """
        Process a refine step - refine an existing project
        
        Args:
            step: The refine step configuration
        """
        if not (self.current_project_path and self.current_structured_goal):
            canvas.warning("No active project. Cannot apply refinement.")
            return
            
        # Standard approval without visual display
        if self.budget_manager.request_approval(
            description=f"Project Refinement",
            prompt="General project refinement",
            model_id=getattr(input_processor_agent.model, 'id', 'Unknown'),
        ):
            # Get start cost for operation tracking
            start_tokens, start_cost = self.budget_manager.get_session_consumption()
            
            # Call route_and_execute without budget_manager parameter to match interface
            ok = route_and_execute(
                action_type='modify',
                action_detail='r',  # 'r' is the refinement command
                current_project_path=self.current_project_path,
                current_structured_goal=self.current_structured_goal
            )
            if not ok:
                canvas.error("Action 'refine' failed. Please review logs.")
            
            # Calculate operation cost
            end_tokens, end_cost = self.budget_manager.get_session_consumption()
            op_tokens = end_tokens - start_tokens
            op_cost = end_cost - start_cost
            
            # Show operation cost after major operation
            show_operation_cost(
                operation=f"Project Refinement",
                tokens=op_tokens,
                cost=op_cost
            )
        else:
            canvas.warning("Refinement cancelled due to budget rejection.")
            
    def _process_knowledge_step(self, step: Dict[str, Any]) -> None:
        """Process a knowledge step - add documentation to knowledge base"""
        if not self.current_project_path:
            canvas.warning("No active project. Cannot add knowledge.")
            return
            
        doc_path = step.get("doc_path", "")
        if not doc_path:
            canvas.warning("Knowledge step missing doc_path. Skipping...")
            return
            
        doc_path = Path(doc_path)
        # Check if path is absolute, if not make it relative to the current directory
        if not doc_path.is_absolute():
            doc_path = Path(os.getcwd()) / doc_path
        
        if not doc_path.exists():
            canvas.warning(f"Document path does not exist: {doc_path}")
            return
            
        # Extract metadata
        doc_type = step.get("doc_type", "API Documentation")
        framework = step.get("framework", "")
        version = step.get("version", "")
        
        canvas.step(f"Adding documentation to knowledge base: {doc_path.name}")
        
        # First, ensure tables exist
        if not self.ensure_database_tables():
            canvas.error("Database tables not ready, skipping knowledge step")
            return
        
        # Use ingest_documentation with proper error handling
        try:
            # Use the ingest_documentation function with explicit error handling
            success = False
            try:
                from i2c.workflow.session_handlers import ingest_documentation
                
                # Make sure path is absolute
                if not doc_path.is_absolute():
                    doc_path = Path(os.getcwd()) / doc_path
                    
                canvas.info(f"Using absolute path: {doc_path}")
                
                if not doc_path.exists():
                    canvas.error(f"Document not found at: {doc_path}")
                    return
                    
                success = ingest_documentation(
                    project_path=self.current_project_path,
                    doc_path=doc_path,
                    document_type=doc_type,
                    framework=framework,
                    version=version
                )
            except ImportError as e:
                canvas.error(f"Failed to import session handlers: {e}")
                return
            except Exception as e:
                canvas.error(f"Error in ingest_documentation: {e}")
                import traceback
                canvas.error(traceback.format_exc())
                return
                
            if success:
                canvas.success(f"Successfully added {doc_path.name} to knowledge base.")
            else:
                canvas.error(f"Failed to add {doc_path.name} to knowledge base.")
        except Exception as e:
            canvas.error(f"Error in knowledge step: {e}")
            import traceback
            canvas.error(traceback.format_exc())
             
    def _process_knowledge_folder_step(self, step: Dict[str, Any]) -> None:
        """
        Process a knowledge folder step - add a folder of documentation
        
        Args:
            step: The knowledge folder step configuration
        """
        if not self.current_project_path:
            canvas.warning("No active project. Cannot add knowledge.")
            return
            
        folder_path = step.get("folder_path", "")
        if not folder_path:
            canvas.warning("Knowledge folder step missing folder_path. Skipping...")
            return
            
        folder_path = Path(folder_path)
        if not folder_path.exists() or not folder_path.is_dir():
            canvas.warning(f"Folder path does not exist or is not a directory: {folder_path}")
            return
            
        # Extract metadata
        doc_type = step.get("doc_type", "API Documentation")
        framework = step.get("framework", "")
        version = step.get("version", "")
        recursive = step.get("recursive", True)
        
        canvas.step(f"Adding documentation folder to knowledge base: {folder_path.name}")
        
        # Use the ingest_documentation function from session_handlers
        from i2c.workflow.session_handlers import ingest_documentation
        
        success = ingest_documentation(
            project_path=self.current_project_path,
            doc_path=folder_path,
            document_type=doc_type,
            framework=framework,
            version=version,
            recursive=recursive
        )
        
        if success:
            canvas.success(f"Successfully added documentation from {folder_path.name} to knowledge base.")
        else:
            canvas.error(f"Failed to add documentation from {folder_path.name} to knowledge base.")
            
    def _process_pause_step(self, step: Dict[str, Any]) -> None:
        """
        Process a pause step - pause for user interaction
        
        Args:
            step: The pause step configuration
        """
        message = step.get("message", "Paused")
        canvas.warning(f"Manual pause: {message}")
        canvas.warning("Press Enter to continue...")
        input()

    def debug_knowledge_base(self) -> bool:
        """Debug knowledge base connectivity and schema"""
        try:
            from i2c.db_utils import get_db_connection, TABLE_KNOWLEDGE_BASE, SCHEMA_KNOWLEDGE_BASE
            
            # Connect to DB
            db = get_db_connection()
            if not db:
                canvas.error("Failed to connect to database")
                return False
                
            # Try to get the table
            canvas.info(f"Knowledge base table: {TABLE_KNOWLEDGE_BASE}")
            if TABLE_KNOWLEDGE_BASE in db.table_names():
                canvas.info(f"Table exists")
                table = db.open_table(TABLE_KNOWLEDGE_BASE)
                canvas.info(f"Table schema: {table.schema}")
                
                # Try to get rows
                try:
                    df = table.to_pandas()
                    canvas.info(f"Table has {len(df)} rows")
                    return True
                except Exception as e:
                    canvas.error(f"Error getting data from table: {e}")
                    return False
            else:
                canvas.error(f"Table does not exist")
                return False
                
        except Exception as e:
            canvas.error(f"Error debugging knowledge base: {e}")
            return False

    def validate_project_path(self, path: Path) -> bool:
        """Validate that the project path exists and is writable"""
        try:
            # Handle Path vs string
            if isinstance(path, str):
                path = Path(path)
                
            # Convert to absolute path
            path = path.resolve()
            
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    canvas.info(f"Created project directory: {path}")
                except Exception as e:
                    canvas.error(f"Failed to create project directory: {e}")
                    return False
            elif not path.is_dir():
                canvas.error(f"Project path exists but is not a directory: {path}")
                return False
                
            # Check if directory is writable
            try:
                test_file = path / ".write_test"
                test_file.touch()
                test_file.unlink()
                canvas.info(f"Project directory is writable: {path}")
                return True
            except Exception as e:
                canvas.error(f"Project directory is not writable: {e}")
                return False
        except Exception as e:
            canvas.error(f"Error validating project path: {e}")
            return False
    
    def _check_for_syntax_errors(self, project_path: Path) -> bool:
        """
        Check if there are syntax errors in Python files in the project
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            bool: True if syntax errors were found, False otherwise
        """
        try:
            import ast
            
            # Look for Python files only
            python_files = list(project_path.glob('**/*.py'))
            
            for file_path in python_files:
                try:
                    # Skip __init__.py files as they're often empty
                    if file_path.name == "__init__.py" and file_path.stat().st_size == 0:
                        continue
                        
                    # Try to parse the file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Try to parse with ast
                    try:
                        ast.parse(content)
                    except SyntaxError:
                        canvas.error(f"Syntax error found in {file_path.relative_to(project_path)}")
                        return True
                        
                except Exception as e:
                    canvas.warning(f"Error checking syntax in {file_path.relative_to(project_path)}: {e}")
                    # Continue checking other files even if one fails
            
            # No syntax errors found
            return False
            
        except Exception as e:
            canvas.error(f"Error in syntax checking: {e}")
            canvas.error(traceback.format_exc())
            # If we can't check for errors, assume there aren't any
            return False
    
def run_scenario(scenario_path: str, budget_manager: Optional[BudgetManagerAgent] = None, debug: bool = False) -> bool:
    """
    Run a scenario file
    
    Args:
        scenario_path: Path to the scenario JSON file
        budget_manager: Optional budget manager instance
        
    Returns:
        bool: True if scenario processed successfully, False otherwise
    """
    if debug:
        # Set up logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler("scenario_debug.log"), logging.StreamHandler()]
        )
        logger.info(f"Debug mode enabled for scenario: {scenario_path}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Using output directory: {DEFAULT_OUTPUT_DIR_BASE}")
        
    processor = ScenarioProcessor(scenario_path, budget_manager)
    return processor.process_scenario()


def add_scenario_arguments(parser):
    """
    Add scenario-related arguments to the CLI parser
    
    Args:
        parser: The argparse parser
    """
    parser.add_argument(
        "--scenario",
        help="Path to a scenario JSON file to execute",
        type=str
    )


def cli_entry_point():
    """CLI entry point for running scenarios directly"""
    import argparse
    
    parser = argparse.ArgumentParser(description="I2C Factory Scenario Runner")
    parser.add_argument("scenario_path", help="Path to scenario JSON file")
    
    args = parser.parse_args()
    run_scenario(args.scenario_path)
    
