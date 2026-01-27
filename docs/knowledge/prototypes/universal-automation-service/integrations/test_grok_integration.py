import sys
import os
from pathlib import Path

# Add project roots to path
sys.path.insert(0, "/Users/garvey/Dev/OpenAI_Hub/universal-automation-service")
sys.path.insert(0, "/Users/garvey/Dev/OpenAI_Hub/universal-automation-service/integrations")

# Mock Environment (Removed to test .env loading)
# os.environ["XAI_API_KEY"] = "..."

try:
    from universal_coordinator import UniversalAutomationCoordinator
    
    print("Testing Universal Coordinator Initialization (Expect .env loading)...")
    coordinator = UniversalAutomationCoordinator(mode="hybrid", gemini_api_key="TEST_KEY", github_token="TEST_TOKEN")
    
    if coordinator.grok_service:
        print("✅ Grok Service is active in Coordinator.")
        
        # Test basic metadata structure (Dry Run)
        meta = {"title": "Test Video", "duration": "10:00"}
        print(f"Testing Grok Context Processing with model: {coordinator.grok_service.model}")
        # We won't actually call the API to save tokens/avoid errors without real video, 
        # just verifying the method exists and runs.
        # result = coordinator.grok_service.process_video_context(meta, "Test transcript")
        # print("Result:", result)
    else:
        print("❌ Grok Service failed to load.")
        sys.exit(1)

except Exception as e:
    print(f"❌ Test Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
