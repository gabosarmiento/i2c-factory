# /src/i2c/workflow/scenario_processor.py
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
from typing import Dict, List, Optional, Any, Union, Tuple
import traceback
from i2c.utils.json_extraction import extract_json_with_fallback

# Import CLI canvas for user interaction
from i2c.cli.controller import canvas
from i2c.cli.budget_display import show_budget_status, show_operation_cost, show_budget_summary

# Import orchestrator for generating and modifying projects
from i2c.workflow.orchestrator import route_and_execute
from i2c.workflow.utils import sanitize_filename, ensure_project_path
from i2c.utils.json_extraction import extract_json

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

# Default output directory with absolute path (Fix #4)
DEFAULT_OUTPUT_DIR_BASE = Path(os.path.abspath("./output"))

class SessionKnowledgeBase:
    def __init__(self, db, embed_model, knowledge_space="default"):
        self.db = db
        self.embed_model = embed_model
        self.knowledge_space = knowledge_space
    
    def to_dict(self):
        """Convert to JSON-serializable dictionary"""
        return {
            "_type": "SessionKnowledgeBase",
            "knowledge_space": self.knowledge_space,
            # Don't serialize db and embed_model as they're not JSON serializable
            "status": "active"
        }
    
    @classmethod
    def from_dict(cls, data, db, embed_model):
        """Recreate from dictionary"""
        return cls(db, embed_model, data.get("knowledge_space", "default"))
    
    def retrieve_knowledge(self, query, limit=5):
        from i2c.db_utils import query_context, TABLE_KNOWLEDGE_BASE
        
        try:
            # Convert text query to vector using embed model
            query_vector = self.embed_model.get_embedding(query)
            
            # Query the knowledge base table
            df = query_context(
                db=self.db,
                table_name=TABLE_KNOWLEDGE_BASE,
                query_vector=query_vector,
                limit=limit
            )
            
            if df is None or df.empty:
                return []
            
            # Convert to list of dictionaries
            results = []
            for _, row in df.iterrows():
                results.append({
                    'source': row.get('source', ''),
                    'content': row.get('content', ''),
                    'category': row.get('category', ''),
                    'knowledge_space': row.get('knowledge_space', ''),
                    'framework': row.get('framework', '')
                })
            
            return results
        except Exception as e:
            canvas.error(f"Error retrieving knowledge: {e}")
            return []
        
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
        # Initialize session state as empty dict instead of None
        self.session_state: Dict[str, Any] = {}
        self.current_structured_goal: Optional[Dict] = None
        self.reader_agent: Optional[ContextReaderAgent] = None
    
    def _process_agentic_evolution_step(self, step: Dict[str, Any]) -> None:
        """
        Process an agentic evolution step - uses the new integrated agent orchestration system.
        
        Args:
            step: The agentic evolution step configuration
        """
        canvas.info("🔎 ENTERING _process_agentic_evolution_step")
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
        canvas.info(f"🔎 STEP TYPE: {step.get('type', 'unknown')}")
        canvas.info(f"🔎 OBJECTIVE KEYS: {list(objective.keys())}")
        
        # DEBUG: Check session state before agentic evolution
        canvas.info(f"🔍 DEBUG: Agentic evolution starting with {len(self.session_state or {})} session keys")
        if self.session_state:
            important_keys = ['knowledge_base', 'backend_api_routes', 'architectural_context', 'retrieved_context']
            for key in important_keys:
                if key in self.session_state:
                    canvas.success(f"✅ DEBUG: Agentic evolution has {key}")
                else:
                    canvas.warning(f"⚠️ DEBUG: Agentic evolution missing {key}")

        if not objective or not objective.get("task"):
            canvas.warning("No task specified in objective. Skipping agentic evolution.")
            return
        
        # Add quality constraints to the objective
        if "constraints" not in objective:
            objective["constraints"] = []
            
        # Add specific constraints for code quality and consistency
        quality_constraints = [
            "Use a consistent data model across all files",
            "Avoid creating duplicate implementations of the same functionality",
            "Ensure tests do not have duplicate unittest.main() calls",
            "If creating a CLI app, use a single approach for the interface",
            "Use consistent file naming for data storage (e.g., todos.json)"
        ]
        
        # Add constraints if they don't already exist
        for constraint in quality_constraints:
            if constraint not in objective["constraints"]:
                objective["constraints"].append(constraint)
        
        canvas.info(f"🧠 Running agent-orchestrated evolution for: {objective.get('task', 'Unknown task')}")
        canvas.info(f"📏 Quality constraints added: {len(quality_constraints)}")

        def clean_session_state(obj):
            """Serialize SessionKnowledgeBase objects recursively"""
            if isinstance(obj, SessionKnowledgeBase):
                return obj.to_dict()
            elif isinstance(obj, dict):
                cleaned = {}
                for k, v in obj.items():
                    if isinstance(v, SessionKnowledgeBase):
                        # Serialize SessionKnowledgeBase to dict
                        cleaned[k] = v.to_dict()
                    elif 'SessionKnowledgeBase' in str(type(v)):
                        # Fallback for edge cases
                        cleaned[k] = {"_type": "SessionKnowledgeBase", "status": "serialized"}
                    elif isinstance(v, dict):
                        cleaned[k] = clean_session_state(v)
                    elif isinstance(v, list):
                        cleaned[k] = [clean_session_state(item) for item in v]
                    else:
                        cleaned[k] = v
                return cleaned
            return obj

        try:
            import json
            # Clean the objective before JSON serialization
            clean_objective = clean_session_state(objective)
            canvas.info(f"Full objective being sent to orchestrator: {json.dumps(clean_objective, indent=2)[:500]}...")
        except Exception as e:
            canvas.info(f"Could not log full objective: {e}")

        try:
            # Import the agentic orchestrator
            from i2c.workflow.agentic_orchestrator import execute_agentic_evolution_sync
            
            # Get start cost for operation tracking
            start_tokens, start_cost = self.budget_manager.get_session_consumption()
            
            # Ensure session state is properly prepared
            if self.session_state:
                self.session_state["project_path"] = str(self.current_project_path)
                self.session_state["current_structured_goal"] = self.current_structured_goal
            
            canvas.info(f"🔍 DEBUG: Calling agentic evolution with session state: {len(self.session_state or {})} keys")

            # Execute the agentic evolution
            result = execute_agentic_evolution_sync(
                objective,
                self.current_project_path,
                self.session_state
            )
            
            # NEW: Better session state handling
            if isinstance(result, dict) and "session_state" in result:
                canvas.info("🔄 DEBUG: Updating session state from agentic evolution result")
                
                # Merge session state (preserve existing, add new)
                updated_session_state = result["session_state"]
                if self.session_state and updated_session_state:
                    self.session_state.update(updated_session_state)
                elif updated_session_state:
                    self.session_state = updated_session_state
                    
                canvas.info(f"🔄 DEBUG: Session state now has {len(self.session_state)} keys")
            else:
                canvas.warning("⚠️ DEBUG: No session state returned from agentic evolution")
               
            # Extract the actual agent output
            output = result.get("result", {})
            
            # Display the result
            if output.get("decision") == "approve":
                canvas.success(f"✅ Evolution approved: {output.get('reason', 'No reason provided')}")
                
                # Show modifications
                modifications = output.get("modifications", {})
                if modifications:
                    canvas.info("📝 Modifications:")
                    for file_path, summary in modifications.items():
                        canvas.info(f"  - {file_path}: {summary}")
            else:
                canvas.error(f"❌ Evolution rejected: {output.get('reason', 'No reason provided')}")
                
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
                    
                    self.project_name = data.get("project_name")
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
        """Ensure all required database tables exist without destroying data"""
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
            
            # Check if knowledge_base has data and preserve it
            preserve_knowledge = False
            try:
                if TABLE_KNOWLEDGE_BASE in db.table_names():
                    kb_table = db.open_table(TABLE_KNOWLEDGE_BASE)
                    row_count = len(kb_table.to_pandas())
                    if row_count > 0:
                        canvas.success(f"✅ Preserving existing knowledge_base with {row_count} rows")
                        preserve_knowledge = True
            except Exception as e:
                canvas.warning(f"Error checking knowledge_base: {e}")
            
            # Handle code_context table (always recreate)
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
            
            # Handle knowledge_base table (preserve if has data)
            try:
                if preserve_knowledge:
                    canvas.info(f"Keeping existing {TABLE_KNOWLEDGE_BASE} table with data")
                else:
                    if TABLE_KNOWLEDGE_BASE in db.table_names():
                        canvas.info(f"Dropping existing {TABLE_KNOWLEDGE_BASE} table")
                        db.drop_table(TABLE_KNOWLEDGE_BASE)
                    canvas.info(f"Creating {TABLE_KNOWLEDGE_BASE} table")
                    kb_tbl = db.create_table(TABLE_KNOWLEDGE_BASE, schema=SCHEMA_KNOWLEDGE_BASE)
                    canvas.success(f"Created {TABLE_KNOWLEDGE_BASE} table")
            except Exception as e:
                canvas.error(f"Failed to handle {TABLE_KNOWLEDGE_BASE} table: {e}")
                return False
            
            canvas.success("Database tables handled successfully")
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
            
            # Initialize session state if not already done
            if not hasattr(self, 'session_state') or self.session_state is None:
                self.session_state = {}
                canvas.info("🔍 DEBUG: Initialized empty session state for scenario")
            
            # Debug knowledge base before starting
            canvas.info("Checking knowledge base connectivity...")
            self.debug_knowledge_base()
            
            canvas.info("Database tables already exist - skipping recreation to preserve knowledge")
            
            # Process each step in the scenario
            for i, step in enumerate(self.scenario_data):
                
                # DEBUG: Show session state progression
                canvas.info(f"🔍 DEBUG: Step {i+1}/{len(self.scenario_data)} - Session state has {len(self.session_state)} keys")

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
        """Process an initial generation step with architectural intelligence enforcement"""
        raw_idea = step.get("prompt", "")
        if not raw_idea:
            canvas.warning("Initial generation step has empty prompt. Skipping...")
            return
            
        # Get project name if specified in the step
        suggested_project_name = step.get("project_name", "")
        
        canvas.info(f"🔍 DEBUG: Initial generation starting with {len(self.session_state or {})} session keys")
        if self.session_state and 'knowledge_base' in self.session_state:
            canvas.success("✅ DEBUG: Knowledge base available for initial generation")
        
        # Standard approval without visual display
        if not self.budget_manager.request_approval(
            description="New Idea Clarification",
            prompt=raw_idea,
            model_id='Dynamic' if input_processor_agent is None else getattr(input_processor_agent.model, 'id', 'Unknown'),
        ):
            canvas.warning("Clarification cancelled due to budget rejection.")
            return
            
        canvas.step("Clarifying new idea with architectural intelligence…")
        try:
            # Get start cost for operation tracking
            start_tokens, start_cost = self.budget_manager.get_session_consumption()
            
            # ENHANCED: Add architectural context to the input processing
            enhanced_prompt = self._enhance_prompt_with_architectural_guidance(raw_idea)
            
            from i2c.agents.core_agents import get_rag_enabled_agent
            temp_agent = get_rag_enabled_agent("input_processor", session_state=self.session_state)
            resp = temp_agent.run(enhanced_prompt)
            # Update budget manager with metrics from Agno agent
            self.budget_manager.update_from_agno_metrics(temp_agent)
            
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
            
            # Get the response content and extract JSON from markdown if needed
            response_content = getattr(resp, 'content', str(resp))

            # Extract JSON from markdown code fences if present
            import re
            json_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
            json_match = re.search(json_pattern, response_content, re.DOTALL)

            if json_match:
                json_str = json_match.group(1).strip()
                canvas.info("Extracted JSON from markdown code fences")
            else:
                json_str = response_content.strip()
                canvas.info("Using response content directly")

            canvas.info(f"JSON to parse: {json_str[:100]}...")

            # Parse the extracted JSON
            proc = extract_json_with_fallback(
                json_str,
                fallback=None  # Don't use hardcoded fallback here
            )
            if not isinstance(proc, dict):
                raise ValueError("Invalid JSON: not a dictionary")

            # Recover values safely if keys are missing
            if "objective" not in proc or not proc["objective"].strip():
                canvas.warning("⚠️ Missing 'objective' in LLM response. Using prompt fallback.")
                proc["objective"] = raw_idea[:80] + "..."

            if "language" not in proc or not proc["language"].strip():
                inferred_lang = "python" if "python" in raw_idea.lower() or "task" in raw_idea.lower() else "javascript"
                canvas.warning(f"⚠️ Missing 'language'. Inferring as '{inferred_lang}'.")
                proc["language"] = inferred_lang

            if "system_type" not in proc:
                proc["system_type"] = "auto"
                
            if "architecture_pattern" not in proc:
                proc["architecture_pattern"] = "auto"
            if not (isinstance(proc, dict) and "objective" in proc and "language" in proc):
                raise ValueError("Invalid JSON from LLM")
            
            # ENHANCED: Add architectural-specific constraints based on detected system type
            proc = self._enhance_objective_with_architectural_rules(proc, raw_idea)
            
            self.current_structured_goal = proc

            canvas.success(f"Objective: {proc['objective']}")
            canvas.success(f"Language:  {proc['language']}")
            canvas.success(f"System Type: {proc.get('system_type', 'auto-detected')}")
            canvas.success(f"Architecture: {proc.get('architecture_pattern', 'auto-detected')}")
                            
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
        
        # ENHANCED: Initialize architectural context early
        self._initialize_architectural_context()
                
        # Reinitialize context reader agent
        from i2c.agents.modification_team.context_reader.context_reader_agent import ContextReaderAgent
        self.reader_agent = ContextReaderAgent(project_path=self.current_project_path)
  
        # Use existing knowledge base if available, create if needed
        if not hasattr(self, 'session_state') or 'knowledge_base' not in self.session_state:
            canvas.info("🔧 Creating knowledge base for initial generation")
            try:
                from i2c.workflow.modification.rag_config import get_embed_model
                from i2c.db_utils import get_db_connection
                
                db = get_db_connection()
                embed_model = get_embed_model()
                
                if db and embed_model:
                    if not hasattr(self, 'session_state') or self.session_state is None:
                        self.session_state = {}
                    
                    self.session_state["knowledge_base"] = SessionKnowledgeBase(db, embed_model)
            except Exception:
                pass
        else:
            canvas.info("✅ Using existing knowledge base from previous steps")

        # Now the agent should see the freshly created tables
        status = self.reader_agent.index_project_context()
        canvas.info(f"Indexing Status: {status}")
        
        canvas.info(f"Preparing architecturally-aware project generation in: {self.current_project_path}")
        
        # Standard approval without visual display
        if self.budget_manager.request_approval(
            description="Initial Project Generation",
            prompt=self.current_structured_goal['objective'],
            model_id=getattr(input_processor_agent.model, 'id', 'Unknown') if input_processor_agent and input_processor_agent.model else 'Dynamic',
        ):
            # Get start cost for operation tracking
            start_tokens, start_cost = self.budget_manager.get_session_consumption()
            
            # ENHANCED: Pass session state with knowledge base to generation
            canvas.info(f"🔍 DEBUG: Passing session state to route_and_execute with {len(self.session_state or {})} keys")
            
            # Ensure current project path is in session state
            if self.session_state:
                self.session_state["project_path"] = str(self.current_project_path)
                self.session_state["current_structured_goal"] = self.current_structured_goal
                
            result = route_and_execute(
                action_type='generate',
                action_detail=self.current_structured_goal,
                current_project_path=self.current_project_path,
                current_structured_goal=self.current_structured_goal,
                architectural_context=(self.session_state or {}).get("architectural_context", {}),
                session_state=self.session_state  
            )
            
            # NEW: Extract updated session state from result if available
            if isinstance(result, dict) and "session_state" in result:
                canvas.info("🔄 DEBUG: Updating session state from generation result")
                self.session_state.update(result["session_state"])
            else:
                canvas.warning("⚠️ DEBUG: No session state returned from generation")

            # Handle detailed result
            if isinstance(result, dict):
                ok = result.get("success", False)
                if not ok:
                    error_msg = result.get("error", "No reason provided")
                    canvas.error(f"❌ Generation failed: {error_msg}")
                else:
                    canvas.success("✅ Generation completed successfully")
            else:
                # Backward compatibility - treat as boolean
                ok = bool(result)
                if not ok:
                    canvas.error("❌ Generation failed: Legacy workflow error")
            
            # Check for generation failures or syntax errors
            if isinstance(result, dict) and not result.get("success", False):
                error_msg = result.get("error", "No reason provided")
                canvas.error(f"❌ Evolution rejected: {error_msg}")
                
                # ENHANCED: Create architectural-appropriate fallback instead of generic
                self._create_architectural_fallback_project()
            elif not ok or self._check_for_syntax_errors(self.current_project_path):
                canvas.error("Action 'generate' failed or syntax errors found.")
                
                # ENHANCED: Create architectural-appropriate fallback instead of generic
                self._create_architectural_fallback_project()
            
            # Calculate operation cost
            end_tokens, end_cost = self.budget_manager.get_session_consumption()
            op_tokens = end_tokens - start_tokens if end_tokens > start_tokens else 5000
            op_cost = end_cost - start_cost if end_cost > start_cost else 0.01
            
            # Show operation cost
            show_operation_cost(
                operation="Initial Project Generation",
                tokens=op_tokens,
                cost=op_cost
            )
        else:
            canvas.warning("Generation cancelled due to budget rejection.")

    def _enhance_prompt_with_architectural_guidance(self, raw_idea: str) -> str:
        """Enhance the input prompt with architectural intelligence guidance"""
        
        enhanced_prompt = f"""
    {raw_idea}

    IMPORTANT: Analyze this idea and determine the appropriate system architecture.

    Pay special attention to these indicators:
    - If mentions: "web app", "frontend", "backend", "React", "API", "FastAPI", "Flask" → FULLSTACK WEB APP
    - If mentions: "CLI", "command line", "script", "terminal" → CLI TOOL  
    - If mentions: "API", "REST", "endpoints", "microservice" → API SERVICE
    - If mentions: "library", "package", "module" → LIBRARY

    For FULLSTACK WEB APPS, ensure you specify:
    - Frontend technology (React, Vue, etc.)
    - Backend technology (FastAPI, Flask, Express, etc.)
    - Proper file structure requirements
    - API communication patterns

    Your response should include:
    - "system_type": one of ["fullstack_web_app", "api_service", "cli_tool", "library", "desktop_app"]
    - "architecture_pattern": appropriate pattern for the system type
    - Constraints that enforce proper architectural boundaries
    """
        
        return enhanced_prompt

    def _enhance_objective_with_architectural_rules(self, proc: Dict[str, Any], raw_idea: str) -> Dict[str, Any]:
        """Enhance the processed objective with architectural rules based on system detection"""
        
        objective = proc.get("objective", "")
        
        # Detect system type from objective and raw idea
        combined_text = f"{objective} {raw_idea}".lower()
        
        # Fullstack web app detection
        if any(indicator in combined_text for indicator in [
            "web app", "frontend", "backend", "react", "api", "fastapi", 
            "flask", "express", "vue", "angular", "full stack", "fullstack"
        ]):
            proc["system_type"] = "fullstack_web_app"
            proc["architecture_pattern"] = "fullstack_web"
            
            # Add fullstack-specific constraints
            fullstack_constraints = [
                "Frontend must be in frontend/ directory with proper React structure",
                "Backend must be in backend/ directory with FastAPI endpoints", 
                "Main backend file must be backend/main.py with FastAPI app",
                "React components must be in frontend/src/components/",
                "Main React app must be frontend/src/App.jsx",
                "No mixing of frontend and backend code in same files",
                "Use proper file extensions: .jsx for React, .py for Python",
                "API endpoints must follow REST conventions",
                "Include proper CORS configuration for development"
            ]
            
            existing_constraints = proc.get("constraints", [])
            proc["constraints"] = existing_constraints + fullstack_constraints
            
            canvas.info("🏗️ Detected FULLSTACK WEB APP - added architectural constraints")
        
        # CLI tool detection
        elif any(indicator in combined_text for indicator in [
            "cli", "command line", "terminal", "script", "command"
        ]):
            proc["system_type"] = "cli_tool"
            proc["architecture_pattern"] = "cli_tool"
            
            cli_constraints = [
                "Main entry point must handle command line arguments",
                "Use argparse or click for argument parsing",
                "Include proper help text and usage examples",
                "Structure commands in organized modules"
            ]
            
            existing_constraints = proc.get("constraints", [])
            proc["constraints"] = existing_constraints + cli_constraints
            
            canvas.info("💻 Detected CLI TOOL - added CLI-specific constraints")
        
        # API service detection
        elif any(indicator in combined_text for indicator in [
            "api", "rest", "endpoints", "microservice", "service"
        ]):
            proc["system_type"] = "api_service"
            proc["architecture_pattern"] = "clean_architecture"
            
            api_constraints = [
                "Use FastAPI or Flask for API framework",
                "Organize endpoints in api/ directory",
                "Include proper request/response models",
                "Add input validation and error handling",
                "Include API documentation (OpenAPI/Swagger)"
            ]
            
            existing_constraints = proc.get("constraints", [])
            proc["constraints"] = existing_constraints + api_constraints
            
            canvas.info("🔌 Detected API SERVICE - added API-specific constraints")
        
        return proc

    def _initialize_architectural_context(self) -> None:
        """Initialize architectural context early in the process"""
        
        if not self.current_structured_goal:
            return
        
        # Create initial architectural context based on detected system type
        system_type = self.current_structured_goal.get("system_type", "web_app")
        architecture_pattern = self.current_structured_goal.get("architecture_pattern", "fullstack_web")
        
        if system_type == "fullstack_web_app":
            architectural_context = {
                "architecture_pattern": "fullstack_web",
                "system_type": "fullstack_web_app",
                "modules": {
                    "frontend": {
                        "boundary_type": "ui_layer",
                        "languages": ["javascript", "jsx"],
                        "responsibilities": ["React components", "user interface", "client-side logic"],
                        "folder_structure": {
                            "base_path": "frontend",
                            "subfolders": ["src", "src/components", "public"]
                        }
                    },
                    "backend": {
                        "boundary_type": "api_layer",
                        "languages": ["python"],
                        "responsibilities": ["REST API endpoints", "business logic", "data management"],
                        "folder_structure": {
                            "base_path": "backend",
                            "subfolders": ["api", "models", "services"]
                        }
                    }
                },
                "file_organization_rules": {
                    "react_components": "frontend/src/components",
                    "main_app": "frontend/src",
                    "api_endpoints": "backend/api",
                    "data_models": "backend/models",
                    "business_logic": "backend/services",
                    "main_backend": "backend"
                },
                "constraints": self.current_structured_goal.get("constraints", []),
                "integration_patterns": ["REST API", "JSON data exchange", "CORS configuration"]
            }
            
            # Store in session state for use by other components
            self.session_state = self.session_state or {}
            self.session_state["architectural_context"] = architectural_context
            self.session_state["system_type"] = system_type
            
            canvas.success("🏗️ Initialized fullstack web app architectural context")

    def _create_architectural_fallback_project(self) -> None:
        """Create architectural-appropriate fallback project instead of generic"""
        
        system_type = self.current_structured_goal.get("system_type", "web_app")
        
        if system_type == "fullstack_web_app":
            canvas.info("Creating fullstack web app fallback structure...")
            
            # Backend structure
            backend_main = self.current_project_path / "backend" / "main.py"
            backend_main.parent.mkdir(parents=True, exist_ok=True)
            backend_main.write_text("""from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title="Generated App")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"]
    )

    @app.get("/")
    def read_root():
        return {"message": "Hello World"}

    @app.get("/api/health")
    def health_check():
        return {"status": "healthy"}

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    """)
            
            # Frontend structure
            frontend_app = self.current_project_path / "frontend" / "src" / "App.jsx"
            frontend_app.parent.mkdir(parents=True, exist_ok=True)
            frontend_app.write_text("""import React from 'react';
    import './App.css';

    function App() {
    return (
        <div className="App">
        <h1>Generated Web App</h1>
        <p>Your fullstack application is ready!</p>
        </div>
    );
    }

    export default App;
    """)
            
            # Frontend CSS
            frontend_css = self.current_project_path / "frontend" / "src" / "App.css"
            frontend_css.write_text(""".App {
    text-align: center;
    padding: 20px;
    }

    h1 {
    color: #333;
    }
    """)
            
            canvas.success("✅ Created fullstack web app fallback structure")
        
        else:
            # Default fallback for other system types
            main_file = self.current_project_path / "main.py"
            main_file.write_text('''def main():
        print("Hello, World!")

    if __name__ == "__main__":
        main()
    ''')
            canvas.success("✅ Created basic fallback structure")
      
    def _process_modification_step(self, step: Dict[str, Any]) -> None:
        """
        Process a modification step - modify an existing project with RAG context
        
        Args:
            step: The modification step configuration
        """
        canvas.info("🔎 ENTERING _process_modification_step")
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
        
        # Add quality constraints to the step
        if "constraints" not in step:
            step["constraints"] = []
                
        quality_constraints = [
            "Use a consistent data model across all files",
            "Avoid creating duplicate implementations of the same functionality",
            "Ensure tests do not have duplicate unittest.main() calls",
            "If creating a CLI app, use a single approach for the interface",
            "Use consistent file naming for data storage (e.g., todos.json)"
        ]
        
        # Add constraints if they don't already exist
        for constraint in quality_constraints:
            if constraint not in step["constraints"]:
                step["constraints"].append(constraint)
                
        canvas.info(f"📏 Quality constraints added to modification step: {len(quality_constraints)}")

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
            model_id=getattr(input_processor_agent.model, 'id', 'Unknown') if input_processor_agent and input_processor_agent.model else 'Dynamic',
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
            model_id=getattr(input_processor_agent.model, 'id', 'Unknown') if input_processor_agent and input_processor_agent.model else 'Dynamic',
        ):
            # Get start cost for operation tracking
            start_tokens, start_cost = self.budget_manager.get_session_consumption()
            
            # Call route_and_execute without budget_manager parameter to match interface
            result = route_and_execute(
                action_type='modify',
                action_detail='r',  # 'r' is the refinement command
                current_project_path=self.current_project_path,
                current_structured_goal=self.current_structured_goal,
                session_state=self.session_state  
            )
            if isinstance(result, dict):
                success = result.get("success", False)
                if not success:
                    error = result.get("error", "Unknown error")
                    canvas.error("Action 'refine' failed. Please review logs.")
            else:
                success = bool(result)  # backward compatibility
            
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
    
    def _handle_knowledge_ingestion(
        self,
        document_path: Path,
        doc_type: str,
        metadata: Dict[str, Any],
        *,
        is_folder: bool = False,
        force_refresh: bool = False  # ADD THIS
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Ingests knowledge from a given path (file or folder) into the specified knowledge space.

        Expects metadata to include:
        - "project_name": the target knowledge space.
        - other optional keys (framework, version, global).

        Args:
            document_path: Path to the file or directory to ingest.
            doc_type:      A string label for the document type (e.g. "API Doc").
            metadata:      A dict that MUST contain "project_name".
            is_folder:     If True, ingests recursively as a directory.

        Returns:
            A tuple (success: bool, stats: dict) from the ingestor.
        """
        # 1. Extract the target knowledge space from metadata
        project_name = metadata.get("project_name")
        if not project_name:
            raise ValueError(
                "No 'project_name' defined in step metadata; "
                "explicit project_name is required to define a knowledge space."
            )

        # 2. Import and instantiate the enhanced ingestor
        from i2c.agents.knowledge.enhanced_knowledge_ingestor import EnhancedKnowledgeIngestorAgent
        
        ingestor = EnhancedKnowledgeIngestorAgent(
            budget_manager=self.budget_manager,     # required by the agent
            knowledge_space=project_name            # injects your per-step project name
        )

        # 3. Execute ingestion
        success, stats = ingestor.execute(
            document_path=document_path,
            document_type=doc_type,
            metadata=metadata,
            recursive=is_folder,
            force_refresh=force_refresh
        )

        # 4. Log or print summary
        canvas.info(f"[Knowledge Ingestion] Space: '{project_name}' → stats: {stats}")
        return success, stats

    def _process_knowledge_step(self, step: Dict[str, Any]) -> None:
        """Process a knowledge step - add documentation to knowledge base"""
        doc_path = step.get("doc_path", "")
        if not doc_path:
            canvas.warning("Knowledge step missing doc_path. Skipping...")
            return

        doc_path = Path(doc_path)
        if not doc_path.is_absolute():
            doc_path = Path(os.getcwd()) / doc_path

        if not doc_path.exists():
            canvas.warning(f"Document path does not exist: {doc_path}")
            return

        doc_type = step.get("doc_type", "API Documentation")
        metadata = {
            "project_name": step.get("project_name"), 
            "framework": step.get("framework", ""),
            "version": step.get("version", ""),
            "project_path": str(self.current_project_path) if self.current_project_path else "global",
            "global": step.get("global", True)
        }

        canvas.step(f"Adding documentation to knowledge base: {doc_path.name}")
        canvas.info(f"🔍 DEBUG: Knowledge step processing with session state: {len(self.session_state or {})} keys")

        try:
            # Get force_refresh from step
            force_refresh = step.get("force_refresh", False)

            success, results = self._handle_knowledge_ingestion(
                doc_path, 
                step.get("doc_type", "Docs"), 
                metadata, 
                is_folder=False,
                force_refresh=force_refresh
            )
            
            if success:
                canvas.success(f"✅ Added {doc_path.name}: {results['successful_files']} files, "
                            f"skipped {results['skipped_files']} (cached)")

                # Create/update knowledge_base in session_state after successful ingestion
                try:
                    from i2c.workflow.modification.rag_config import get_embed_model
                    from i2c.db_utils import get_db_connection
                    
                    # Initialize session_state if not exists
                    if not hasattr(self, 'session_state') or self.session_state is None:
                        self.session_state = {}
                    
                    # Always create/update knowledge_base after successful ingestion
                    db = get_db_connection()
                    embed_model = get_embed_model()
                    
                    if db and embed_model:
                        self.session_state['knowledge_base'] = SessionKnowledgeBase(db, embed_model)
                        # Also store db and embed_model for other components
                        self.session_state['db'] = db
                        self.session_state['embed_model'] = embed_model
                        self.session_state['db_path'] = "./data/lancedb"  # Standard path
                        
                        canvas.success("✅ Updated knowledge_base in session_state after ingestion")
                        canvas.info(f"🔍 DEBUG: Session state now has {len(self.session_state)} keys")
                    else:
                        canvas.warning("⚠️ Could not create knowledge_base - missing db or embed_model")
                        
                except Exception as e:
                    canvas.warning(f"⚠️ Could not create/update knowledge_base: {e}")
                    canvas.success("✅ Knowledge ingested to database - will be available to agents")
                                    
            else:
                canvas.error(f"Failed to add {doc_path.name} to knowledge base.")
        except Exception as e:
            canvas.error(f"Error during ingestion: {e}")       
    
    def _process_knowledge_folder_step(self, step: Dict[str, Any]) -> None:
        """Process a knowledge folder step with smart caching"""
        folder_path = step.get("folder_path", "") or step.get("document_path", "")
        if not folder_path:
            canvas.warning("Knowledge folder step missing folder_path. Skipping...")
            return

        folder_path = Path(folder_path)
        if not folder_path.exists() or not folder_path.is_dir():
            canvas.warning(f"Folder path does not exist or is not a directory: {folder_path}")
            return

        doc_type = step.get("doc_type", "API Documentation")
        metadata = {
            "project_name": step.get("project_name"), 
            "framework": step.get("framework", ""),
            "version": step.get("version", ""),
            "project_path": str(self.current_project_path) if self.current_project_path else "global",
            "global": step.get("global", False)
        }

        canvas.step(f"Adding documentation folder to knowledge base: {folder_path.name}")

        try:
            # Get force_refresh from step
            force_refresh = step.get("force_refresh", False)

            success, results = self._handle_knowledge_ingestion(
                folder_path, 
                step.get("doc_type", "Docs"), 
                metadata, 
                is_folder=True,
                force_refresh=force_refresh
            )

            if success:
                canvas.success(f"✅ Added {folder_path.name}: {results['successful_files']} files, "
                            f"skipped {results['skipped_files']} (cached)")

                # Create/update knowledge_base in session_state after successful ingestion
                try:
                    from i2c.workflow.modification.rag_config import get_embed_model
                    from i2c.db_utils import get_db_connection
                    
                    # Initialize session_state if not exists
                    if not hasattr(self, 'session_state') or self.session_state is None:
                        self.session_state = {}
                    
                    # Always create/update knowledge_base after successful ingestion
                    db = get_db_connection()
                    embed_model = get_embed_model()
                    
                    if db and embed_model:
                        self.session_state['knowledge_base'] = SessionKnowledgeBase(db, embed_model)
                        # Also store supporting components
                        self.session_state['db'] = db
                        self.session_state['embed_model'] = embed_model
                        self.session_state['db_path'] = "./data/lancedb"
                        
                        canvas.success("✅ Updated knowledge_base in session_state after folder ingestion")
                        canvas.info(f"🔍 DEBUG: Session state updated with knowledge components: {len(self.session_state)} total keys")
                    else:
                        canvas.warning("⚠️ Could not create knowledge_base - missing db or embed_model")
                        
                except Exception as e:
                    canvas.warning(f"⚠️ Could not create/update knowledge_base: {e}")
                    canvas.success("✅ Knowledge ingested to database - will be available to agents")
            else:
                canvas.error(f"Failed to add documentation from {folder_path.name}")
        except Exception as e:
            canvas.error(f"Error during ingestion: {e}")
            
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
    
