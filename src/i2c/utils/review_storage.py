# Utility function for saving review results.

from pathlib import Path
from datetime import datetime

# Import CLI for logging (optional)
try:
    from i2c.cli.controller import canvas
except ImportError:
    # Basic fallback logger
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_UTIL] {msg}")
        def error(self, msg): print(f"[ERROR_UTIL] {msg}")
        def info(self, msg): print(f"[INFO_UTIL] {msg}")
    canvas = FallbackCanvas()


def save_review_to_file(project_path: Path, review_text: str) -> Path | None:
    """
    Saves the review text into a timestamped file inside the project's .reviews folder.

    Args:
        project_path: Root path of the project being reviewed.
        review_text: Text generated by the ReviewerAgent.

    Returns:
        Path to the saved review file, or None if saving failed.
    """
    if not review_text: # Don't save empty reviews
        return None

    try:
        reviews_dir = project_path / ".reviews" # Hidden directory for reviews
        reviews_dir.mkdir(exist_ok=True) # Create .reviews folder if not exists

        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") # Added seconds for uniqueness
        review_file = reviews_dir / f"review_{timestamp}.md" # Save as Markdown

        # Write the review text
        review_file.write_text(review_text.strip(), encoding="utf-8")
        canvas.info(f"   [ReviewStorage] Saved AI review to: {review_file.relative_to(project_path.parent)}") # Show relative path
        return review_file
    except Exception as e:
        canvas.error(f"   ❌ [ReviewStorage] Failed to save review file: {e}")
        return None

