import pytest
from pathlib import Path
import asyncio
import json
import tempfile
from i2c.agents.code_orchestration_agent import CodeOrchestrationAgent
from i2c.agents.architecture.architecture_understanding_agent import architecture_agent

@pytest.mark.integration
def test_architectural_analysis_integration(tmp_path):
    """Test that architectural analysis is properly integrated into orchestration"""
    
    # --- Setup: Create a project with clear architectural patterns ---
    # Frontend structure
    frontend_dir = tmp_path / "client" / "src"
    frontend_dir.mkdir(parents=True)
    
    (frontend_dir / "App.js").write_text("""
import React from 'react';
import SnippetList from './components/SnippetList';

function App() {
  return (
    <div className="App">
      <h1>Code Snippet Manager</h1>
      <SnippetList />
    </div>
  );
}

export default App;
""")
    
    (frontend_dir / "components").mkdir()
    (frontend_dir / "components" / "SnippetList.js").write_text("""
import React, { useState, useEffect } from 'react';

const SnippetList = () => {
  const [snippets, setSnippets] = useState([]);
  
  useEffect(() => {
    fetch('/api/snippets')
      .then(res => res.json())
      .then(data => setSnippets(data));
  }, []);
  
  return (
    <div>
      {snippets.map(snippet => (
        <div key={snippet.id}>{snippet.title}</div>
      ))}
    </div>
  );
};

export default SnippetList;
""")
    
    # Backend structure
    backend_dir = tmp_path / "server" / "app"
    backend_dir.mkdir(parents=True)
    
    (backend_dir / "main.py").write_text("""
from flask import Flask, jsonify
from routes.snippet_routes import snippet_bp

app = Flask(__name__)
app.register_blueprint(snippet_bp, url_prefix='/api')

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True)
""")
    
    (backend_dir / "routes").mkdir()
    (backend_dir / "routes" / "snippet_routes.py").write_text("""
from flask import Blueprint, jsonify
from services.snippet_service import SnippetService

snippet_bp = Blueprint('snippets', __name__)
snippet_service = SnippetService()

@snippet_bp.route('/snippets', methods=['GET'])
def get_snippets():
    snippets = snippet_service.get_all_snippets()
    return jsonify(snippets)
""")
    
    (backend_dir / "services").mkdir()
    (backend_dir / "services" / "snippet_service.py").write_text("""
class SnippetService:
    def __init__(self):
        self.snippets = []
    
    def get_all_snippets(self):
        return self.snippets
    
    def create_snippet(self, title, content, language):
        snippet = {
            'id': len(self.snippets) + 1,
            'title': title,
            'content': content,
            'language': language
        }
        self.snippets.append(snippet)
        return snippet
""")
    
    print(f"📁 Created project structure at: {tmp_path}")
    
    # --- Test architectural analysis ---
    session_state = {"project_path": str(tmp_path)}
    agent = CodeOrchestrationAgent(session_state=session_state)
    
    async def test_analysis():
        # This should trigger architectural analysis
        analysis = await agent._analyze_project_context(
            tmp_path, 
            "Add user authentication and authorization to the snippet manager"
        )
        return analysis
    
    loop = asyncio.get_event_loop()
    analysis_result = loop.run_until_complete(test_analysis())
    
    # --- Validate architectural understanding ---
    print("\n" + "="*60)
    print("ARCHITECTURAL ANALYSIS RESULTS")
    print("="*60)
    
    assert "architectural_context" in analysis_result
    arch_context = analysis_result["architectural_context"]
    
    print(f"🏗️ Architecture Pattern: {arch_context.get('architecture_pattern')}")
    print(f"🎯 System Type: {arch_context.get('system_type')}")
    
    # Should detect fullstack web architecture
    assert arch_context.get("system_type") in ["web_app", "fullstack_web"]
    assert arch_context.get("architecture_pattern") in ["fullstack_web", "layered_monolith"]
    
    # Should identify modules
    modules = arch_context.get("modules", {})
    print(f"📦 Modules found: {list(modules.keys())}")
    assert len(modules) > 0, "Should identify architectural modules"
    
    # Should have UI and API modules
    module_types = [module.get("boundary_type") for module in modules.values()]
    print(f"🔍 Module types: {module_types}")
    
    # Should have file organization rules
    file_rules = arch_context.get("file_organization_rules", {})
    print(f"📋 File organization rules: {list(file_rules.keys())}")
    assert len(file_rules) > 0, "Should have file organization rules"
    
    # Should identify constraints
    constraints = arch_context.get("constraints", [])
    print(f"⚖️ Architectural constraints: {len(constraints)} found")
    
    return analysis_result


@pytest.mark.integration
def test_architectural_planning_integration(tmp_path):
    """Test that modification planning uses architectural intelligence"""
    
    # Create simple backend project
    (tmp_path / "app.py").write_text("""
from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello World'
""")
    
    (tmp_path / "models.py").write_text("""
class User:
    def __init__(self, username):
        self.username = username
""")
    
    session_state = {"project_path": str(tmp_path), "language": "python"}
    agent = CodeOrchestrationAgent(session_state=session_state)
    
    async def test_planning():
        # First analyze the project architecture
        analysis = await agent._analyze_project_context(
            tmp_path, 
            "Add API endpoints for user management with proper authentication"
        )
        
        # Then create modification plan using architectural intelligence
        plan = await agent._create_modification_plan(
            task="Add API endpoints for user management with proper authentication",
            constraints=["Follow REST conventions", "Add input validation"],
            analysis=analysis
        )
        
        return analysis, plan
    
    loop = asyncio.get_event_loop()
    analysis_result, plan_result = loop.run_until_complete(test_planning())
    
    print("\n" + "="*60)
    print("ARCHITECTURAL PLANNING RESULTS")
    print("="*60)
    
    # Check architectural guidance in plan
    assert "architectural_guidance" in plan_result
    arch_guidance = plan_result["architectural_guidance"]
    
    print(f"🎯 Architecture Pattern: {arch_guidance.get('architecture_pattern')}")
    print(f"📁 File Organization Rules: {arch_guidance.get('file_organization_rules')}")
    print(f"🔗 Integration Patterns: {arch_guidance.get('integration_patterns')}")
    
    # Check modification steps
    steps = plan_result.get("steps", [])
    print(f"📋 Generated {len(steps)} modification steps")
    
    for step in steps:
        file_path = step.get("file", "")
        what = step.get("what", "")
        print(f"   - {file_path}: {what}")
        
        # Check if step has architectural context
        if "architectural_context" in step:
            arch_ctx = step["architectural_context"]
            relevant_modules = arch_ctx.get("relevant_modules", [])
            if relevant_modules:
                print(f"     Modules: {[m['name'] for m in relevant_modules]}")
    
    return plan_result


@pytest.mark.integration
def test_architectural_validation():
    """Test architectural validation of file paths and content"""
    
    # Test the architecture agent directly
    objective = "Build a React frontend with Flask API backend for a task management system"
    
    # Simulate existing files
    existing_files = [
        "frontend/src/App.js",
        "frontend/src/components/TaskList.js", 
        "backend/app.py",
        "backend/models/task.py",
        "backend/routes/task_routes.py"
    ]
    
    # Sample content for analysis
    content_samples = {
        "frontend/src/App.js": """
import React from 'react';
import TaskList from './components/TaskList';

function App() {
  return <div><TaskList /></div>;
}

export default App;
""",
        "backend/app.py": """
from flask import Flask
from routes.task_routes import task_bp

app = Flask(__name__)
app.register_blueprint(task_bp)
""",
        "backend/models/task.py": """
class Task:
    def __init__(self, title, description):
        self.title = title
        self.description = description
"""
    }
    
    print("🔍 Testing direct architectural analysis...")
    
    # Analyze architecture
    structural_context = architecture_agent.analyze_system_architecture(
        objective=objective,
        existing_files=existing_files,
        content_samples=content_samples
    )
    
    print(f"🏗️ Detected Pattern: {structural_context.architecture_pattern.value}")
    print(f"🎯 System Type: {structural_context.system_type}")
    print(f"📦 Modules: {list(structural_context.modules.keys())}")
    print(f"📋 File Rules: {list(structural_context.file_organization_rules.keys())}")
    
    # Test file validation
    test_cases = [
        ("frontend/src/NewComponent.js", "const NewComponent = () => <div>Hello</div>;"),
        ("backend/api/new_endpoint.py", "@app.route('/api/data')\ndef get_data(): return {}"),
        ("wrong/location/component.js", "const Component = () => <div>Wrong Place</div>;")
    ]
    
    print("\n🧪 Testing file validation:")
    for file_path, content in test_cases:
        validation = architecture_agent.validate_file_against_architecture(
            file_path, content, structural_context
        )
        
        status = "✅" if validation["is_valid"] else "❌"
        print(f"{status} {file_path}")
        
        if validation["violations"]:
            for violation in validation["violations"]:
                print(f"     - {violation}")
        
        if validation["correct_location"] != file_path:
            print(f"     → Suggested: {validation['correct_location']}")
    
    assert structural_context.architecture_pattern != None
    assert len(structural_context.modules) > 0
    assert len(structural_context.file_organization_rules) > 0


if __name__ == "__main__":
    print("Testing architectural intelligence integration...")
    pytest.main(["-xvs", __file__])