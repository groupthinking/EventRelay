import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
import json
from datetime import datetime
import textwrap

# Add src to path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from youtube_extension.processors.enhanced_extractor import (
    EnhancedVideoExtractor, 
    VideoMetadata, 
    TranscriptSegment, 
    VideoContent, 
    ProcessingStage
)

class TestEnhancedVideoExtractor(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Mock dependencies
        self.mock_youtube = MagicMock()
        self.mock_gemini = MagicMock()
        
        # Patch module-level constants
        self.has_video_deps_patcher = patch('youtube_extension.processors.enhanced_extractor.HAS_VIDEO_DEPS', True)
        self.has_ai_deps_patcher = patch('youtube_extension.processors.enhanced_extractor.HAS_AI_DEPS', True)
        self.has_video_deps_patcher.start()
        self.has_ai_deps_patcher.start()

        # Initialize extractor with mocks
        with patch('youtube_extension.processors.enhanced_extractor.build', return_value=self.mock_youtube), \
             patch('youtube_extension.processors.enhanced_extractor.GeminiService', return_value=self.mock_gemini):
            
            config = {'youtube_api_key': 'test_key', 'openai_api_key': 'test_openai_key'}
            self.extractor = EnhancedVideoExtractor(config)
            
            # Manually inject mocks
            self.extractor.youtube = self.mock_youtube
            self.extractor.gemini_service = self.mock_gemini
            # Fix Gemini process_text to be async
            self.extractor.gemini_service.process_text = AsyncMock()
            
            # Mock scoring engine
            self.extractor.scoring_engine = MagicMock()
            self.extractor.scoring_engine.calculate_all_scores.return_value = {"score": 100}
            self.extractor.scoring_engine.generate_actions.return_value = []

    def tearDown(self):
        self.has_video_deps_patcher.stop()
        self.has_ai_deps_patcher.stop()

    async def test_extract_video_metadata_success(self):
        # Setup mock response
        mock_response = {
            'items': [{
                'snippet': {
                    'title': 'Test Video',
                    'description': 'Test Description',
                    'publishedAt': '2023-01-01T00:00:00Z',
                    'channelTitle': 'Test Channel',
                    'tags': ['tag1', 'tag2'],
                    'thumbnails': {'high': {'url': 'http://example.com/thumb.jpg'}},
                    'defaultLanguage': 'en'
                },
                'statistics': {
                    'viewCount': '1000',
                    'likeCount': '100',
                    'commentCount': '10'
                },
                'contentDetails': {
                    'duration': 'PT5M30S'
                }
            }]
        }
        
        # Configure mock
        self.mock_youtube.videos.return_value.list.return_value.execute.return_value = mock_response
        
        # Execute
        metadata = await self.extractor.extract_video_metadata('video123')
        
        # Verify
        self.assertEqual(metadata.video_id, 'video123')
        self.assertEqual(metadata.title, 'Test Video')
        self.assertEqual(metadata.duration, 330) # 5m 30s
        self.assertEqual(metadata.view_count, 1000)
        self.assertEqual(metadata.source.value, 'youtube')

    async def test_extract_video_metadata_not_found(self):
        # Setup mock empty response
        self.mock_youtube.videos.return_value.list.return_value.execute.return_value = {'items': []}
        
        # Execute & Verify
        with self.assertRaises(ValueError) as cm:
            await self.extractor.extract_video_metadata('missing123')
        self.assertIn("not found", str(cm.exception))

    @patch('httpx.AsyncClient')
    async def test_extract_transcript_success(self, mock_client_cls):
        # Setup mock client
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "subtitles": [
                    {"text": "Hello world", "start": "0", "dur": "2"},
                    {"text": "This is a test", "start": "2", "dur": "3"}
                ]
            }
        }
        mock_client.post.return_value = mock_response
        
        # Execute
        segments = await self.extractor.extract_transcript('video123')
        
        # Verify
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].text, "Hello world")
        self.assertEqual(segments[0].start, 0.0)
        self.assertEqual(segments[0].duration, 2.0)
        self.assertEqual(segments[1].end, 5.0) # 2+3

    @patch('httpx.AsyncClient')
    async def test_extract_transcript_failure(self, mock_client_cls):
        # Setup mock failure
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": False,
            "error": "No captions available"
        }
        mock_client.post.return_value = mock_response
        
        # Execute & Verify
        with self.assertRaises(ValueError):
            await self.extractor.extract_transcript('video123')

    async def test_analyze_content_gemini(self):
        # Setup Gemini mock
        self.mock_gemini.is_available.return_value = True
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.response = textwrap.dedent("""
        ## 🎯 Content Summary
        This is a summary generated by Gemini.

        ## 🔗 Related Topics
        ['Python', 'Testing', 'Mocking']
        """).strip()
        self.mock_gemini.process_text.return_value = mock_result
        
        transcript = [TranscriptSegment(text="content", start=0, duration=1)]
        
        # Execute
        analysis = await self.extractor.analyze_content(transcript)
        
        # Verify
        self.assertEqual(analysis['summary'], "This is a summary generated by Gemini.")
        self.assertEqual(analysis['topics'], ["Python", "Testing", "Mocking"])
        self.assertEqual(analysis['sentiment'], "analyzed_by_gemini")

    @patch('youtube_extension.processors.enhanced_extractor.pipeline')
    async def test_analyze_content_fallback_local(self, mock_pipeline):
        # Setup Gemini unavailable
        self.mock_gemini.is_available.return_value = False
        
        # Setup local pipeline mocks
        mock_summarizer = MagicMock()
        mock_summarizer.return_value = [{'summary_text': 'Local summary.'}]
        
        mock_sentiment = MagicMock()
        mock_sentiment.return_value = [{'label': 'POSITIVE', 'score': 0.99}]
        
        # Let's mock _load_ai_models behavior by injecting mocks directly
        self.extractor.summarizer = mock_summarizer
        self.extractor.sentiment_analyzer = mock_sentiment
        
        # Make text long enough to trigger summarizer (> 1000 chars)
        long_text = "This is a very important and positive test video about software engineering. " * 50
        transcript = [TranscriptSegment(text=long_text, start=0, duration=10)]
        
        # Execute
        analysis = await self.extractor.analyze_content(transcript)
        
        # Verify
        self.assertEqual(analysis['summary'], "Local summary.")
        self.assertEqual(analysis['sentiment'], "positive")
        self.assertTrue(len(analysis['key_points']) > 0) # "important" keyword logic

    @patch('youtube_extension.processors.enhanced_extractor.extract_video_id', return_value='video123')
    async def test_process_video_integration(self, mock_extract_id):
        # Mock parts of process_video to avoid full integration
        self.extractor.extract_video_metadata = AsyncMock(return_value=VideoMetadata(
            video_id='video123',
            title='Integrated Test',
            description='Desc',
            duration=60,
            upload_date='2023-01-01',
            uploader='Me',
            view_count=100
        ))
        
        self.extractor.extract_transcript = AsyncMock(return_value=[
            TranscriptSegment(text="Hello", start=0, duration=1)
        ])
        
        self.extractor.analyze_content = AsyncMock(return_value={
            'summary': 'Analyzed',
            'sentiment': 'Neutral'
        })
        
        # Execute
        content = await self.extractor.process_video('http://youtube.com/watch?v=video123')
        
        # Verify
        self.assertEqual(content.metadata.title, 'Integrated Test')
        self.assertEqual(content.transcript[0].text, 'Hello')
        self.assertEqual(content.summary, 'Analyzed')
        self.assertEqual(content.processing_stage, ProcessingStage.COMPLETE)
        self.assertIsNotNone(content.world_class_analysis) # Mocked in setUp

    def test_export_content_json(self):
        content = VideoContent(
            metadata=VideoMetadata(video_id='v1', title='T', description='D', duration=10, upload_date='D', uploader='U', view_count=1),
            transcript=[],
            summary='S'
        )
        
        with patch('builtins.open', unittest.mock.mock_open()) as m:
            with patch('json.dump') as mock_json_dump:
                self.extractor.export_content(content, 'json', 'test_output')
                
                m.assert_called_with('test_output.json', 'w', encoding='utf-8')
                mock_json_dump.assert_called()

if __name__ == '__main__':
    unittest.main()