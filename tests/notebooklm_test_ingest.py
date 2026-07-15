
import sys
import os
from src.utils.notebooklm_ingest import upload_to_notebooklm

# Define test file path
TEST_FILE = "youtube_processed_videos/enhanced_analysis/General/dQw4w9WgXcQ_20260211_192116_enhanced.md"

if __name__ == "__main__":
    if not os.path.exists(TEST_FILE):
        print(f"Error: Test file not found: {TEST_FILE}")
        sys.exit(1)
        
    print(f"Running test ingestion for: {TEST_FILE}")
    url = upload_to_notebooklm(TEST_FILE)
    
    if url:
        print(f"Test Passed! Notebook URL: {url}")
        # Could verify by calling 'get_notebook' via MCP here, but let's keep it simple.
    else:
        print("Test Failed.")
        sys.exit(1)
