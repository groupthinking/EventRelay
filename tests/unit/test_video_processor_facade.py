import pytest
from unittest.mock import AsyncMock, MagicMock
from youtube_extension.services.video_processor_facade import VideoProcessorFacade, VideoProcessorBackend

@pytest.mark.asyncio
async def test_facade_dispatches_to_backend():
    mock_backend = MagicMock(spec=VideoProcessorBackend)
    mock_backend.process_video = AsyncMock(return_value={"status": "success"})
    
    facade = VideoProcessorFacade(mock_backend)
    result = await facade.process("https://www.youtube.com/watch?v=auJzb1D-fag")
    
    assert result == {"status": "success"}
    mock_backend.process_video.assert_called_once_with("https://www.youtube.com/watch?v=auJzb1D-fag")
