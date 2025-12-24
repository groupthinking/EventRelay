from __future__ import annotations
import json, os
from pathlib import Path
from typing import Union
from .schema import VideoPackV0

PathLike = Union[str, os.PathLike]


def load_json(path: PathLike) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: PathLike, data: dict) -> None:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with open(path_obj, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_pack(path: PathLike) -> VideoPackV0:
    data = load_json(path)
    return VideoPackV0(**data)


def write_pack(path: PathLike, pack: VideoPackV0) -> None:
    save_json(path, json.loads(pack.json()))
