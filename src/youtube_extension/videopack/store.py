"""Filesystem get-or-create store for VideoPack v0.

Layout matches the existing convention documented in versioning.py:
`storage/video_packs/<video_id>/pack.json`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from youtube_extension.videopack.io import read_pack, write_pack
from youtube_extension.videopack.schema import VideoPackV0

PathLike = Union[str, Path]


class VideoPackStore:
    def __init__(self, root: PathLike) -> None:
        self.root = Path(root)

    def path_for(self, video_id: str) -> Path:
        return self.root / video_id / "pack.json"

    def get(self, video_id: str) -> Optional[VideoPackV0]:
        path = self.path_for(video_id)
        if not path.is_file():
            return None
        return read_pack(path)

    def put(self, pack: VideoPackV0) -> None:
        write_pack(self.path_for(pack.video_id), pack)
