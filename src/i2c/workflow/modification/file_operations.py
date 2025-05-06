# Handles writing and deleting files for the modification cycle.

from pathlib import Path
from i2c.cli.controller import canvas # For logging

def write_files_to_disk(code_map: dict[str, str], destination_dir: Path):
    """Writes the generated/modified code content to disk."""
    canvas.step("Writing files to disk...")
    saved_count = 0
    try:
        destination_dir.mkdir(parents=True, exist_ok=True)
        for relative_path_str, content in code_map.items():
            full_path = destination_dir / relative_path_str
            canvas.info(f"   -> Writing {full_path} ({len(content)} chars)")
            try:
                # Ensure parent directories for the file exist
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding='utf-8')
                saved_count += 1
            except OSError as e:
                canvas.error(f"   ❌ Error writing file {full_path}: {e}")
                # Decide if one error should stop all writing? For now, continue.
            except Exception as e:
                 canvas.error(f"   ❌ Unexpected error writing file {full_path}: {e}")

        if saved_count == len(code_map):
            canvas.success(f"✅ All {saved_count} files saved successfully!")
        else:
            canvas.warning(f"⚠️ Saved {saved_count} out of {len(code_map)} files.")

    except Exception as e:
        canvas.error(f"❌ Critical error setting up destination directory {destination_dir}: {e}")
        raise # Re-raise critical errors


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

