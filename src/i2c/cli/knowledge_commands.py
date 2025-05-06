# from i2c/cli/knowledge_commands.py
"""CLI commands for knowledge base management"""
from pathlib import Path
from i2c.agents.knowledge.knowledge_ingestor import KnowledgeIngestorAgent
from i2c.cli.controller import canvas, budget_manager

def add_knowledge_command(project_path: Path):
    """CLI command to add documentation to knowledge base"""
    
    canvas.info("=== Add Documentation to Knowledge Base ===")
    
    # Get document path
    doc_path = canvas.get_user_input("Enter path to documentation file: ").strip()
    doc_path = Path(doc_path)
    
    if not doc_path.exists():
        canvas.error(f"File not found: {doc_path}")
        return
    
    # Get document type
    doc_types = ["api_documentation", "tutorial", "example_code", "best_practices"]
    canvas.info("Document types:")
    for i, dtype in enumerate(doc_types, 1):
        canvas.info(f"  {i}. {dtype}")
    
    choice = canvas.get_user_input("Select document type (1-4): ").strip()
    doc_type = doc_types[int(choice) - 1] if choice.isdigit() else "api_documentation"
    
    # Get metadata
    framework = canvas.get_user_input("Framework (e.g., react, django, leave blank if N/A): ").strip()
    version = canvas.get_user_input("Version (e.g., 18.0.0, leave blank if N/A): ").strip()
    
    # Ingest document
    canvas.info(f"Ingesting {doc_path.name}...")
    
    ingestor = KnowledgeIngestorAgent(
        budget_manager=budget_manager,
        knowledge_space=project_path.name
    )
    
    success, result = ingestor.execute(
        document_path=doc_path,
        document_type=doc_type,
        metadata={
            "framework": framework,
            "version": version
        }
    )
    
    if success:
        canvas.success(f"Successfully added {doc_path.name} to knowledge base")
        canvas.info(f"Chunks created: {result.get('chunks_created', 0)}")
    else:
        canvas.error("Failed to add documentation")
        # Print the error + full traceback if available
        for line in result.get("traceback", result.get("error", "No details")).splitlines():
            canvas.error(line)
            
