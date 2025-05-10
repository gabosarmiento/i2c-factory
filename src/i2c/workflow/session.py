# Manages the user interaction loop, state, and calls the orchestrator.

import os
from pathlib import Path
import json

# Import orchestrator function
from .orchestrator import route_and_execute
# Import CLI controller
from i2c.cli.controller import canvas
from i2c.workflow.utils import sanitize_filename, ensure_project_path
# Import handlers from the sibling module
from .session_handlers import (
    handle_get_user_action,
    handle_load_project,
    handle_new_project_idea,
    handle_knowledge_management
)
from i2c.cli.budget_display import show_budget_status, show_budget_summary, show_operation_cost

# --- Configuration ---
DEFAULT_OUTPUT_DIR_BASE = Path("./output")

# Updated section for workflow/session.py with simplified budget display integration
def run_session():
    """Manages the overall user session and interaction loop."""
    from i2c.agents.core_agents import input_processor_agent  # Lazy import to avoid circular dependency
    from i2c.agents.budget_manager import BudgetManagerAgent
        
    canvas.info("Initializing Session…")
    budget_manager = BudgetManagerAgent(session_budget=None)

    # Session state variables
    current_project_path: Path | None = None
    last_raw_idea: str | None = None
    current_structured_goal: dict | None = None

    # We'll keep a single reader-agent around once we have a project_path
    from i2c.agents.modification_team.context_reader.context_reader_agent import ContextReaderAgent
    reader_agent: ContextReaderAgent | None = None

    while True:
        # Show budget status (with warnings only when approaching limit)
        # Returns True if a warning was shown
        show_budget_status(budget_manager)
        
        canvas.step("Ready for next action")
        command_type, command_detail = handle_get_user_action(current_project_path)
        
        if command_type == 'quit':
            canvas.info("Exiting session.")
            # Show comprehensive budget summary at end of session
            show_budget_summary(budget_manager)
            tokens, cost = budget_manager.get_session_consumption()
            canvas.info(f"Session Summary: Consumed ~{tokens} tokens (~${cost:.6f})")
            break
        
        elif command_type == 'knowledge':  # Handle knowledge command
            if not current_project_path:
                canvas.warning("No active project. Create or load a project first.")
                continue
                
            handle_knowledge_management(current_project_path)
            
        elif command_type == 'load_project':
            loaded_path, inferred_goal = handle_load_project(command_detail)
            if loaded_path:
                current_project_path = loaded_path
                current_structured_goal = inferred_goal
                last_raw_idea = f"Loaded project: {command_detail}"
                if not current_structured_goal:
                    canvas.warning("Could not infer project objective/language.")
            print("-" * 30)
            continue

        elif command_type == 'new_idea':
            raw = command_detail
            last_raw_idea = raw

            # Standard approval without visual display
            if not budget_manager.request_approval(
                description="New Idea Clarification",
                prompt=raw,
                model_id=getattr(input_processor_agent.model, 'id', 'Unknown'),
            ):
                canvas.warning("Clarification cancelled due to budget rejection.")
                print("-" * 30)
                continue

            canvas.step("Clarifying new idea…")
            try:
                # Get start cost for operation tracking
                start_tokens, start_cost = budget_manager.get_session_consumption()
                
                resp = input_processor_agent.run(raw)
                
                # Update budget manager with metrics from Agno agent
                budget_manager.update_from_agno_metrics(input_processor_agent)
                
                # Calculate operation cost
                end_tokens, end_cost = budget_manager.get_session_consumption()
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
                current_structured_goal = proc
                canvas.success(f"Objective: {proc['objective']}")
                canvas.success(f"Language:  {proc['language']}")
            except Exception as e:
                canvas.error(f"Error clarifying idea: {e}")
                print("-" * 30)
                continue

            # Project naming
            suggested = sanitize_filename(current_structured_goal['objective'])
            answer = canvas.get_user_input(
                f"Enter directory name (suggestion: '{suggested}'): "
            ).strip()
            final_name = sanitize_filename(answer or suggested)
            current_project_path = ensure_project_path(DEFAULT_OUTPUT_DIR_BASE, final_name)

            # Index (empty dir) using the class-based agent
            if current_project_path.exists() and any(current_project_path.glob("*")):  # Only index if directory has files
                reader_agent = ContextReaderAgent(project_path=current_project_path)
                status = reader_agent.index_project_context()
                canvas.info(f"Indexing Status: {status}")
            else: 
                canvas.info("Skipping initial indexing for empty directory...")

            canvas.info(f"Preparing new project generation in: {current_project_path}")

 
            # Standard approval without visual display
            # Standard approval without visual display
            if budget_manager.request_approval(
                description="Initial Project Generation",
                prompt=current_structured_goal['objective'],
                model_id=getattr(input_processor_agent.model, 'id', 'Unknown'),
            ):
                # Get start cost for operation tracking
                start_tokens, start_cost = budget_manager.get_session_consumption()
                
                # Use the recovery-enabled version
                try:
                    from i2c.workflow.orchestrator import route_and_execute_with_recovery
                    ok = route_and_execute_with_recovery(
                        action_type='generate',
                        action_detail=current_structured_goal,
                        current_project_path=current_project_path,
                        current_structured_goal=current_structured_goal
                    )
                except ImportError:
                    # Fallback if the recovery function isn't available
                    ok = route_and_execute(
                        action_type='generate',
                        action_detail=current_structured_goal,
                        current_project_path=current_project_path,
                        current_structured_goal=current_structured_goal
                    )
                
                if not ok:
                    canvas.error("Action 'generate' failed. Please review logs.")
       
                # Calculate operation cost
                end_tokens, end_cost = budget_manager.get_session_consumption()
                op_tokens = end_tokens - start_tokens
                op_cost = end_cost - start_cost
                
                # Show operation cost after major operation
                show_operation_cost(
                    operation="Initial Project Generation",
                    tokens=op_tokens,
                    cost=op_cost
                )
                
                # Show comprehensive budget summary after major operations
                show_budget_summary(budget_manager)
            else:
                canvas.warning("Generation cancelled due to budget rejection.")

        elif command_type == 'modify':
            if not (current_project_path and current_structured_goal):
                canvas.warning("Load or create a project first before modifying.")
                print("-" * 30)
                continue

            # Standard approval without visual display
            if budget_manager.request_approval(
                description=f"Project Modification ({command_detail})",
                prompt=command_detail,
                model_id=getattr(input_processor_agent.model, 'id', 'Unknown'),
            ):
                # Get start cost for operation tracking
                start_tokens, start_cost = budget_manager.get_session_consumption()
                
                # Use the recovery-enabled version
                try:
                    from i2c.workflow.orchestrator import route_and_execute_with_recovery
                    ok = route_and_execute_with_recovery(
                        action_type='modify',
                        action_detail=command_detail,
                        current_project_path=current_project_path,
                        current_structured_goal=current_structured_goal
                    )
                except ImportError:
                    # Fallback if the recovery function isn't available
                    ok = route_and_execute(
                        action_type='modify',
                        action_detail=command_detail,
                        current_project_path=current_project_path,
                        current_structured_goal=current_structured_goal
                    )
                
                if not ok:
                    canvas.error("Action 'modify' failed. Please review logs.")
                    
                # Calculate operation cost
                end_tokens, end_cost = budget_manager.get_session_consumption()
                op_tokens = end_tokens - start_tokens
                op_cost = end_cost - start_cost
                
                # Show operation cost after major operation
                show_operation_cost(
                    operation=f"Project Modification ({command_detail[:20]}...)",
                    tokens=op_tokens,
                    cost=op_cost
                )
            else:
                canvas.warning("Modification cancelled due to budget rejection.")

        else:
            print("-" * 30)
            continue

        print("-" * 30)

    canvas.end_process("Session ended.")
    
def start_factory_session():
    run_session()
