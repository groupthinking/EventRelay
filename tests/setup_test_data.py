import os
import shutil
from pathlib import Path


def setup_data():
    project_root = Path("/Users/garvey/Dev/projects/EventRelay")
    source_base = project_root / "tests" / "youtube_processed_videos"
    target_base = (
        project_root
        / "src"
        / "youtube_extension"
        / "backend"
        / "youtube_processed_videos"
    )

    # Also check the current working directory if running from src...
    # But usually, it's relative to where the server starts.
    # The DataService default is "youtube_processed_videos/enhanced_analysis" relative to CWD.

    source_dir = source_base
    target_dir = project_root / "youtube_processed_videos" / "enhanced_analysis"

    print(f"Setting up test data...")
    print(f"Source: {source_dir}")
    print(f"Target: {target_dir}")

    if not source_dir.exists():
        print(f"Error: Source directory {source_dir} not found.")
        return

    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy all categories
    for category in source_dir.iterdir():
        if category.is_dir():
            target_category = target_dir / category.name
            target_category.mkdir(parents=True, exist_ok=True)
            print(f"Copying category: {category.name}")
            for item in category.iterdir():
                if item.is_file():
                    shutil.copy2(item, target_category / item.name)
                    print(f"  Copied: {item.name}")

    print("Test data setup complete.")


if __name__ == "__main__":
    setup_data()
