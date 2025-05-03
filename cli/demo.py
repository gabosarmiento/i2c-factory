# cli/demo.py
"""Demo script to showcase the Feature Pipeline capabilities"""
import sys
import argparse
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from typing import List
import time

from models.user_story import UserStory, AcceptanceCriteria, StoryPriority, StoryStatus
from story_manager import StoryManager
from workflow.feature_pipeline import FeaturePipeline
from agents.budget_manager import BudgetManagerAgent
from agents.knowledge.knowledge_manager import ExternalKnowledgeManager
from cli.rich_output import rich_output
from rich.panel import Panel
from db_utils import get_db_connection
import os


def create_sample_stories() -> List[UserStory]:
    """Create sample user stories for demo"""
    stories = [
        UserStory(
            title="User Authentication System",
            description="Implement a secure user authentication system with JWT tokens",
            as_a="system administrator",
            i_want="users to be able to securely log in and register",
            so_that="we can protect user data and track user sessions",
            acceptance_criteria=[
                AcceptanceCriteria(
                    description="Users can register with email and password",
                    verification_steps=["Test registration API", "Verify user creation in database"]
                ),
                AcceptanceCriteria(
                    description="Users can log in and receive JWT token",
                    verification_steps=["Test login API", "Verify JWT token generation"]
                ),
                AcceptanceCriteria(
                    description="Passwords are securely hashed",
                    verification_steps=["Check password hashing implementation", "Verify no plain text passwords"]
                )
            ],
            priority=StoryPriority.HIGH,
            tags=["security", "authentication"],
            estimated_effort=8
        ),
        
        UserStory(
            title="Data Export Feature",
            description="Allow users to export their data in multiple formats",
            as_a="registered user",
            i_want="to export my data in CSV and JSON formats",
            so_that="I can backup my data or use it in other applications",
            acceptance_criteria=[
                AcceptanceCriteria(
                    description="Export button available on user dashboard",
                    verification_steps=["Check UI for export button", "Test button functionality"]
                ),
                AcceptanceCriteria(
                    description="Data exported correctly in CSV format",
                    verification_steps=["Export data as CSV", "Verify CSV structure and content"]
                ),
                AcceptanceCriteria(
                    description="Data exported correctly in JSON format",
                    verification_steps=["Export data as JSON", "Verify JSON structure and content"]
                )
            ],
            priority=StoryPriority.MEDIUM,
            tags=["export", "user-data"],
            estimated_effort=5
        ),
        
        UserStory(
            title="API Rate Limiting",
            description="Implement rate limiting for API endpoints to prevent abuse",
            as_a="API developer",
            i_want="to limit the number of requests per user per hour",
            so_that="we can prevent API abuse and ensure fair usage",
            acceptance_criteria=[
                AcceptanceCriteria(
                    description="Rate limiting middleware implemented",
                    verification_steps=["Check middleware implementation", "Test with various request rates"]
                ),
                AcceptanceCriteria(
                    description="Configurable rate limits per endpoint",
                    verification_steps=["Test different rate limits", "Verify configuration system"]
                ),
                AcceptanceCriteria(
                    description="Proper error responses when rate limit exceeded",
                    verification_steps=["Test rate limit exceeded scenario", "Verify error response format"]
                )
            ],
            priority=StoryPriority.HIGH,
            tags=["api", "security", "performance"],
            estimated_effort=6
        )
    ]
    
    return stories


def ingest_sample_documentation(knowledge_manager: ExternalKnowledgeManager):
    """Ingest sample documentation for demo"""
    docs = [
        {
            "source": "auth_best_practices.md",
            "content": """
# Authentication Best Practices

1. **Password Hashing**: Always use strong hashing algorithms like bcrypt or Argon2
2. **JWT Tokens**: Use short expiration times and implement refresh tokens
3. **Rate Limiting**: Implement rate limiting to prevent brute force attacks
4. **Input Validation**: Validate all user inputs to prevent injection attacks
5. **HTTPS**: Always use HTTPS for authentication endpoints
6. **Error Messages**: Don't reveal whether an email exists during login failures
            """
        },
        {
            "source": "api_design_guidelines.md",
            "content": """
# API Design Guidelines

1. **RESTful Principles**: Follow REST conventions for resource naming
2. **Versioning**: Use URL versioning (e.g., /api/v1/)
3. **Error Handling**: Use standard HTTP status codes and consistent error format
4. **Documentation**: Provide OpenAPI/Swagger documentation
5. **Rate Limiting**: Implement rate limiting with clear headers
6. **Security**: Use authentication for sensitive endpoints
            """
        },
        {
            "source": "data_export_patterns.md",
            "content": """
# Data Export Patterns

1. **Format Support**: Support multiple formats (CSV, JSON, XML)
2. **Streaming**: Use streaming for large datasets
3. **Compression**: Offer compressed downloads for large exports
4. **Progress Tracking**: Show progress for long-running exports
5. **Error Recovery**: Allow resuming interrupted exports
6. **Security**: Validate user permissions before export
            """
        }
    ]
    
    for doc in docs:
        success = knowledge_manager.ingest_knowledge(
            source=doc["source"],
            content=doc["content"],
            metadata={"category": "documentation"}
        )
        if success:
            rich_output.print_success(f"Ingested documentation: {doc['source']}")
        else:
            rich_output.print_error(f"Failed to ingest: {doc['source']}")


def run_demo(project_path: Path, skip_setup: bool = False):
    """Run the Feature Pipeline demo"""
    rich_output.console.print(Panel(
        "[bold blue]i2c Factory Feature Pipeline Demo[/bold blue]\n\n"
        "This demo showcases the transformation of user stories into code features.",
        title="🏭 Feature Pipeline Demo",
        border_style="blue"
    ))
    
    # Initialize components
    db_connection = get_db_connection()
    if db_connection is None:
        rich_output.print_error("Failed to connect to database")
        return
    
    # Initialize embedding model
    try:
        from sentence_transformers import SentenceTransformer
        embed_model = SentenceTransformer(os.getenv('EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2'))
    except ImportError:
        rich_output.print_error("sentence-transformers not installed")
        return
    
    # Initialize managers
    budget_manager = BudgetManagerAgent(session_budget=5.0)  # $5 budget for demo
    knowledge_manager = ExternalKnowledgeManager(embed_model=embed_model)
    story_manager = StoryManager(
        storage_path=project_path / "user_stories",
        knowledge_manager=knowledge_manager
    )
    
    if not skip_setup:
        # Setup phase
        rich_output.console.print("\n[bold]Setup Phase[/bold]")
        
        # Ingest documentation
        with rich_output.progress_bar("Ingesting documentation", total=3) as progress:
            task = progress.add_task("Ingesting...", total=3)
            ingest_sample_documentation(knowledge_manager)
            progress.update(task, advance=3)
        
        # Create sample stories
        rich_output.console.print("\n[bold]Creating Sample Stories[/bold]")
        stories = create_sample_stories()
        
        for story in stories:
            story_id = story_manager.create_story(story)
            rich_output.print_success(f"Created story: {story_id} - {story.title}")
            # Update status to READY for demo
            story_manager.update_story_status(story_id, StoryStatus.READY)
    
    # Initialize Feature Pipeline
    pipeline = FeaturePipeline(
        project_path=project_path,
        story_manager=story_manager,
        budget_manager=budget_manager,
        embed_model=embed_model,
        db_connection=db_connection
    )
    
    # Process stories
    rich_output.console.print("\n[bold]Processing User Stories[/bold]")
    ready_stories = story_manager.get_ready_stories()
    
    if not ready_stories:
        rich_output.print_warning("No ready stories found")
        return
    
    results = {}
    
    for story in ready_stories:
        rich_output.console.print(f"\n[bold]Processing: {story.title}[/bold]")
        rich_output.show_story_details(story.to_dict())
        
        # Simulate processing with visual feedback
        with rich_output.progress_bar(f"Processing {story.story_id}", total=4) as progress:
            task = progress.add_task("Processing...", total=4)
            
            # Phase 1: Context
            progress.update(task, advance=1, description="Gathering context...")
            time.sleep(1)  # Simulate work
            
            # Phase 2: Plan
            progress.update(task, advance=1, description="Generating plan...")
            time.sleep(1)
            
            # Phase 3: Implementation
            progress.update(task, advance=1, description="Implementing feature...")
            time.sleep(1)
            
            # Phase 4: Verification
            progress.update(task, advance=1, description="Verifying implementation...")
            time.sleep(1)
        
        # Actually process the story
        success, result = pipeline.process_story(story.story_id)
        results[story.story_id] = {"success": success, "result": result}
        
        # Show results
        if success:
            rich_output.print_success(f"Successfully processed story: {story.story_id}")
            
            # Show context
            if "context" in result:
                rich_output.show_context_gathering(result["context"])
            
            # Show plan
            if "plan" in result and "refined_plan" in result["plan"]:
                rich_output.show_plan(result["plan"]["refined_plan"])
            
            # Show best practices
            if "plan" in result and "best_practices" in result["plan"]:
                rich_output.show_best_practices(result["plan"]["best_practices"])
            
            # Show implementation
            if "implementation" in result and "code_map" in result["implementation"]:
                rich_output.show_code_implementation(result["implementation"]["code_map"])
            
            # Show resolution
            if "resolution" in result:
                rich_output.show_issue_resolution(result["resolution"])
                
        else:
            rich_output.print_error(f"Failed to process story: {result.get('error', 'Unknown error')}")
    
    # Show final summary
    rich_output.console.print("\n[bold]Pipeline Execution Summary[/bold]")
    rich_output.show_pipeline_summary(results)
    
    # Show budget usage
    tokens, cost = budget_manager.get_session_consumption()
    rich_output.console.print(Panel(
        f"[bold]Budget Usage[/bold]\n\n"
        f"Tokens: {tokens:,}\n"
        f"Cost: ${cost:.4f}\n"
        f"Remaining: ${5.0 - cost:.4f}",
        title="💰 Budget Report",
        border_style="yellow"
    ))


def main():
    parser = argparse.ArgumentParser(description="Feature Pipeline Demo")
    parser.add_argument(
        "--project-path",
        type=Path,
        default=Path("./demo_project"),
        help="Path to demo project directory"
    )
    parser.add_argument(
        "--skip-setup",
        action="store_true",
        help="Skip setup phase (use existing stories)"
    )
    
    args = parser.parse_args()
    args.project_path.mkdir(parents=True, exist_ok=True)
    
    run_demo(args.project_path, args.skip_setup)


if __name__ == "__main__":
    main()