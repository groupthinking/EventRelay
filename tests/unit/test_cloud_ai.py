import pytest
import sys
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Load cloud_ai.py module explicitly to avoid collision with the cloud_ai package folder
src_dir = Path(__file__).resolve().parents[2] / "src"
cloud_ai_path = src_dir / "youtube_extension" / "integrations" / "cloud_ai.py"

spec = importlib.util.spec_from_file_location(
    "youtube_extension.integrations.cloud_ai_module",
    str(cloud_ai_path)
)
cloud_ai = importlib.util.module_from_spec(spec)
sys.modules["youtube_extension.integrations.cloud_ai_module"] = cloud_ai
spec.loader.exec_module(cloud_ai)

get_available_providers = cloud_ai.get_available_providers
create_default_config = cloud_ai.create_default_config
quick_analyze = cloud_ai.quick_analyze
AnalysisType = cloud_ai.AnalysisType

def test_get_available_providers():
    providers = get_available_providers()
    assert isinstance(providers, list)

def test_create_default_config():
    config = create_default_config()
    assert "google_cloud" in config
    assert "aws_rekognition" in config
    assert "azure_vision" in config

@pytest.mark.asyncio
async def test_quick_analyze(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    
    mock_result = AsyncMock()
    mock_integrator = AsyncMock()
    mock_integrator.__aenter__.return_value = mock_integrator
    mock_integrator.analyze_video.return_value = mock_result
    
    # Use patch.object on the loaded module directly
    with patch.object(cloud_ai, "CloudAIIntegrator", return_value=mock_integrator):
        result = await quick_analyze("https://www.youtube.com/watch?v=auJzb1D-fag")
        assert result is mock_result
        mock_integrator.analyze_video.assert_called_once_with(
            "https://www.youtube.com/watch?v=auJzb1D-fag",
            [
                AnalysisType.LABEL_DETECTION,
                AnalysisType.OBJECT_TRACKING,
                AnalysisType.TEXT_DETECTION,
            ],
            preferred_provider=None,
        )
