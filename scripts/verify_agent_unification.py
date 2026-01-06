
import asyncio
import sys
import unittest
from unittest.mock import MagicMock, AsyncMock

# Add src to path
sys.path.append("/Users/garvey/Dev/projects/EventRelay/src")

# Mock missing dependencies to allow import in bare environment
sys.modules['google.generativeai'] = MagicMock()
sys.modules['google.api_core'] = MagicMock()
sys.modules['pandas'] = MagicMock()
sys.modules['numpy'] = MagicMock()
sys.modules['openai'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['transformers'] = MagicMock()
sys.modules['yt_dlp'] = MagicMock()
sys.modules['googleapiclient'] = MagicMock()
sys.modules['googleapiclient.discovery'] = MagicMock()
sys.modules['googleapiclient.errors'] = MagicMock()
sys.modules['youtube_transcript_api'] = MagicMock()
sys.modules['youtube_transcript_api._errors'] = MagicMock()
sys.modules['httpx'] = MagicMock()
sys.modules['aiohttp'] = MagicMock() # Mock legacy dependency

from agents.mcp_ecosystem_coordinator import MCPVideoProcessorServer
from youtube_extension.processors.enhanced_extractor import VideoContent, VideoMetadata, ProcessingStage

class TestUnifiedPipeline(unittest.IsolatedAsyncioTestCase):
    async def test_coordinator_integration(self):
        """Verify that MCP server calls EnhancedVideoExtractor and returns world_class_score"""

        # 1. Setup Server
        server = MCPVideoProcessorServer()

        # 2. Mock the Extractor to avoid real network calls
        mock_content = VideoContent(
            metadata=VideoMetadata(
                video_id="test_vid", title="Test Title", description="Test Desc",
                duration=100, upload_date="2024-01-01", uploader="Tester", view_count=1000,
                like_count=50, comment_count=10
            ),
            transcript=[],
            summary="Test Summary",
            topics=["AI", "Python"],
            sentiment="positive",
            # This 'world_class_analysis' field is the proof of Unification
            world_class_analysis={"quality_score": 9.5},
            actions=[{"type": "learning_pathway"}]
        )

        server.extractor.process_video = AsyncMock(return_value=mock_content)

        # 3. Handle Request
        result = await server.handle_request({"action": "process_video", "video_id": "test_vid"})

        # 4. Verification
        print("\n--- Result Verification ---")
        print(result)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"], "Test Summary")
        self.assertEqual(result["analysis"]["world_class_score"], 9.5)
        self.assertEqual(len(result["analysis"]["actions"]), 1)

        print("\n✅ VERIFICATION PASSED: Unification Logic Confirmed")

if __name__ == "__main__":
    unittest.main()
