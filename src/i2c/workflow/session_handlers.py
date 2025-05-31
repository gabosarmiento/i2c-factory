# /workflow/session_handlers.py
# Contains handler functions for different actions within the user session.

import json
from pathlib import Path

# Import necessary components (agents, utils, canvas, llms)
from i2c.agents.core_agents import input_processor_agent
from i2c.agents.core_agents import project_context_analyzer_agent
from i2c.agents.modification_team.context_reader import context_reader_agent
from i2c.agents.budget_manager import BudgetManagerAgent
from i2c.cli.controller import canvas
from i2c.cli.utils.documentation_type_selector import get_document_type
from i2c.workflow.utils import sanitize_filename, ensure_project_path
from builtins import llm_middle
import hashlib
from datetime import datetime
from i2c.workflow.visual_helpers import (
    show_help_message,
    show_project_plan
)
# Function to safely parse JSON, returning None on failure
def _safe_json_loads(text: str) -> dict | None:
    """Safely parse JSON, handling potentially complex JSON structures."""
    try:
        # Handle case where the input is already a dict
        if isinstance(text, dict):
            return text
            
        # Pre-process potential markdown fences
        text = text.strip()
        if text.startswith("```json"): text = text[len("```json"):].strip()
        if text.startswith("```"): text = text[3:].strip()
        if text.endswith("```"): text = text[:-3].strip()
        
        # Try to parse the JSON
        parsed = json.loads(text)
        
        if "error" in parsed:
            raise ValueError(f"Agent error: {parsed['error']}")
        # Handle case where we have a JSON with a "prompt" field
        if isinstance(parsed, dict) and "prompt" in parsed:
            prompt_content = parsed["prompt"]
            
            # For handling single-line input with escaped newlines
            if isinstance(prompt_content, str):
                # Replace literal "\n" with actual newlines for better processing
                prompt_content = prompt_content.replace("\\n", "\n")
            
            # Process the prompt content through the input processor
            from i2c.agents.core_agents import input_processor_agent
            canvas.info("Processing JSON prompt content...")
            
            from i2c.agents.core_agents import get_rag_enabled_agent
            temp_agent = get_rag_enabled_agent("input_processor")
            response = temp_agent.run(prompt_content)
            response_content = response.content if hasattr(response, 'content') else str(response)
            
            try:
                processed = json.loads(response_content)
                if isinstance(processed, dict) and "objective" in processed and "language" in processed:
                    return processed
                else:
                    # If structured correctly but missing fields
                    canvas.warning("Processed JSON missing required fields. Using original.")
            except json.JSONDecodeError:
                # If not valid JSON, use the original parsed content
                canvas.warning("Could not parse processor response as JSON.")
                
            # Return the original parsed JSON if we couldn't process the prompt
            return parsed
            
        # If we have a regular JSON with objective/language, use it directly
        if isinstance(parsed, dict) and "objective" in parsed and "language" in parsed:
            return parsed
            
        # Return whatever was successfully parsed
        return parsed
    except (json.JSONDecodeError, TypeError) as e:
        # Log the full error without truncation
        import logging
        logging.error(f"JSON parse error: {str(e)}")
        logging.error(f"Failed JSON content: {text}")
        
        # Show a more helpful error to the user
        canvas.error(f"Failed to parse JSON: {str(e)}")
        canvas.error("Make sure your JSON is properly formatted and doesn't contain unescaped special characters.")
        canvas.info("Tip: For complex JSON, try escaping newlines with \\n instead of actual line breaks.")
        
        return None



def handle_get_user_action(current_project_path: Path | None) -> tuple[str | None, str | None]:
    """Gets and parses the user's next action command."""
    
    if current_project_path:
        project_status = f"Project: '{current_project_path.name}'"
        options = "'f <idea>', 'r', 's <story>', 'k', 'plan', '?', 'q'"
        action_prompt = f"{project_status} | Options: {options}:"
    else:
        project_status = "No active project."
        options = "'<idea>', 'p <path>', '?', 'q'"
        action_prompt = f"{project_status} | Options: {options}:"

    user_input = canvas.get_user_input(f"🎯 {action_prompt}").strip()
    command_lower = user_input.lower()

    # Handle help command
    if command_lower == "?" or command_lower == "help":
        show_help_message(current_project_path)
        return None, None
        
    # Handle plan command
    if command_lower == "plan" and current_project_path:
        show_project_plan(current_project_path)
        return None, None

    # Handle quit
    if command_lower == 'q':
        return 'quit', None
        
    # Handle project path
    elif command_lower.startswith('p '):
        path_str = user_input[len('p '):].strip().strip('\'"')
        return 'load_project', path_str
        
    # Commands requiring an active project
    elif current_project_path: 
        # Handle refine
        if command_lower == 'r':
            return 'modify', 'r'
            
        # Handle feature (both 'f' and 'feature')
        elif command_lower.startswith('f ') or command_lower.startswith('feature '):
            prefix = 'f ' if command_lower.startswith('f ') else 'feature '
            feature_idea = user_input[len(prefix):].strip()
            if not feature_idea:
                canvas.warning("⚠️ Please provide a description for the feature.")
                return None, None
            return 'modify', f'f {feature_idea}'
            
        # Handle story (both 's' and 'story')
        elif command_lower.startswith('s ') or command_lower.startswith('story '):
            prefix = 's ' if command_lower.startswith('s ') else 'story '
            story_text = user_input[len(prefix):].strip()
            if not story_text:
                canvas.warning("⚠️ Please provide a description for the user story.")
                return None, None
            return 'feature_pipeline', story_text
            
        # Handle knowledge
        elif command_lower == 'k':  
            return 'knowledge', None
            
        # Unknown command
        elif user_input:
            canvas.warning(f"⚠️ Unrecognized command. Type '?' for help.")
            return None, None
            
        # Empty input
        else:
            return None, None
            
    # No project active - treat as new idea
    elif user_input:
        return 'new_idea', user_input
        
    # Empty input
    else:
        return None, None



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

    # Call the Project Context Analyzer Agent
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
            from i2c.agents.core_agents import get_rag_enabled_agent
            temp_agent = get_rag_enabled_agent("project_context_analyzer")
            response = temp_agent.run(prompt)
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

    # Return path and the inferred goal (which might be None if analysis failed)
    return project_path, structured_goal


def handle_new_project_idea(raw_idea: str, budget_manager: BudgetManagerAgent, base_output_dir: Path) -> tuple[dict | None, Path | None]:
    """Handles clarifying, naming, and setting up a new project."""
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
        from i2c.agents.core_agents import get_rag_enabled_agent
        temp_agent = get_rag_enabled_agent("input_processor")
        response = temp_agent.run(raw_idea)
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

#
# Knowledge Management Functions
#

def handle_knowledge_management(project_path: Path):
    """Main entry point for knowledge base management for the current project."""
    while True:
        canvas.info("\n📚 Knowledge Base Management")
        canvas.info("1. Add documentation file")
        canvas.info("2. Add documentation folder")
        canvas.info("3. View loaded documentation")
        canvas.info("4. Search knowledge base")
        canvas.info("5. Refresh documentation")
        canvas.info("6. Return to main menu")
        
        choice = canvas.get_user_input("Select option (1-6): ").strip()
        
        if choice == '1':
            handle_add_documentation_file(project_path)
        elif choice == '2':
            handle_add_documentation_folder(project_path)
        elif choice == '3':
            handle_view_documentation(project_path)
        elif choice == '4':
            handle_search_knowledge(project_path)
        elif choice == '5':
            handle_refresh_documentation(project_path)
        elif choice == '6':
            break
        else:
            canvas.warning("Invalid option. Please select 1-6.")

def handle_view_documentation(project_path: Path):
    """View documentation files loaded in the knowledge base."""
    try:
        from i2c.db_utils import get_db_connection, TABLE_KNOWLEDGE_BASE
        
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
        from i2c.db_utils import get_db_connection, query_context_filtered, TABLE_KNOWLEDGE_BASE
        from i2c.agents.modification_team.context_utils import generate_embedding
        
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
                if 'chunk_type' in row:
                    canvas.info(f"   Chunk: {row['chunk_type']}")
                
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

def handle_add_documentation_file(project_path: Path):
    """Add a single documentation file to the knowledge base."""
    # Get file path
    file_path_str = canvas.get_user_input("Enter path to documentation file: ").strip()
    
    if not file_path_str:
        canvas.warning("No file path provided.")
        return
        
    file_path = Path(file_path_str).expanduser().resolve()
    
    if not file_path.exists():
        canvas.error(f"File not found: {file_path}")
        return
        
    if not file_path.is_file():
        canvas.error(f"Path is not a file: {file_path}")
        return
    
    # Get document metadata
    document_type = get_document_type()
    framework = canvas.get_user_input("Framework/Library (optional, e.g., React, Django): ").strip()
    version = canvas.get_user_input("Version (optional, e.g., 3.0.0): ").strip()
    
    # Process the file
    ingest_documentation(
        project_path=project_path,
        doc_path=file_path,
        document_type=document_type,
        framework=framework,
        version=version
    )

def handle_add_documentation_folder(project_path: Path):
    """Add a folder of documentation files to the knowledge base."""
    # Get folder path
    folder_path_str = canvas.get_user_input("Enter path to documentation folder: ").strip()
    
    if not folder_path_str:
        canvas.warning("No folder path provided.")
        return
        
    folder_path = Path(folder_path_str).expanduser().resolve()
    
    if not folder_path.exists():
        canvas.error(f"Folder not found: {folder_path}")
        return
        
    if not folder_path.is_dir():
        canvas.error(f"Path is not a directory: {folder_path}")
        return
    
    # Ask if we should process recursively
    recursive_input = canvas.get_user_input("Process subdirectories recursively? (y/n): ").strip().lower()
    recursive = recursive_input.startswith('y')
    
    # Get document metadata
    document_type = get_document_type()
    framework = canvas.get_user_input("Framework/Library (optional, e.g., React, Django): ").strip()
    version = canvas.get_user_input("Version (optional, e.g., 3.0.0): ").strip()
    
    # Process the folder
    ingest_documentation(
        project_path=project_path,
        doc_path=folder_path,
        document_type=document_type,
        framework=framework,
        version=version,
        recursive=recursive
    )

def handle_refresh_documentation(project_path: Path):
    """Refresh/update previously loaded documentation."""
    # Option to refresh file, folder, or all
    canvas.info("\n🔄 Refresh Documentation")
    canvas.info("1. Refresh a specific file")
    canvas.info("2. Refresh a specific folder")
    canvas.info("3. Refresh all documentation")
    canvas.info("4. Return to knowledge menu")
    
    choice = canvas.get_user_input("Select option (1-4): ").strip()
    
    if choice == '4':
        return
    
    if choice == '1':
        # Refresh specific file
        file_path_str = canvas.get_user_input("Enter path to documentation file: ").strip()
        if not file_path_str:
            canvas.warning("No file path provided.")
            return
            
        file_path = Path(file_path_str).expanduser().resolve()
        
        if not file_path.exists() or not file_path.is_file():
            canvas.error(f"Invalid file path: {file_path}")
            return
            
        doc_path = file_path
        
    elif choice == '2':
        # Refresh specific folder
        folder_path_str = canvas.get_user_input("Enter path to documentation folder: ").strip()
        if not folder_path_str:
            canvas.warning("No folder path provided.")
            return
            
        folder_path = Path(folder_path_str).expanduser().resolve()
        
        if not folder_path.exists() or not folder_path.is_dir():
            canvas.error(f"Invalid folder path: {folder_path}")
            return
            
        doc_path = folder_path
        
    elif choice == '3':
        # Refresh all documentation - just use project docs directory
        docs_dir = project_path / "docs"
        if not docs_dir.exists() or not docs_dir.is_dir():
            canvas.warning("No docs directory found in project. Using project directory.")
            doc_path = project_path
        else:
            doc_path = docs_dir
    else:
        canvas.warning("Invalid option.")
        return
    
    # Get document metadata
    document_type = get_document_type()
    framework = canvas.get_user_input("Framework/Library (optional, e.g., React, Django): ").strip()
    version = canvas.get_user_input("Version (optional, e.g., 3.0.0): ").strip()
    
    # Execute refresh
    ingest_documentation(
        project_path=project_path,
        doc_path=doc_path,
        document_type=document_type,
        framework=framework,
        version=version,
        is_refresh=True
    )

# Implementation function for documentation processing
def ingest_documentation(
    project_path: Path, 
    doc_path: Path, 
    document_type: str, 
    framework: str = "",
    version: str = "",
    recursive: bool = True,
    is_refresh: bool = False
) -> bool:
    """
    Core function to ingest documentation into the knowledge base with improved error handling.
    
    Args:
        project_path: The project path for which documentation is being added
        doc_path: Path to the document or directory to ingest
        document_type: Type of document (e.g., "API Documentation")
        framework: Optional framework name (e.g., "React")
        version: Optional version info
        recursive: Whether to process directories recursively
        is_refresh: Whether this is a refresh of existing documentation
        
    Returns:
        bool: True if ingestion was successful, False otherwise
    """
    try:
        # Import dependencies with detailed error reporting
        canvas.info("Setting up knowledge ingestion...")
        
        try:
            from sentence_transformers import SentenceTransformer
            canvas.info("✅ SentenceTransformer imported successfully")
        except ImportError as e:
            canvas.error(f"Failed to import SentenceTransformer: {e}")
            canvas.error("Please install with: pip install sentence-transformers")
            return False
            
        try:
            import hashlib
            import json
            canvas.info("✅ Standard libraries imported successfully")
        except ImportError as e:
            canvas.error(f"Failed to import standard libraries: {e}")
            return False
            
        try:
            from i2c.db_utils import (
                get_db_connection,
                get_or_create_table,
                add_or_update_chunks,
                TABLE_KNOWLEDGE_BASE,
                SCHEMA_KNOWLEDGE_BASE
            )
            canvas.info("✅ Database utilities imported successfully")
        except ImportError as e:
            canvas.error(f"Failed to import database utilities: {e}")
            return False
        
        # Create a SentenceTransformerEmbedder wrapper class
        class SentenceTransformerEmbedder:
            def __init__(self):
                canvas.info("Initializing embedding model...")
                try:
                    self.model = SentenceTransformer('all-MiniLM-L6-v2')
                    canvas.info("✅ Embedding model initialized")
                except Exception as e:
                    canvas.error(f"Error initializing embedding model: {e}")
                    raise
                
            def get_embedding(self, text):
                return self.model.encode(text).tolist()
        
        # Use the project's knowledge space
        knowledge_space = f"project_{project_path.name}"
        canvas.info(f"Using knowledge space: {knowledge_space}")
        
        # Initialize embedding model
        try:
            embed_model = SentenceTransformerEmbedder()
            canvas.info("✅ Embedding model created successfully")
        except Exception as e:
            canvas.error(f"Failed to initialize embedding model: {e}")
            return False
        
        # Connect to database with retry
        db = None
        max_retries = 3
        for attempt in range(max_retries):
            try:
                canvas.info(f"Connecting to database (attempt {attempt+1}/{max_retries})...")
                db = get_db_connection()
                if db:
                    canvas.info(f"✅ Connected to database: {db}")
                    break
            except Exception as e:
                canvas.error(f"Database connection error (attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    canvas.info("Retrying database connection...")
                    import time
                    time.sleep(1)  # Wait before retry
                else:
                    canvas.error("Failed to connect to database after multiple attempts")
                    return False
                    
        if not db:
            canvas.error("Failed to connect to database")
            return False
            
        # Check database tables
        canvas.info("Checking for knowledge base table...")
        try:
            # First try to open the table to see if it exists
            if TABLE_KNOWLEDGE_BASE in db.table_names():
                canvas.info(f"Table '{TABLE_KNOWLEDGE_BASE}' exists")
                try:
                    table = db.open_table(TABLE_KNOWLEDGE_BASE)
                    # Try to get table schema to check if it's valid
                    schema = table.schema
                    canvas.info(f"Table schema: {schema}")
                except Exception as e:
                    canvas.warning(f"Error opening existing table: {e}")
                    canvas.warning("Will attempt to recreate the table")
                    try:
                        canvas.info(f"Dropping problematic table '{TABLE_KNOWLEDGE_BASE}'")
                        db.drop_table(TABLE_KNOWLEDGE_BASE)
                    except Exception as drop_e:
                        canvas.error(f"Error dropping table: {drop_e}")
            
            # Direct table creation approach
            try:
                canvas.info(f"Creating/ensuring table '{TABLE_KNOWLEDGE_BASE}'")
                if TABLE_KNOWLEDGE_BASE in db.table_names():
                    table = db.open_table(TABLE_KNOWLEDGE_BASE)
                else:
                    table = db.create_table(TABLE_KNOWLEDGE_BASE, schema=SCHEMA_KNOWLEDGE_BASE)
                canvas.success(f"✅ Table ready: {TABLE_KNOWLEDGE_BASE}")
            except Exception as e:
                canvas.error(f"Error creating table: {e}")
                import traceback
                canvas.error(traceback.format_exc())
                return False
        except Exception as e:
            canvas.error(f"Error checking/creating knowledge base table: {e}")
            import traceback
            canvas.error(traceback.format_exc())
            return False
            
        # Now process the document or directory
        if doc_path.is_dir():
            # Process directory
            pattern = "**/*" if recursive else "*"
            files_processed = 0
            files_succeeded = 0
            
            canvas.info(f"Processing directory: {doc_path}")
            for file_path in doc_path.glob(pattern):
                if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                    files_processed += 1
                    canvas.info(f"Processing file {files_processed}: {file_path}")
                    
                    # Process file based on type
                    if file_path.suffix.lower() == '.pdf':
                        success = process_pdf_file(
                            file_path, document_type, knowledge_space, embed_model, db, 
                            {"framework": framework, "version": version, "project": project_path.name}
                        )
                    else:
                        success = process_text_file(
                            file_path, document_type, knowledge_space, embed_model, db,
                            {"framework": framework, "version": version, "project": project_path.name}
                        )
                    
                    if success:
                        files_succeeded += 1
                        canvas.success(f"✅ Successfully processed {file_path}")
                    else:
                        canvas.error(f"❌ Failed to process {file_path}")
            
            # Report results
            canvas.success(f"📚 Successfully processed {files_succeeded}/{files_processed} files")
            return files_succeeded > 0
            
        else:
            # Process single file
            canvas.info(f"Processing single file: {doc_path}")
            if doc_path.suffix.lower() == '.pdf':
                success = process_pdf_file(
                    doc_path, document_type, knowledge_space, embed_model, db, 
                    {"framework": framework, "version": version, "project": project_path.name}
                )
            else:
                success = process_text_file(
                    doc_path, document_type, knowledge_space, embed_model, db,
                    {"framework": framework, "version": version, "project": project_path.name}
                )
            
            if success:
                canvas.success(f"✅ Successfully processed {doc_path}")
                return True
            else:
                canvas.error(f"❌ Failed to process {doc_path}")
                return False
                
    except Exception as e:
        canvas.error(f"Error ingesting documentation: {e}")
        import traceback
        canvas.error(traceback.format_exc())
        return False
    
def process_pdf_file(file_path, document_type, knowledge_space, embed_model, db, metadata=None):
    """Process a PDF file into knowledge chunks"""
    try:
        canvas.info(f"Processing PDF: {file_path}")
        
        # Try to import required libraries
        try:
            import pypdf
        except ImportError:
            canvas.error("pypdf package not installed. Install with 'pip install pypdf'")
            return False
            
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Read PDF
        pdf_reader = pypdf.PdfReader(open(file_path, 'rb'))
        num_pages = len(pdf_reader.pages)
        
        canvas.info(f"PDF has {num_pages} pages")
        
        # Process pages
        chunks = []
        for i in range(num_pages):
            try:
                if i % 10 == 0:
                    canvas.info(f"Processing page {i+1}/{num_pages}...")
                
                page = pdf_reader.pages[i]
                text = page.extract_text()
                
                # Skip empty pages
                if not text or len(text.strip()) < 10:
                    continue
                
                # Create vector
                vector = embed_model.get_embedding(text)
                
                # Create chunk
                chunk = {
                    "source": str(file_path),
                    "content": text,
                    "vector": vector,
                    "category": document_type,
                    "last_updated": datetime.now().isoformat(),
                    "knowledge_space": knowledge_space,
                    "document_type": document_type,
                    "framework": metadata.get("framework", "") if metadata else "",
                    "version": metadata.get("version", "") if metadata else "",
                    "parent_doc_id": "",
                    "chunk_type": f"page_{i+1}",
                    "source_hash": file_hash,
                    "metadata_json": json.dumps(metadata or {}),
                }
                chunks.append(chunk)
            except Exception as e:
                canvas.warning(f"Error processing page {i+1}: {e}")
        
        # Add chunks to database
        from i2c.db_utils import add_or_update_chunks, TABLE_KNOWLEDGE_BASE, SCHEMA_KNOWLEDGE_BASE
        
        add_or_update_chunks(
            db=db,
            table_name=TABLE_KNOWLEDGE_BASE,
            schema=SCHEMA_KNOWLEDGE_BASE,
            identifier_field="source",
            identifier_value=str(file_path),
            chunks=chunks
        )
        
        canvas.success(f"Added {len(chunks)} chunks from PDF: {file_path}")
        return True
    except Exception as e:
        canvas.error(f"Error processing PDF: {e}")
        import traceback
        canvas.error(traceback.format_exc())
        return False

def process_text_file(file_path, document_type, knowledge_space, embed_model, db, metadata=None):
    """Process a text file into knowledge chunks with better error handling"""
    try:
        canvas.info(f"Processing text file: {file_path}")
        
        # Calculate file hash
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
                canvas.info(f"File hash calculated: {file_hash[:8]}...")
        except Exception as e:
            canvas.error(f"Error calculating file hash: {e}")
            file_hash = "unknown_hash"
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                canvas.info(f"File content read: {len(content)} characters")
                
                if not content or len(content) < 10:
                    canvas.warning(f"File content too short or empty: {len(content)} chars")
                    return False
        except Exception as e:
            canvas.error(f"Error reading file content: {e}")
            return False
        
        # Create vector
        try:
            vector = embed_model.get_embedding(content)
            canvas.info(f"Vector embedding created: {len(vector)} dimensions")
        except Exception as e:
            canvas.error(f"Error creating vector embedding: {e}")
            return False
        
        # Create chunk
        try:
            chunks = [{
                "source": str(file_path),
                "content": content,
                "vector": vector,
                "category": document_type,
                "last_updated": datetime.now().isoformat(),
                "knowledge_space": knowledge_space,
                "document_type": document_type,
                "framework": metadata.get("framework", "") if metadata else "",
                "version": metadata.get("version", "") if metadata else "",
                "parent_doc_id": "",
                "chunk_type": "text",
                "source_hash": file_hash,
                "metadata_json": json.dumps(metadata or {}),
            }]
            canvas.info(f"Chunk created successfully")
        except Exception as e:
            canvas.error(f"Error creating chunk: {e}")
            return False
        
        # Add chunks to database
        try:
            from i2c.db_utils import add_or_update_chunks, TABLE_KNOWLEDGE_BASE, SCHEMA_KNOWLEDGE_BASE
            
            add_or_update_chunks(
                db=db,
                table_name=TABLE_KNOWLEDGE_BASE,
                schema=SCHEMA_KNOWLEDGE_BASE,
                identifier_field="source",
                identifier_value=str(file_path),
                chunks=chunks
            )
            
            canvas.success(f"Added text file to knowledge base: {file_path}")
            return True
        except Exception as e:
            canvas.error(f"Error adding chunks to database: {e}")
            import traceback
            canvas.error(traceback.format_exc())
            return False
            
    except Exception as e:
        canvas.error(f"Error processing text file: {e}")
        import traceback
        canvas.error(traceback.format_exc())
        return False
    """Process a text file into knowledge chunks"""
    try:
        canvas.info(f"Processing text file: {file_path}")
        
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Create vector
        vector = embed_model.get_embedding(content)
        
        # Create chunk
        chunks = [{
            "source": str(file_path),
            "content": content,
            "vector": vector,
            "category": document_type,
            "last_updated": datetime.now().isoformat(),
            "knowledge_space": knowledge_space,
            "document_type": document_type,
            "framework": metadata.get("framework", "") if metadata else "",
            "version": metadata.get("version", "") if metadata else "",
            "parent_doc_id": "",
            "chunk_type": "text",
            "source_hash": file_hash,
            "metadata_json": json.dumps(metadata or {}),
        }]
        
        # Add chunks to database
        from i2c.db_utils import add_or_update_chunks, TABLE_KNOWLEDGE_BASE, SCHEMA_KNOWLEDGE_BASE
        
        add_or_update_chunks(
            db=db,
            table_name=TABLE_KNOWLEDGE_BASE,
            schema=SCHEMA_KNOWLEDGE_BASE,
            identifier_field="source",
            identifier_value=str(file_path),
            chunks=chunks
        )
        
        canvas.success(f"Added text file to knowledge base: {file_path}")
        return True
    except Exception as e:
        canvas.error(f"Error processing text file: {e}")
        import traceback
        canvas.error(traceback.format_exc())
        return False