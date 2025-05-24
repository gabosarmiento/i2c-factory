# Handles writing and deleting files for the modification cycle.

from pathlib import Path
from i2c.cli.controller import canvas # For logging

# In file_operations.py, modify the write_files_to_disk function:

# In file_operations.py or a related file

def post_process_code_map(code_map: dict) -> dict:
    """Fix common quality issues in the code map before writing to disk."""
    processed_map = code_map.copy()
    
    # Fix duplicate unittest.main() calls
    for file_path, content in processed_map.items():
        if file_path.startswith("test_") and file_path.endswith(".py"):
            # Check for duplicate unittest.main() calls
            if content.count("unittest.main()") > 1:
                canvas.warning(f"Fixing duplicate unittest.main() calls in {file_path}")
                
                # Split into lines, find all unittest.main() occurrences
                lines = content.splitlines()
                main_calls = [i for i, line in enumerate(lines) if "unittest.main()" in line]
                
                # Keep only the last one
                if len(main_calls) > 1:
                    for idx in main_calls[:-1]:
                        lines[idx] = "# " + lines[idx] + " # Removed duplicate"
                
                # Update content
                processed_map[file_path] = "\n".join(lines)
        
        # Fix inconsistent file references
        if "tasks.json" in content:
            canvas.warning(f"Fixing inconsistent file reference in {file_path}")
            processed_map[file_path] = content.replace("tasks.json", "todos.json")
    
    return processed_map

def write_files_to_disk(code_map: dict[str, str], destination_dir: Path):
    """Writes the generated/modified code content to disk with intelligent path resolution."""
    canvas.step("Writing files to disk with intelligent path resolution...")
    saved_count = 0
    
    try:
        destination_dir.mkdir(parents=True, exist_ok=True)
        
        # Resolve file paths using project layout intelligence
        try:
            from i2c.workflow.file_path_resolver import resolve_code_map_paths
            
            canvas.info(f"🧠 Resolving {len(code_map)} file paths using project layout analysis...")
            resolved_code_map = resolve_code_map_paths(code_map, destination_dir)
            
            # Show path resolutions
            if len(resolved_code_map) != len(code_map) or any(orig != res for orig, res in zip(code_map.keys(), resolved_code_map.keys())):
                canvas.info("📍 Path resolutions applied:")
                for orig_path in code_map.keys():
                    resolved_path = next((r for r in resolved_code_map.keys() if code_map[orig_path] == resolved_code_map[r]), orig_path)
                    if orig_path != resolved_path:
                        canvas.info(f"   {orig_path} → {resolved_path}")
            
            # Use resolved code map
            code_map = resolved_code_map
            
        except Exception as e:
            canvas.warning(f"⚠️ Path resolution failed, using original paths: {e}")
            # Continue with original code_map
        
        # Add debug logging
        canvas.info(f"Files to write: {len(code_map)}")
        for rel_path, content in code_map.items():
            canvas.info(f"Content length for {rel_path}: {len(content)} chars")
        
        for relative_path_str, content in code_map.items():
            full_path = destination_dir / relative_path_str
            
            # Skip empty or near-empty content if the file already exists
            try:
                file_exists = full_path.exists()
            except (PermissionError, OSError):
                file_exists = False  # Assume doesn't exist if we can't check
            
            if file_exists and len(content.strip()) < 5:
                canvas.warning(f"   ⚠️ Skipping write of empty content to existing file: {full_path}")
                continue
                
            canvas.info(f"   -> Writing {full_path} ({len(content)} chars)")
            
            try:
                # Ensure parent directories exist - force creation
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Verify directory was created
                if not full_path.parent.exists():
                    canvas.error(f"   ❌ Failed to create directory: {full_path.parent}")
                    continue
                
                # Clean content - remove diff artifacts if present
                clean_content = content
                if content.startswith("# === Diff for") or content.startswith("---"):
                    # This is diff format, extract actual content
                    lines = content.splitlines()
                    clean_lines = []
                    in_diff_header = True
                    
                    for line in lines:
                        if line.startswith("+++") and in_diff_header:
                            in_diff_header = False
                            continue
                        elif not in_diff_header:
                            if line.startswith("+"):
                                clean_lines.append(line[1:])  # Remove + prefix
                            elif not line.startswith("-") and not line.startswith("@@"):
                                clean_lines.append(line)
                    
                    clean_content = "\n".join(clean_lines)
                
                # Final check - don't write empty content
                if len(clean_content.strip()) < 10 and full_path.exists():
                    canvas.warning(f"   ⚠️ Preserving existing file - new content too short")
                    continue
                
                # Write the file
                full_path.write_text(clean_content, encoding='utf-8')
                
                # Verify file was written (safely handle permission errors)
                try:
                    if full_path.exists() and full_path.stat().st_size > 0:
                        saved_count += 1
                        canvas.info(f"   ✅ Successfully wrote {full_path}")
                    else:
                        canvas.error(f"   ❌ File write verification failed: {full_path}")
                except (PermissionError, OSError):
                    # Can't verify file stats due to permissions, assume success if no write error
                    saved_count += 1
                    canvas.info(f"   ✅ File written (verification skipped due to permissions): {full_path}")
            except PermissionError as e:
                canvas.error(f"   ❌ Permission denied writing {full_path}: {e}")
                # Continue without failing the entire process
                continue
            except FileNotFoundError as e:
                canvas.error(f"   ❌ Directory creation failed for {full_path}: {e}")
                continue
            except OSError as e:
                canvas.error(f"   ❌ OS error writing {full_path}: {e}")
                continue
            except Exception as e:
                canvas.error(f"   ❌ Unexpected error writing {full_path}: {e}")

        if saved_count == len(code_map):
            canvas.success(f"✅ All {saved_count} files saved successfully!")
        else:
            canvas.warning(f"⚠️ Saved {saved_count} out of {len(code_map)} files.")

    except Exception as e:
        canvas.error(f"❌ Critical error setting up destination directory {destination_dir}: {e}")
        raise
    
def delete_files(files_to_delete: list[Path], project_path: Path):
    """Deletes the specified files."""
    if not files_to_delete:
        return # Nothing to delete

    canvas.step("Deleting planned files...")
    deleted_count = 0
    for file_to_delete in files_to_delete:
        try:
            if file_to_delete.is_file():
                file_to_delete.unlink()
                canvas.success(f"  - Deleted: {file_to_delete.relative_to(project_path)}")
                deleted_count += 1
            elif file_to_delete.exists(): # It exists but isn't a file
                 canvas.warning(f"  - Path exists but is not a file, skipping deletion: {file_to_delete.relative_to(project_path)}")
            else:
                canvas.warning(f"  - File not found for deletion: {file_to_delete.relative_to(project_path)}")
        except Exception as e:
            canvas.error(f"  - Error deleting file {file_to_delete.relative_to(project_path)}: {e}")
            # Decide if deletion error is critical? For now, continue.

    canvas.info(f"Deleted {deleted_count} out of {len(files_to_delete)} planned files.")

