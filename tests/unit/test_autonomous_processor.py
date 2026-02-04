
import unittest
from unittest.mock import MagicMock, patch, AsyncMock, mock_open
import sys
import os
from datetime import datetime, timedelta

from src.youtube_extension.processors.autonomous_processor import AutonomousProcessor

class TestAutonomousProcessor(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Prevent creating actual log files or directories
        self.mock_makedirs = patch('pathlib.Path.mkdir').start()
        
        self.processor = AutonomousProcessor(duration_hours=1)
        # Override start/end time for testing
        self.processor.start_time = datetime.now()
        self.processor.end_time = self.processor.start_time + timedelta(seconds=1)

    def tearDown(self):
        patch.stopall()

    def test_should_continue(self):
        # Case 1: Within time and count limit
        self.processor.end_time = datetime.now() + timedelta(hours=1)
        self.processor.processed_count = 0
        self.assertTrue(self.processor.should_continue())

        # Case 2: Time expired
        self.processor.end_time = datetime.now() - timedelta(hours=1)
        self.assertFalse(self.processor.should_continue())

        # Case 3: Count exceeded
        self.processor.end_time = datetime.now() + timedelta(hours=1)
        self.processor.processed_count = 100
        self.assertFalse(self.processor.should_continue())

    def test_get_next_video(self):
        video_id, category = self.processor.get_next_video()
        self.assertIsInstance(video_id, str)
        self.assertIsInstance(category, str)
        self.assertIn(category, self.processor.category_counts)

    @patch('src.youtube_extension.processors.autonomous_processor.process_video', new_callable=MagicMock)
    async def test_process_video_safe_success(self, mock_process_video):
        # Mock successful processing
        # process_video returns a dict, so we ensure it's a dict
        mock_process_video.return_value = {
            "status": "success", 
            "summary": "test summary",
            "video_id": "v1"
        }
        
        with patch('builtins.open', mock_open()) as mocked_file:
            result = await self.processor.process_video_safe("v1", "Educational_Content")
            
            self.assertIsNotNone(result)
            self.assertEqual(result.get('status'), 'success')
            self.assertEqual(self.processor.processed_count, 1)
            self.assertEqual(self.processor.category_counts['Educational_Content'], 1)
            # Verify file write (mkdir mocked in setUp)
            mocked_file.assert_called()

    @patch('src.youtube_extension.processors.autonomous_processor.process_video', new_callable=MagicMock)
    async def test_process_video_safe_failure(self, mock_process_video):
        # Mock failed processing
        mock_process_video.return_value = {"status": "error"}
        
        result = await self.processor.process_video_safe("v1", "Educational_Content")
        
        self.assertIsNone(result)
        self.assertEqual(self.processor.processed_count, 0)

    @patch('src.youtube_extension.processors.autonomous_processor.process_video', new_callable=MagicMock)
    async def test_run_logic(self, mock_process_video):
        # Mock successful processing
        mock_process_video.return_value = {"status": "success", "summary": "test"}
        
        # Override should_continue to run once then stop
        with patch.object(self.processor, 'should_continue', side_effect=[True, False]):
             with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                 # Must mock open because process_video_safe writes to file
                 with patch('builtins.open', mock_open()):
                    await self.processor.run()
                    
                    # Should have processed 1 video
                    self.assertEqual(len(self.processor.results), 1)
                    mock_process_video.assert_called_once()
                    mock_sleep.assert_called_once()

    def test_log_progress(self):
        # Just ensure no exceptions
        with self.assertLogs(level='INFO') as cm:
            self.processor.log_progress()
            self.assertTrue(any("PROGRESS UPDATE" in msg for msg in cm.output))

    def test_generate_report(self):
        self.processor.results = [{"id": "v1"}]
        
        with patch('builtins.open', mock_open()) as mocked_file:
            self.processor.generate_report()
            mocked_file.assert_called()
            # Could check json dump content if needed

if __name__ == '__main__':
    unittest.main()
