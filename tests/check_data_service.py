from youtube_extension.backend.services.data_service import DataService
import os
import json


def check_data():
    # Initialize DataService directly. It uses default directories unless specified.
    # The container usually passes enhanced_analysis_dir="youtube_processed_videos/enhanced_analysis"
    service = DataService()
    video_id = "dQw4w9WgXcQ"

    print(f"Checking data for {video_id}...")
    detail = service.get_video_detail(video_id)
    if not detail:
        print(f"No detail found in DataService for video_id: {video_id}")
        print(f"Checking directory: {service.enhanced_analysis_dir.absolute()}")
        if service.enhanced_analysis_dir.exists():
            print("Existing categories:")
            for d in service.enhanced_analysis_dir.iterdir():
                if d.is_dir():
                    print(f"  - {d.name}")
                    for f in d.glob("*"):
                        print(f"    - {f.name}")
        else:
            print("Enhanced analysis directory does not exist.")
        return

    print("Found detail:")
    print(f"Title: {detail.get('title')}")
    print(f"Category: {detail.get('category')}")

    metadata = detail.get("metadata", {})
    print(f"Metadata keys: {list(metadata.keys())}")

    transcript = (
        metadata.get("transcript_text")
        or metadata.get("transcript")
        or detail.get("markdown", "")
    )
    print(f"Transcript preview: {transcript[:100]}...")


if __name__ == "__main__":
    check_data()
