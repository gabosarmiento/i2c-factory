# /workflow/session_handlers.py
# Contains handler functions for different actions within the user session.

import json
from pathlib import Path

# Import necessary components (agents, utils, canvas, llms)
from agents.core_agents import input_processor_agent
# <<< Import the new context analyzer agent >>>
from agents.core_agents import project_context_analyzer_agent
from agents.modification_team.context_reader import context_reader_agent
from agents.budget_manager import BudgetManagerAgent
from cli.controller import canvas
from .utils import sanitize_filename, ensure_project_path
from builtins import llm_middle

# Function to safely parse JSON, returning None on failure
def _safe_json_loads(text: str) -> dict | None:
    try:
        # Pre-process potential markdown fences just in case
        text = text.strip()
        if text.startswith("```json"): text = text[len("```json"):].strip()
        if text.startswith("```"): text = text[3:].strip()
        if text.endswith("```"): text = text[:-3].strip()
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        canvas.error(f"DEBUG: Failed to parse JSON: {text[:500]}")
        return None

def handle_get_user_action(current_project_path: Path | None) -> tuple[str | None, str | None]:
    """Gets and parses the user's next action command."""
    if current_project_path:
        project_status = f"Project: '{current_project_path.name}'"
        options = "'f <feature_idea>', 'r' (refine), 'k' (knowledge), 'p <path>' (switch project), 'q' (quit)"
        action_prompt = f"{project_status} | Options: {options}:"
    else:
        project_status = "No active project."
        options = "'<your new idea>', 'p <path>' (load existing), 'q' (quit)"
        action_prompt = f"{project_status} | Options: {options}:"

    user_input = canvas.get_user_input(action_prompt).strip()
    command_lower = user_input.lower()

    if command_lower == 'q':
        return 'quit', None
    elif command_lower.startswith('p '):
        path_str = user_input[len('p '):].strip().strip('\'"')
        return 'load_project', path_str
    elif current_project_path: 
        if command_lower == 'r':
            return 'modify', 'r'
        elif command_lower.startswith('f '):
            feature_idea = user_input[len('f '):].strip()
            if not feature_idea:
                canvas.warning("Please provide a description for the feature.")
                return None, None
            return 'modify', f'f {feature_idea}'
        elif command_lower == 'k':  
            return 'knowledge', None
        elif user_input:
            canvas.warning(f"Unrecognized command '{user_input}'. Use 'f', 'r', 'k', 'p', or 'q'.")
            return None, None
        else:
            return None, None
    elif user_input:
        return 'new_idea', user_input
    else:
        return None, None


# <<< MODIFIED to return structured_goal >>>
def handle_load_project(path_str: str) -> tuple[Path | None, dict | None]:
    """Handles loading, indexing, and analyzing an existing project path."""
    potential_path = Path(path_str).expanduser()
    if not potential_path.is_dir():
        canvas.error(f"Invalid path provided: '{path_str}' is not a directory.")
        return None, None

    canvas.info(f"Switching to project path: {potential_path}")
    project_path = potential_path.resolve()
    structured_goal = None # Initialize goal

    # Trigger Indexing
    canvas.step(f"Indexing project context for '{project_path.name}'...")
    index_status = context_reader_agent.index_project_context(project_path)
    if index_status["errors"]:
        canvas.warning(f"Indexing completed with errors: {index_status['errors']}")
    else:
        canvas.success(f"Indexing complete. Indexed: {index_status['files_indexed']}, Skipped: {index_status['files_skipped']}.")

    # --- <<< Call the Project Context Analyzer Agent >>> ---
    canvas.step("Analyzing project structure for objective and suggestions...")
    try:
        # Create a list of file names relative to the project path
        # Filter out hidden files/dirs again for the prompt
        file_list = []
        for p in project_path.rglob('*'):
             if any(part.startswith('.') for part in p.relative_to(project_path).parts) or \
                any(ex in p.relative_to(project_path).parts for ex in ["__pycache__", "node_modules", ".git"]):
                 continue
             if p.is_file():
                  file_list.append(str(p.relative_to(project_path)))

        if not file_list:
             canvas.warning("No files found to analyze in the project directory.")
        else:
            # Limit number of files sent in prompt
            max_files_for_prompt = 100
            prompt = "Files:\n" + "\n".join(file_list[:max_files_for_prompt])
            if len(file_list) > max_files_for_prompt:
                 prompt += "\n... (more files exist)"

            # Use direct run - error handling below
            response = project_context_analyzer_agent.run(prompt)
            analysis_json = response.content if hasattr(response, "content") else str(response)
            analysis_data = _safe_json_loads(analysis_json) # Use safe JSON parsing

            if analysis_data and "objective" in analysis_data and "language" in analysis_data:
                # Store the inferred goal
                structured_goal = {
                    "objective": analysis_data.get("objective", "Objective could not be inferred."),
                    "language": analysis_data.get("language", "Language could not be inferred.")
                }
                canvas.success(f"Inferred Objective: {structured_goal['objective']}")
                canvas.success(f"Inferred Language: {structured_goal['language']}")

                # Display suggestions
                suggestions = analysis_data.get("suggestions", [])
                if suggestions:
                    canvas.info("🔮 Suggestions for next steps:")
                    for idx, suggestion in enumerate(suggestions, 1):
                        canvas.info(f"   {idx}. {suggestion}")
                else:
                    canvas.warning("   No specific next-step suggestions generated.")
            else:
                 canvas.warning("Could not fully analyze project structure from LLM response.")
                 canvas.error(f"Analyzer Raw Response: {analysis_json[:500]}")


    except Exception as e:
        canvas.warning(f"Could not analyze project or generate suggestions: {e}")
    # --- <<< End Analyzer Call >>> ---

    # Return path and the inferred goal (which might be None if analysis failed)
    return project_path, structured_goal


def handle_new_project_idea(raw_idea: str, budget_manager: BudgetManagerAgent, base_output_dir: Path) -> tuple[dict | None, Path | None]:
    """Handles clarifying, naming, and setting up a new project."""
    # ... (Budget check logic remains the same) ...
    budget_description = "New Idea Clarification"
    prompt_for_estimation = raw_idea
    model_id_for_estimation = getattr(llm_middle, 'id', 'Unknown')
    approved = budget_manager.request_approval(
        description=budget_description,
        prompt=prompt_for_estimation,
        model_id=model_id_for_estimation
    )
    if not approved:
        canvas.warning("Action cancelled due to budget rejection.")
        return None, None

    # Clarify Idea
    canvas.step("Clarifying new idea...")
    response_content = None
    processed_goal = None
    try:
        response = input_processor_agent.run(raw_idea)
        response_content = response.content if hasattr(response, 'content') else str(response)
        processed_goal = _safe_json_loads(response_content) # Use safe JSON parsing
        if not isinstance(processed_goal, dict) or "objective" not in processed_goal or "language" not in processed_goal:
             raise ValueError("LLM response for clarification was invalid JSON structure.")
        canvas.success(f"Objective: {processed_goal['objective']}")
        canvas.success(f"Language: {processed_goal['language']}")
    except Exception as e:
        canvas.error(f"Error clarifying idea: {e}")
        if response_content: canvas.error(f"LLM Raw Response: {response_content[:500]}")
        return None, None

    # Get Project Name
    suggested_name = sanitize_filename(processed_goal['objective'])
    name_prompt = f"Enter directory name (suggestion: '{suggested_name}'): "
    project_name_input = canvas.get_user_input(name_prompt).strip()
    final_project_name = sanitize_filename(project_name_input or suggested_name)
    project_path = ensure_project_path(base_output_dir, final_project_name)

    # Index the (currently empty) new project directory
    context_reader_agent.index_project_context(project_path)

    canvas.info(f"Preparing new project generation in: {project_path}")
    return processed_goal, project_path

def handle_view_documentation(project_path: Path):
    """View documentation files loaded in the knowledge base."""
    try:
        from db_utils import get_db_connection, TABLE_KNOWLEDGE_BASE
        
        db = get_db_connection()
        if not db:
            canvas.error("Failed to connect to database")
            return
        
        # Get all documents for this project's knowledge space
        knowledge_space = f"project_{project_path.name}"
        
        try:
            table = db.open_table(TABLE_KNOWLEDGE_BASE)
            df = table.to_pandas()
            
            # Filter by knowledge space
            project_docs = df[df['knowledge_space'] == knowledge_space] if 'knowledge_space' in df.columns else df
            
            if project_docs.empty:
                canvas.warning("No documentation loaded for this project yet.")
                canvas.info("Use option 1 to add documentation files.")
                return
            
            # Group by source file
            unique_sources = project_docs['source'].unique()
            
            canvas.info(f"\nLoaded Documentation ({len(unique_sources)} files):")
            canvas.info("-" * 50)
            
            for idx, source in enumerate(unique_sources, 1):
                source_docs = project_docs[project_docs['source'] == source]
                
                # Extract metadata
                doc_type = source_docs.iloc[0]['document_type'] if 'document_type' in source_docs.columns else 'unknown'
                framework = source_docs.iloc[0]['framework'] if 'framework' in source_docs.columns else 'N/A'
                version = source_docs.iloc[0]['version'] if 'version' in source_docs.columns else 'N/A'
                chunks = len(source_docs)
                
                canvas.info(f"{idx}. {Path(source).name}")
                canvas.info(f"   Type: {doc_type}")
                canvas.info(f"   Framework: {framework}")
                canvas.info(f"   Version: {version}")
                canvas.info(f"   Chunks: {chunks}")
                canvas.info("")
            
            canvas.info("-" * 50)
            canvas.info(f"Total chunks in knowledge base: {len(project_docs)}")
            
        except Exception as e:
            canvas.error(f"Error retrieving documentation list: {e}")
            
    except ImportError:
        canvas.error("Database utilities not available. Please check your installation.")

def handle_search_knowledge(project_path: Path):
    """Search the knowledge base for specific information."""
    try:
        from db_utils import get_db_connection, query_context_filtered, TABLE_KNOWLEDGE_BASE
        from agents.modification_team.context_utils import generate_embedding
        
        db = get_db_connection()
        if not db:
            canvas.error("Failed to connect to database")
            return
        
        # Get search query from user
        query = canvas.get_user_input("Enter search query (or 'back' to return): ").strip()
        
        if query.lower() == 'back':
            return
        
        if not query:
            canvas.warning("Please enter a search query.")
            return
        
        canvas.info(f"\nSearching for: '{query}'...")
        
        try:
            # Generate embedding for the query
            query_vector = generate_embedding(query)
            
            if query_vector is None:
                canvas.error("Failed to generate search embedding. Please check your embedding model.")
                return
            
            # Search with filters for this project
            knowledge_space = f"project_{project_path.name}"
            
            results = query_context_filtered(
                db=db,
                table_name=TABLE_KNOWLEDGE_BASE,
                query_vector=query_vector,
                filters={'knowledge_space': knowledge_space},
                limit=5
            )
            
            if results is None or results.empty:
                canvas.warning("No relevant results found.")
                return
            
            # Display results
            canvas.info(f"\nFound {len(results)} relevant results:")
            canvas.info("-" * 50)
            
            for idx, row in results.iterrows():
                canvas.info(f"\n{idx + 1}. Source: {Path(row['source']).name}")
                if 'document_type' in row:
                    canvas.info(f"   Type: {row['document_type']}")
                if 'framework' in row and row['framework']:
                    canvas.info(f"   Framework: {row['framework']}")
                
                # Show content preview
                content = row['content']
                preview_length = 200
                content_preview = content[:preview_length] + "..." if len(content) > preview_length else content
                
                canvas.info(f"\n   Content Preview:")
                canvas.info(f"   {content_preview}")
                canvas.info("-" * 50)
            
            # Ask if user wants to see full content
            if len(results) > 0:
                view_full = canvas.get_user_input("\nView full content of a result? Enter number (1-{}) or 'n': ".format(len(results))).strip()
                
                if view_full.isdigit() and 1 <= int(view_full) <= len(results):
                    selected_idx = int(view_full) - 1
                    selected_row = results.iloc[selected_idx]
                    
                    canvas.info("\nFull Content:")
                    canvas.info("-" * 50)
                    canvas.info(selected_row['content'])
                    canvas.info("-" * 50)
                    
                    canvas.get_user_input("\nPress Enter to continue...")
                    
        except Exception as e:
            canvas.error(f"Error searching knowledge base: {e}")
            import traceback
            canvas.error(traceback.format_exc())
            
    except ImportError as e:
        canvas.error(f"Required modules not available: {e}")
        canvas.error("Please ensure all dependencies are installed.")
        
def handle_knowledge_management(project_path: Path):
    """Handle knowledge base management for current project."""
    
    # Check if required modules are available
    try:
        from agents.knowledge.knowledge_ingestor import KnowledgeIngestorAgent
        from db_utils import get_db_connection
    except ImportError as e:
        canvas.error("Knowledge base features not fully implemented yet.")
        canvas.error(f"Missing module: {e}")
        canvas.info("\nThe knowledge base system is still under development.")
        canvas.info("Required components:")
        canvas.info("- KnowledgeIngestorAgent")
        canvas.info("- Enhanced database utilities")
        canvas.info("- Document parsers")
        return
    
    while True:
        canvas.info("\nKnowledge Base Management")
        canvas.info("1. Add documentation file")
        canvas.info("2. View loaded documentation")
        canvas.info("3. Search knowledge base")
        canvas.info("4. Return to main menu")
        
        choice = canvas.get_user_input("Select option (1-4): ").strip()
        
        if choice == '1':
            handle_add_documentation(project_path)
        elif choice == '2':
            handle_view_documentation(project_path)
        elif choice == '3':
            handle_search_knowledge(project_path)
        elif choice == '4':
            break
        else:
            canvas.warning("Invalid option. Please select 1-4.")

def handle_add_documentation(project_path: Path):
    """Add a documentation file to the knowledge base."""
    
    # Get file path
    file_path = canvas.get_user_input("Enter path to documentation file: ").strip()
    
    if not file_path:
        canvas.warning("No file path provided.")
        return
        
    doc_path = Path(file_path).expanduser()
    
    if not doc_path.exists():
        canvas.error(f"File not found: {doc_path}")
        return
        
    if not doc_path.is_file():
        canvas.error(f"Path is not a file: {doc_path}")
        return
    
    # Get document metadata
    canvas.info("\nDocument types:")
    canvas.info("1. API Documentation")
    canvas.info("2. Tutorial/Guide")
    canvas.info("3. Code Examples")
    canvas.info("4. Best Practices")
    canvas.info("5. Other")
    
    doc_type_map = {
        '1': 'api_documentation',
        '2': 'tutorial',
        '3': 'code_examples',
        '4': 'best_practices',
        '5': 'other'
    }
    
    doc_type_choice = canvas.get_user_input("Select document type (1-5): ").strip()
    doc_type = doc_type_map.get(doc_type_choice, 'other')
    
    # Optional metadata
    framework = canvas.get_user_input("Framework/Library (optional, e.g., React, Django): ").strip()
    version = canvas.get_user_input("Version (optional, e.g., 3.0.0): ").strip()
    
    canvas.info(f"\nProcessing {doc_path.name}...")
    
    try:
        # Initialize the knowledge ingestor
        from agents.knowledge.knowledge_ingestor import KnowledgeIngestorAgent
        from agents.budget_manager import BudgetManagerAgent
        
        # Use the project's knowledge space
        knowledge_space = f"project_{project_path.name}"
        
        ingestor = KnowledgeIngestorAgent(
            budget_manager=BudgetManagerAgent(session_budget=0.1),  # Small budget for ingestion
            knowledge_space=knowledge_space
        )
        
        # Execute ingestion
        success, result = ingestor.execute(
            document_path=doc_path,
            document_type=doc_type,
            metadata={
                'framework': framework,
                'version': version,
                'project': project_path.name
            }
        )
        
        if success:
            canvas.success(f"Successfully added {doc_path.name} to knowledge base!")
            canvas.info(f"Created {result.get('chunks_created', 0)} knowledge chunks")
        else:
            canvas.error(f"Failed to add documentation: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        canvas.error(f"Error adding documentation: {e}")