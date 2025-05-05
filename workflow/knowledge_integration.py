# workflow/knowledge_integration.py
"""Integration points for Knowledge Base with main workflow"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import json

# Import CLI controller for logging
from cli.controller import canvas

# Import database utilities
from db_utils import get_db_connection, get_or_create_table_with_migration, SCHEMA_KNOWLEDGE_BASE_V2

# Import budget manager
from agents.budget_manager import BudgetManagerAgent

# Import embedder
from agents.modification_team.context_utils import _embedding_model as embed_model

# Import knowledge agents (these will need to be created)
from agents.knowledge.knowledge_retriever import KnowledgeRetrieverAgent
from agents.knowledge.knowledge_ingestor import KnowledgeIngestorAgent

def detect_framework(project_path: Path) -> Optional[str]:
    """Detect the framework used in a project by analyzing files."""
    framework_indicators = {
        'react': ['package.json', 'src/App.js', 'src/App.tsx', 'src/index.js'],
        'django': ['manage.py', 'settings.py', 'wsgi.py'],
        'flask': ['app.py', 'wsgi.py', 'requirements.txt'],
        'vue': ['vue.config.js', 'src/main.js', 'src/App.vue'],
        'angular': ['angular.json', 'src/main.ts', 'src/app/app.component.ts'],
        'express': ['app.js', 'server.js', 'routes/'],
        'fastapi': ['main.py', 'requirements.txt'],
        'nextjs': ['next.config.js', 'pages/', 'app/']
    }
    
    detected_frameworks = []
    
    for framework, indicators in framework_indicators.items():
        matches = 0
        for indicator in indicators:
            if (project_path / indicator).exists():
                matches += 1
        if matches > 0:
            detected_frameworks.append((framework, matches))
    
    if detected_frameworks:
        # Return the framework with most matches
        detected_frameworks.sort(key=lambda x: x[1], reverse=True)
        return detected_frameworks[0][0]
    
    # Check package.json for framework detection
    package_json = project_path / 'package.json'
    if package_json.exists():
        try:
            with open(package_json) as f:
                data = json.load(f)
                deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                
                if 'react' in deps:
                    return 'react'
                elif 'vue' in deps:
                    return 'vue'
                elif '@angular/core' in deps:
                    return 'angular'
                elif 'express' in deps:
                    return 'express'
        except:
            pass
    
    # Check requirements.txt for Python frameworks
    requirements = project_path / 'requirements.txt'
    if requirements.exists():
        try:
            with open(requirements) as f:
                content = f.read().lower()
                if 'django' in content:
                    return 'django'
                elif 'flask' in content:
                    return 'flask'
                elif 'fastapi' in content:
                    return 'fastapi'
        except:
            pass
    
    return None

def format_knowledge_results(results: List[Dict[str, Any]]) -> str:
    """Format knowledge retrieval results for LLM consumption."""
    if not results:
        return "No relevant knowledge found."
    
    formatted = ["Retrieved Knowledge:"]
    for i, result in enumerate(results, 1):
        formatted.append(f"\n--- Knowledge Item {i} ---")
        formatted.append(f"Source: {result.get('source', 'Unknown')}")
        if 'framework' in result:
            formatted.append(f"Framework: {result['framework']}")
        if 'version' in result:
            formatted.append(f"Version: {result['version']}")
        if 'document_type' in result:
            formatted.append(f"Type: {result['document_type']}")
        formatted.append(f"Content: {result.get('content', '')}")
        formatted.append("-------------------")
    
    return "\n".join(formatted)

def enhance_modification_workflow_with_knowledge(
    modification_plan: List[Dict],
    project_path: Path,
    knowledge_space: str,
    budget_manager: BudgetManagerAgent
) -> List[Dict]:
    """Enhance modification plan with knowledge base context."""
    
    # Initialize database connection
    db = get_db_connection()
    if not db:
        canvas.warning("Knowledge base unavailable - proceeding without enhancement")
        return modification_plan
    
    # Create vector database instance
    from agents.knowledge.knowledge_manager import EnhancedLanceDb
    vector_db = EnhancedLanceDb(
        knowledge_space=knowledge_space,
        table_name="knowledge_base",
        uri=str(Path(db.uri).parent),
        search_type="hybrid",
        embedder=embed_model
    )
    
    # Initialize knowledge retriever
    knowledge_retriever = KnowledgeRetrieverAgent(
        budget_manager=budget_manager,
        vector_db=vector_db,
        embed_model=embed_model
    )
    
    # Detect project framework
    framework = detect_framework(project_path)
    
    enhanced_plan = []
    
    for step in modification_plan:
        # Create query from step information
        query_parts = []
        if 'file' in step:
            query_parts.append(f"file: {step['file']}")
        if 'what' in step:
            query_parts.append(step['what'])
        if 'how' in step:
            query_parts.append(step['how'])
        
        query = " ".join(query_parts)
        
        # Retrieve relevant knowledge
        try:
            success, result = knowledge_retriever.execute(
                query=query,
                filters={
                    "knowledge_space": knowledge_space,
                    "framework": framework
                } if framework else {"knowledge_space": knowledge_space},
                max_results=3
            )
            
            if success and result.get('results'):
                step['knowledge_context'] = format_knowledge_results(result['results'])
                canvas.info(f"Enhanced step with {len(result['results'])} knowledge items")
            else:
                step['knowledge_context'] = None
        except Exception as e:
            canvas.warning(f"Failed to retrieve knowledge for step: {e}")
            step['knowledge_context'] = None
        
        enhanced_plan.append(step)
    
    return enhanced_plan

def integrate_knowledge_with_code_modifier(
    code_modifier_agent,
    knowledge_retriever_agent: KnowledgeRetrieverAgent
):
    """Integrate knowledge retriever with code modifier agent."""
    # Store reference to knowledge retriever in code modifier
    code_modifier_agent.knowledge_retriever = knowledge_retriever_agent
    
    # Patch the modify_code method to use knowledge
    original_modify_code = code_modifier_agent.modify_code
    
    def enhanced_modify_code(modification_step: Dict, project_path: Path, 
                           retrieved_context: Optional[str] = None) -> Optional[str]:
        """Enhanced modify_code that includes knowledge base context."""
        # Retrieve knowledge context
        knowledge_context = None
        if hasattr(code_modifier_agent, 'knowledge_retriever') and code_modifier_agent.knowledge_retriever:
            try:
                # Create query from modification step
                query = f"{modification_step.get('what', '')} {modification_step.get('how', '')}"
                
                # Detect framework for filtering
                framework = detect_framework(project_path)
                
                # Retrieve knowledge
                success, result = code_modifier_agent.knowledge_retriever.execute(
                    query=query,
                    filters={
                        "framework": framework,
                        "language": detect_language(modification_step.get('file', ''))
                    } if framework else {},
                    max_results=3
                )
                
                if success and result.get('results'):
                    knowledge_context = format_knowledge_results(result['results'])
            except Exception as e:
                canvas.warning(f"Failed to retrieve knowledge context: {e}")
        
        # Call original method with additional context
        if knowledge_context:
            # Append knowledge context to existing context
            if retrieved_context:
                combined_context = f"{retrieved_context}\n\n{knowledge_context}"
            else:
                combined_context = knowledge_context
            
            return original_modify_code(modification_step, project_path, combined_context)
        else:
            return original_modify_code(modification_step, project_path, retrieved_context)
    
    # Replace the method
    code_modifier_agent.modify_code = enhanced_modify_code

def detect_language(file_path: str) -> Optional[str]:
    """Detect programming language from file extension."""
    if not file_path:
        return None
        
    ext_to_lang = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.cpp': 'cpp',
        '.c': 'c',
        '.cs': 'csharp',
        '.php': 'php',
        '.rb': 'ruby',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        '.sql': 'sql',
        '.sh': 'bash',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.json': 'json',
        '.xml': 'xml',
        '.md': 'markdown'
    }
    
    ext = Path(file_path).suffix.lower()
    return ext_to_lang.get(ext)

# Usage example in workflow
def integrate_knowledge_into_workflow():
    """Example of how to integrate knowledge base into the main workflow."""
    from agents.modification_team.code_modifier import code_modifier_agent
    from agents.budget_manager import BudgetManagerAgent
    
    # Initialize budget manager
    budget_manager = BudgetManagerAgent(session_budget=1.0)
    
    # Initialize database
    db = get_db_connection()
    if not db:
        canvas.error("Failed to initialize database for knowledge integration")
        return
    
    # Create knowledge retriever
    knowledge_retriever = KnowledgeRetrieverAgent(
        budget_manager=budget_manager,
        vector_db=db,
        embed_model=embed_model
    )
    
    # Integrate with code modifier
    integrate_knowledge_with_code_modifier(code_modifier_agent, knowledge_retriever)
    
    canvas.success("Knowledge base integrated with code modification workflow")