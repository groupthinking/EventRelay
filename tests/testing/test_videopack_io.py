from src.youtube_extension.videopack import read_pack, write_pack
from src.youtube_extension.videopack.schema import VideoPackV0, Transcript, TranscriptSegment, Provenance
from datetime import datetime
import json

def test_roundtrip(tmp_path):
    path = tmp_path/"pack.json"
    p = VideoPackV0(
        video_id="auJzb1D-fag",
        transcript=Transcript(full_text="Hi", segments=[TranscriptSegment(idx=0, start_s=0.0, end_s=0.5, text="Hi")]),
        provenance=Provenance(created_at=datetime.utcnow())
    )
    write_pack(path, p)
    q = read_pack(path)
    assert q.video_id == "auJzb1D-fag"
