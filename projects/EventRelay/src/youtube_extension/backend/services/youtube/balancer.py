from typing import List, Optional
from .provider import YouTubeProvider, TranscriptSegment

class BalancedYouTube(YouTubeProvider):
    def __init__(self, providers: List[YouTubeProvider]):
        self.providers = providers

    def get_transcript(self, video_id: str, lang_hint: Optional[str]=None) -> List[TranscriptSegment]:
        errors = []
        for p in self.providers:
            try:
                return p.get_transcript(video_id, lang_hint)
            except Exception as e:
                errors.append((type(p).__name__, str(e)))
        raise RuntimeError(f"All providers failed: {errors}")

    def get_metadata(self, video_id: str) -> dict:
        for p in self.providers:
            try:
                return p.get_metadata(video_id)
            except Exception:
                continue
        raise RuntimeError("No providers could fetch metadata")
