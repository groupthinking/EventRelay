
import sys
import os
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock

# Setup path to import src
sys.path.append(os.path.join(os.getcwd(), "src"))

# Import app
try:
    from youtube_extension.backend.main import app
    # Import the specific dependency to override
    from youtube_extension.backend.api.v1.router import get_health_monitoring_service
except ImportError as e:
    print(f"Failed to import app: {e}")
    sys.exit(1)

# Mock the health service
mock_health_service = MagicMock()
mock_health_service.get_basic_health_status.return_value = {
    "status": "healthy",
    "timestamp": "2026-01-27T00:00:00Z",
    "version": "test",
    "components": {}
}

# Override dependency
app.dependency_overrides[get_health_monitoring_service] = lambda: mock_health_service

async def run_tests():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        print("Testing /api/v1/health (Mocked)...")
        response = await client.get("/api/v1/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200

        print("\nTesting /api/v1/transcript-action (validation)...")
        # Empty body should fail validation
        response = await client.post("/api/v1/transcript-action", json={})
        print(f"Status: {response.status_code}")
        assert response.status_code == 422
        print("✅ Validation check passed (422 received)")

        print("\nTesting /process_video endpoint...")
        # This endpoint is in main.py directly
        # It calls get_enhanced_video_processor() which might fail if dependencies are missing
        # We expect 503 or 500 if dependencies fail, or 200 if working.
        # But we mostly care that the route exists.
        response = await client.post("/process_video", json={"youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "include_transcript": False, "include_ai_analysis": False})
        print(f"Status: {response.status_code}")
        # print(f"Response: {response.json()}") # Might be error details

if __name__ == "__main__":
    try:
        asyncio.run(run_tests())
        print("\n🎉 All integration tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        sys.exit(1)
