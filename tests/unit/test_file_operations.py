import pytest
from pathlib import Path
import tempfile
import shutil
from i2c.workflow.modification.file_operations import write_files_to_disk, delete_files

def test_write_files_to_disk_success():
    """Test successful file writing with nested directories"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        destination = Path(temp_dir)
        
        code_map = {
            "main.py": "def main():\n    print('Hello World')\n",
            "backend/app/models/__init__.py": "# Models package\n",
            "backend/app/models/user.py": "class User:\n    pass\n",
            "frontend/src/components/App.tsx": "export const App = () => <div>Hello</div>;\n",
            "docs/README.md": "# Project Documentation\n",
        }
        
        # Write files
        write_files_to_disk(code_map, destination)
        
        # Verify all files were created
        for file_path, expected_content in code_map.items():
            full_path = destination / file_path
            assert full_path.exists(), f"File should exist: {file_path}"
            assert full_path.is_file(), f"Should be a file: {file_path}"
            
            actual_content = full_path.read_text(encoding='utf-8')
            assert actual_content == expected_content, f"Content mismatch in {file_path}"
        
        # Verify directory structure was created
        assert (destination / "backend" / "app" / "models").exists()
        assert (destination / "frontend" / "src" / "components").exists()
        assert (destination / "docs").exists()


def test_write_files_to_disk_empty_content():
    """Test handling of empty or minimal content"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        destination = Path(temp_dir)
        
        # Create existing file first
        existing_file = destination / "existing.py"
        existing_file.parent.mkdir(parents=True, exist_ok=True)
        existing_file.write_text("# Existing substantial content\ndef important_function():\n    pass\n")
        
        code_map = {
            "new_empty.py": "",  # Empty file - should be written
            "existing.py": "  ",  # Nearly empty - should be skipped for existing file
            "normal.py": "def hello():\n    return 'Hello'\n"  # Normal content
        }
        
        write_files_to_disk(code_map, destination)
        
        # Empty new file should be created
        assert (destination / "new_empty.py").exists()
        
        # Existing file should be preserved (not overwritten with empty content)
        existing_content = (destination / "existing.py").read_text()
        assert "important_function" in existing_content
        
        # Normal file should be written
        normal_content = (destination / "normal.py").read_text()
        assert "def hello():" in normal_content


def test_write_files_to_disk_diff_content():
    """Test handling of diff-formatted content"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        destination = Path(temp_dir)
        
        # Diff format content
        diff_content = """# === Diff for calculator.py ===
--- calculator.py
+++ calculator.py
@@ -1,3 +1,6 @@
+def add(a, b):
+    return a + b
+
 def subtract(a, b):
     return a - b
"""
        
        code_map = {
            "calculator.py": diff_content
        }
        
        write_files_to_disk(code_map, destination)
        
        # Verify diff was processed and clean content was written
        calc_file = destination / "calculator.py"
        assert calc_file.exists()
        
        content = calc_file.read_text()
        # Should contain the added lines without diff markers
        assert "def add(a, b):" in content
        assert "def subtract(a, b):" in content
        # Should not contain diff markers
        assert "+++" not in content
        assert "---" not in content
        assert "@@ -1,3 +1,6 @@" not in content

def test_write_files_to_disk_permission_error(tmp_path):
    """Test handling of permission errors"""

    # Create a read-only directory (with execute so we can check inside)
    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    readonly_dir.chmod(0o555)  # Read-only + executable (no write)

    code_map = {
        "test_file.py": "def test():\n    pass\n"
    }

    write_files_to_disk(code_map, readonly_dir)

    # Now this line won't crash and will correctly return False
    assert not (readonly_dir / "test_file.py").exists()

def test_delete_files_success():
    """Test successful file deletion"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Create test files
        files_to_create = [
            "file1.py",
            "subdir/file2.js", 
            "another/deep/file3.txt"
        ]
        
        created_files = []
        for file_rel in files_to_create:
            file_path = project_path / file_rel
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(f"Content of {file_rel}")
            created_files.append(file_path)
        
        # Verify files exist
        for file_path in created_files:
            assert file_path.exists()
        
        # Delete files
        delete_files(created_files, project_path)
        
        # Verify files were deleted
        for file_path in created_files:
            assert not file_path.exists()


def test_delete_files_nonexistent():
    """Test deletion of non-existent files"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        nonexistent_files = [
            project_path / "does_not_exist.py",
            project_path / "also/missing.js"
        ]
        
        # Should handle gracefully without errors
        delete_files(nonexistent_files, project_path)


def test_delete_files_mixed_existence():
    """Test deletion with mix of existing and non-existent files"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Create one file, leave another non-existent
        existing_file = project_path / "exists.py"
        existing_file.write_text("def exists(): pass")
        nonexistent_file = project_path / "missing.py"
        
        files_to_delete = [existing_file, nonexistent_file]
        
        # Verify initial state
        assert existing_file.exists()
        assert not nonexistent_file.exists()
        
        # Delete files
        delete_files(files_to_delete, project_path)
        
        # Verify existing file was deleted, no error for non-existent
        assert not existing_file.exists()
        assert not nonexistent_file.exists()


def test_write_files_to_disk_unicode_content():
    """Test handling of unicode and special characters"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        destination = Path(temp_dir)
        
        code_map = {
            "unicode.py": "# -*- coding: utf-8 -*-\n# Tëst ünïcödë: 你好世界\ndef greet():\n    return 'Hello 🌍'\n",
            "json_data.json": '{"name": "José", "emoji": "🚀", "chinese": "测试"}\n'
        }
        
        write_files_to_disk(code_map, destination)
        
        # Verify unicode content was written correctly
        for file_path, expected_content in code_map.items():
            full_path = destination / file_path
            assert full_path.exists()
            
            actual_content = full_path.read_text(encoding='utf-8')
            assert actual_content == expected_content


if __name__ == "__main__":
    print("Running file operations unit tests...")
    pytest.main(["-xvs", __file__])