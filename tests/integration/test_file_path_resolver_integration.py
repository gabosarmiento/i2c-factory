import pytest
from pathlib import Path
import tempfile
from i2c.workflow.modification.file_operations import write_files_to_disk

def test_file_path_resolver_integration_fullstack():
    """Test file path resolver integration with fullstack app structure"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Create problematic code map (like from the scenario)
        problematic_code_map = {
            # These should be resolved to proper paths
            "frontend": """import React from 'react';
import './App.css';

function App() {
  return (
    <div className="App">
      <h1>Code Snippet Generator</h1>
    </div>
  );
}

export default App;""",
            
            "backend": """from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True)""",
            
            # These should work normally
            "README.md": "# Project Documentation",
            "main.py": "def main():\n    print('Hello World')",
            
            # Nested paths should work
            "docs/api.md": "# API Documentation",
        }
        
        print("🧪 Testing file path resolver integration...")
        print(f"📁 Original code map: {list(problematic_code_map.keys())}")
        
        # Write files with intelligent path resolution
        write_files_to_disk(problematic_code_map, project_path)
        
        # Check what files were actually created
        created_files = []
        for file_path in project_path.rglob("*"):
            if file_path.is_file():
                created_files.append(str(file_path.relative_to(project_path)))
        
        print(f"📄 Created files: {created_files}")
        
        # Verify problematic paths were resolved
        assert len(created_files) > 0, "Should create some files"
        
        # Check that 'frontend' is not a file (should be resolved to proper structure)
        frontend_file = project_path / "frontend"
        if frontend_file.exists():
            assert frontend_file.is_dir() or not frontend_file.exists(), "Frontend should not be a plain file"
        
        # Check for properly structured frontend files
        frontend_files = [f for f in created_files if f.startswith("frontend/")]
        if frontend_files:
            print(f"✅ Frontend files properly structured: {frontend_files}")
        
        # Check for properly structured backend files  
        backend_files = [f for f in created_files if f.startswith("backend/")]
        if backend_files:
            print(f"✅ Backend files properly structured: {backend_files}")
        
        # Verify normal files still work
        assert "README.md" in created_files, "Normal files should still be created"
        assert "main.py" in created_files, "Normal files should still be created"
        
        # Check content is preserved
        readme_content = (project_path / "README.md").read_text()
        assert "Project Documentation" in readme_content
        
        return created_files


def test_file_path_resolver_with_existing_structure():
    """Test resolver respects existing project structure"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Create existing structure
        (project_path / "client").mkdir()
        (project_path / "client" / "src").mkdir(parents=True)
        (project_path / "server").mkdir()
        (project_path / "server" / "api").mkdir(parents=True)
        
        # Create existing files to establish structure
        (project_path / "client" / "src" / "index.js").write_text("// Existing frontend")
        (project_path / "server" / "api" / "routes.py").write_text("# Existing backend")
        
        # New problematic code map
        code_map = {
            "frontend": "const NewComponent = () => <div>New</div>;",
            "backend": "def new_endpoint(): return 'data'",
            "api": "from flask import Blueprint\napi = Blueprint('api', __name__)"
        }
        
        print("🏗️ Testing with existing project structure...")
        write_files_to_disk(code_map, project_path)
        
        # Check files were created
        created_files = []
        for file_path in project_path.rglob("*"):
            if file_path.is_file():
                created_files.append(str(file_path.relative_to(project_path)))
        
        print(f"📄 All files: {created_files}")
        
        # Should respect existing structure and place files appropriately
        assert len(created_files) >= 5, "Should have original + new files"
        
        # Original files should still exist
        assert "client/src/index.js" in created_files
        assert "server/api/routes.py" in created_files


def test_path_resolver_error_handling():
    """Test that path resolver handles errors gracefully"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Edge case code map
        edge_case_map = {
            "": "empty key content",  # Empty key
            "just_extension.": "content with just dot",
            "no_extension_no_content": "",
            "normal_file.py": "def normal(): pass"
        }
        
        print("🔧 Testing edge cases and error handling...")
        
        # Should not crash
        write_files_to_disk(edge_case_map, project_path)
        
        # Check some files were created
        created_files = []
        for file_path in project_path.rglob("*"):
            if file_path.is_file():
                created_files.append(str(file_path.relative_to(project_path)))
        
        print(f"📄 Created files from edge cases: {created_files}")
        
        # At least normal file should be created
        assert "normal_file.py" in created_files


if __name__ == "__main__":
    print("Testing file path resolver integration...")
    test_file_path_resolver_integration_fullstack()
    print("\n" + "="*50)
    test_file_path_resolver_with_existing_structure()
    print("\n" + "="*50)
    test_path_resolver_error_handling()
    print("\n✅ All file path resolver integration tests completed!")