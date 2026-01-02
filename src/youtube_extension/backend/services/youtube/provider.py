from dataclasses import dataclass
from typing import Optional


@dataclass
class TranscriptSegment:
    idx: int
    start_s: float
    end_s: float
    text: str

class YouTubeProvider:
    def get_transcript(self, video_id: str, lang_hint: Optional[str]=None) -> list[TranscriptSegment]:
        raise NotImplementedError

    def get_metadata(self, video_id: str) -> dict:
        raise NotImplementedError
